"""Idempotent, opt-in demo data. Never reset an existing user's password."""

import json
import uuid
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import BaseCommand, CommandError
from django.db import transaction

from quizapp.models import Quiz, QuizAttempt, StudyMaterial, UserAnswer
from quizapp.seed_questions import QUESTIONS
from quizapp.services import replace_questions


class Command(BaseCommand):
    help = "Load five study topics, public practice quizzes and local demo history."

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Demo accounts are for development only (DJANGO_DEBUG=true).")
        # Import fixture CONTENT through the ORM, never its fixed primary keys.
        # Running seed after a learner added notes must not overwrite those notes.
        fixtures = json.loads((settings.BASE_DIR / "fixtures" / "sample_material.json").read_text())
        for entry in fixtures:
            fields = entry["fields"]
            StudyMaterial.objects.get_or_create(
                owner=None,
                topic=fields["topic"],
                defaults={"title": fields["title"], "content": fields["content"]},
            )
        user, created = get_user_model().objects.get_or_create(username="demo")
        if created:
            user.set_password("Practice!Since2008")
            user.save()
        for index, material in enumerate(
            StudyMaterial.objects.filter(owner__isnull=True, topic__in=QUESTIONS)
        ):
            quiz, created = Quiz.objects.get_or_create(
                owner=None,
                topic=material.topic,
                defaults={
                    "title": material.title,
                    "difficulty": "beginner",
                    "status": "published",
                    "source_text": material.content,
                    "ai_mode": "curated",
                    "ai_notice": "Human-readable reference quiz included with the dataset.",
                },
            )
            if not created:
                continue
            questions = QUESTIONS[material.topic]
            replace_questions(quiz, questions)
            if index < 3:
                correct_count = 1 if index == 0 else 2
                attempt = QuizAttempt.objects.create(
                    user=user,
                    quiz=quiz,
                    score=Decimal(correct_count * 50),
                    correct_count=correct_count,
                    total_questions=2,
                    time_spent=44 + index * 12,
                    idempotency_key=uuid.uuid5(
                        uuid.NAMESPACE_URL, f"brain-check/demo/{material.topic}"
                    ),
                    payload_hash="demo-fixture",
                    ai_mode="mock",
                )
                for n, question in enumerate(quiz.questions.all()):
                    correct = n < correct_count
                    UserAnswer.objects.create(
                        attempt=attempt,
                        question=question,
                        selected_answer=question.expected
                        if correct
                        else "I need to review this concept.",
                        expected=question.expected,
                        question_text=question.text,
                        question_type=question.type,
                        time_spent=22 + index * 6,
                        verdict="correct" if correct else "incorrect",
                        credit=int(correct),
                        justification="Seeded example result for exploring the app.",
                        ai_mode="mock",
                    )
        self.stdout.write(
            self.style.SUCCESS(
                "Demo data ready. New demo account: demo / Practice!Since2008. Existing passwords remain unchanged."
            )
        )
