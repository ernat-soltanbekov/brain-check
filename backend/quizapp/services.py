"""Business rules, separate from HTTP handling and model prompts."""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from decimal import ROUND_HALF_UP, Decimal

from ai_service.grading import grade
from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError

from .errors import Conflict
from .models import Question, Quiz, QuizAttempt, UserAnswer


def replace_questions(quiz, questions):
    quiz.questions.all().delete()
    Question.objects.bulk_create(
        [Question(quiz=quiz, position=i, **q) for i, q in enumerate(questions)]
    )


def submit_quiz(user, quiz, data, key):
    questions = list(quiz.questions.all())
    answers = {a["questionId"]: a for a in data["answers"]}
    if data.get("quizId", quiz.id) != quiz.id:
        raise ValidationError("quizId does not match the URL.")
    if set(answers) != {q.id for q in questions}:
        raise ValidationError(
            "Submit every quiz question exactly once. Use an empty answer to skip."
        )
    canonical = {
        "quizId": quiz.id,
        "answers": sorted(data["answers"], key=lambda a: a["questionId"]),
    }
    fingerprint = hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()

    def existing_attempt():
        existing = QuizAttempt.objects.filter(user=user, idempotency_key=key).first()
        if existing and existing.payload_hash != fingerprint:
            raise Conflict("This submission key was already used with different answers.")
        return existing

    existing = existing_attempt()
    if existing:
        return existing, False
    if quiz.status != "published":
        raise ValidationError("Review and save this draft before taking it.")
    # Do not hold a database transaction open while waiting for a remote model.
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(
            pool.map(
                lambda q: grade(q, answers[q.id]["selectedAnswer"], quiz.source_text), questions
            )
        )
    correct_count = sum(r["verdict"] == "correct" for r in results)
    # The model NEVER computes this score. Each correct answer has equal weight.
    score = (Decimal(correct_count) * 100 / len(questions)).quantize(
        Decimal(".01"), rounding=ROUND_HALF_UP
    )
    modes = {r["mode"] for r in results} - {"deterministic"}
    ai_mode = (
        "fallback"
        if "fallback" in modes
        else "mock"
        if "mock" in modes
        else "live"
        if "live" in modes
        else "deterministic"
    )
    try:
        with transaction.atomic():
            locked_quiz = Quiz.objects.select_for_update().filter(pk=quiz.pk).first()
            if locked_quiz is None:
                raise Conflict("The quiz was deleted while your answers were being graded.")
            existing = existing_attempt()
            if existing:
                return existing, False
            if locked_quiz.version != quiz.version or locked_quiz.status != "published":
                raise Conflict()
            attempt = QuizAttempt.objects.create(
                user=user,
                quiz=locked_quiz,
                score=score,
                correct_count=correct_count,
                total_questions=len(questions),
                time_spent=sum(a["timeSpent"] for a in answers.values()),
                idempotency_key=key,
                payload_hash=fingerprint,
                ai_mode=ai_mode,
            )
            UserAnswer.objects.bulk_create(
                [
                    UserAnswer(
                        attempt=attempt,
                        question=q,
                        question_text=q.text,
                        question_type=q.type,
                        expected=q.expected,
                        selected_answer=answers[q.id]["selectedAnswer"],
                        time_spent=answers[q.id]["timeSpent"],
                        verdict=r["verdict"],
                        credit=r["score"],
                        justification=r["justification"],
                        ai_mode=r["mode"],
                    )
                    for q, r in zip(questions, results)
                ]
            )
        return attempt, True
    except IntegrityError:
        existing = existing_attempt()
        if existing:
            return existing, False
        raise
