import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.utils import timezone
from quizapp.errors import Conflict
from quizapp.models import Quiz, QuizAttempt, StudyMaterial, UserAnswer
from quizapp.services import submit_quiz
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def submission(quiz, correct=True):
    return {
        "quizId": quiz["id"],
        "answers": [
            {
                "questionId": q["id"],
                "selectedAnswer": q["expected"] if correct else "Bananas are spaceships.",
                "timeSpent": 12,
            }
            for q in quiz["questions"]
        ],
    }


def submit(client, quiz, body=None, key=None):
    return client.post(
        f"/api/quizzes/{quiz['id']}/submit/",
        body or submission(quiz),
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(key or uuid.uuid4()),
    )


def test_full_offline_flow(client, quiz):
    public = client.get(f"/api/quizzes/{quiz['id']}/").data
    assert all("expected" not in q and "source_quote" not in q for q in public["questions"])
    response = submit(client, quiz)
    assert response.status_code == 201, response.data
    assert response.data["score"] == 100
    assert response.data["correct_count"] == 2
    assert response.data["ai_mode"] == "mock"
    assert UserAnswer.objects.count() == 2
    assert client.get("/api/profile/history/").data["totalAttempts"] == 1
    analysis = client.post(f"/api/quizzes/{quiz['id']}/analyze/", {}, format="json")
    assert analysis.status_code == 200
    assert analysis.data["overallScore"] == 100
    assert analysis.data["categories"][0]["averageSeconds"] == 12
    assert client.get("/api/recommendations/").data["recommendations"][0]["quizId"] == quiz["id"]


def test_semantic_grading_still_uses_backend_score(client, quiz):
    body = submission(quiz)
    body["answers"][1]["selectedAnswer"] = (
        "Related meanings occupy neighboring locations in a numerical space."
    )
    with patch(
        "ai_service.grading.run_with_fallback",
        return_value=(
            {"verdict": "correct", "score": 0.9, "justification": "Preserves the meaning."},
            {"mode": "live", "notice": "real"},
        ),
    ):
        response = submit(client, quiz, body)
    assert response.data["score"] == 100  # NOT 95: binary objective score.
    assert response.data["answers"][1]["score"] == 0.9
    assert response.data["answers"][1]["justification"] == "Preserves the meaning."


def test_wrong_and_skipped_answers(client, quiz):
    body = submission(quiz, False)
    body["answers"][1]["selectedAnswer"] = ""
    result = submit(client, quiz, body)
    assert result.data["score"] == 0
    assert result.data["correct_count"] == 0
    assert result.data["answers"][1]["justification"] == "No answer submitted."


def test_idempotent_retry_and_payload_conflict(client, quiz):
    key = uuid.uuid4()
    first = submit(client, quiz, key=key)
    again = submit(client, quiz, key=key)
    conflict = submit(client, quiz, submission(quiz, False), key)
    assert (first.status_code, again.status_code, conflict.status_code) == (201, 200, 409)
    assert first.data["id"] == again.data["id"]
    assert QuizAttempt.objects.count() == 1


def test_missing_idempotency_key(client, quiz):
    response = client.post(f"/api/quizzes/{quiz['id']}/submit/", submission(quiz), format="json")
    assert response.status_code == 400


@pytest.mark.parametrize(
    "change",
    [
        "duplicate",
        "missing",
        "foreign",
        "negative_time",
        "huge_time",
        "huge_answer",
        "mismatch",
        "nan",
        "wrong_type",
    ],
)
def test_invalid_submission_never_writes(client, quiz, change):
    body = submission(quiz)
    if change == "duplicate":
        body["answers"][1] = body["answers"][0]
    if change == "missing":
        body["answers"].pop()
    if change == "foreign":
        body["answers"][0]["questionId"] = 99999
    if change == "negative_time":
        body["answers"][0]["timeSpent"] = -1
    if change == "huge_time":
        body["answers"][0]["timeSpent"] = 86401
    if change == "huge_answer":
        body["answers"][0]["selectedAnswer"] = "x" * 4001
    if change == "mismatch":
        body["quizId"] = 99999
    if change == "nan":
        body["answers"][0]["timeSpent"] = "NaN"
    if change == "wrong_type":
        body["answers"] = "oops"
    assert submit(client, quiz, body).status_code == 400
    assert QuizAttempt.objects.count() == 0


@pytest.mark.parametrize(
    "change",
    [
        {"count": 0},
        {"count": 11},
        {"count": 1},
        {"types": []},
        {"types": ["multiple_choice", "multiple_choice"]},
        {"difficulty": "impossible"},
        {"topic": "no material"},
    ],
)
def test_invalid_generation(client, material, change):
    payload = {
        "topic": "embeddings",
        "count": 2,
        "types": ["multiple_choice", "short_answer"],
        **change,
    }
    result = client.post("/api/quizzes/generate/", payload, format="json")
    assert result.status_code == 400, result.data
    assert Quiz.objects.count() == 0


def test_no_material_message(client):
    result = client.post("/api/quizzes/generate/", {"topic": "unknown"}, format="json")
    assert "Add study material" in str(result.data)


def test_private_notes_are_isolated(client, material, user):
    other = get_user_model().objects.create_user("other")
    material.owner = other
    material.save()
    assert client.get("/api/material/").data["count"] == 0
    result = client.post("/api/quizzes/generate/", {"topic": "embeddings"}, format="json")
    assert result.status_code == 400


def test_other_user_cannot_read_edit_submit_analyze_or_delete(client, quiz):
    attempt = submit(client, quiz).data
    other = APIClient()
    other.force_authenticate(get_user_model().objects.create_user("other"))
    url = f"/api/quizzes/{quiz['id']}/"
    assert other.get(url).status_code == 404
    assert other.get(url + "review/").status_code == 404
    assert other.patch(url, {"title": "changed"}, format="json").status_code == 404
    assert other.delete(url).status_code == 404
    assert other.post(url + "submit/", submission(quiz), format="json").status_code == 404
    assert other.post(url + "analyze/", {}, format="json").status_code == 404
    assert other.get(f"/api/attempts/{attempt['id']}/").status_code == 404
    assert other.get("/api/profile/history/").data["totalAttempts"] == 0


def test_attempt_makes_quiz_immutable(client, quiz):
    submit(client, quiz)
    url = f"/api/quizzes/{quiz['id']}/"
    assert (
        client.patch(
            url, {"version": quiz["version"], "title": "New title"}, format="json"
        ).status_code
        == 409
    )
    assert client.delete(url).status_code == 409


def test_stale_editor_rejected(client, quiz):
    result = client.patch(
        f"/api/quizzes/{quiz['id']}/", {"version": 1, "title": "stale"}, format="json"
    )
    assert result.status_code == 409


def test_edit_questions_and_publish(client, material):
    quiz = client.post(
        "/api/quizzes/generate/", {"topic": "embeddings", "count": 2}, format="json"
    ).data
    assert submit(client, quiz).status_code == 400
    questions = quiz["questions"]
    questions[1]["text"] = "Explain the concept with different wording."
    result = client.patch(
        f"/api/quizzes/{quiz['id']}/",
        {"questions": questions, "version": 1, "status": "published"},
        format="json",
    )
    assert result.status_code == 200, result.data
    assert result.data["questions"][1]["text"] == questions[1]["text"]


def test_mid_grading_edit_rolls_back_attempt(client, quiz, user):
    model = Quiz.objects.get(pk=quiz["id"])

    def grading(*args):
        Quiz.objects.filter(pk=model.id).update(version=99)
        return {"verdict": "correct", "score": 1, "justification": "yes", "mode": "mock"}

    # Run sequential map here to avoid SQLite test transaction visibility between threads.
    with (
        patch("quizapp.services.ThreadPoolExecutor") as pool,
        patch("quizapp.services.grade", side_effect=grading),
    ):
        pool.return_value.__enter__.return_value.map.side_effect = lambda fn, rows: map(fn, rows)
        with pytest.raises(Conflict):
            submit_quiz(user, model, submission(quiz), uuid.uuid4())
    assert not QuizAttempt.objects.exists()


def test_transaction_rolls_back_if_answer_write_fails(client, quiz):
    with patch(
        "quizapp.services.UserAnswer.objects.bulk_create", side_effect=IntegrityError("simulated")
    ):
        with pytest.raises(IntegrityError):
            submit(client, quiz)
    assert not QuizAttempt.objects.exists()


def test_registration_login_expiry_and_logout(db):
    client = APIClient()
    result = client.post(
        "/api/auth/register/",
        {"username": "NewLearner", "password": "Stronger!Practice2026"},
        format="json",
    )
    assert result.status_code == 201
    client.credentials(HTTP_AUTHORIZATION=f"Token {result.data['token']}")
    assert client.get("/api/auth/me/").data["username"] == "newlearner"
    assert client.post("/api/auth/logout/").status_code == 204
    assert client.get("/api/auth/me/").status_code == 401
    result = client.post(
        "/api/auth/login/",
        {"username": "NEWLEARNER", "password": "Stronger!Practice2026"},
        format="json",
    )
    token = result.data["token"]
    Token.objects.filter(key=token).update(created=timezone.now() - timedelta(hours=25))
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    assert client.get("/api/auth/me/").status_code == 401


@pytest.mark.parametrize(
    "payload",
    [
        {"username": "bad user", "password": "longrandompassword123"},
        {"username": "valid", "password": "123"},
        {"username": "valid", "password": "12345678901"},
    ],
)
def test_bad_registration(payload):
    assert APIClient().post("/api/auth/register/", payload, format="json").status_code == 400


def test_unauthenticated_protected_endpoints():
    client = APIClient()
    for path in [
        "/api/material/",
        "/api/quizzes/",
        "/api/profile/history/",
        "/api/recommendations/",
        "/api/attempts/",
    ]:
        assert client.get(path).status_code == 401
    assert client.get("/api/health/").status_code == 200


def test_material_upload_and_validation(client):
    from django.core.files.uploadedfile import SimpleUploadedFile

    result = client.post(
        "/api/material/",
        {
            "topic": "  Custom Topic  ",
            "title": "Notes",
            "file": SimpleUploadedFile(
                "notes.md", b"These notes describe a unique custom topic in sufficient detail."
            ),
        },
        format="multipart",
    )
    assert result.status_code == 201
    assert result.data["topic"] == "custom topic"
    for filename, content in [
        ("bad.pdf", b"x" * 40),
        ("bad.txt", b"\xff" * 40),
        ("large.txt", b"x" * 100001),
    ]:
        result = client.post(
            "/api/material/",
            {"topic": "topic", "title": "Notes", "file": SimpleUploadedFile(filename, content)},
            format="multipart",
        )
        assert result.status_code == 400


def test_personal_notes_override_seed(client, material):
    StudyMaterial.objects.create(
        owner=None,
        topic="embeddings",
        title="other",
        content="A completely different source about generic embeddings.",
    )
    result = client.post(
        "/api/quizzes/generate/", {"topic": " EMBEDDINGS ", "count": 2}, format="json"
    )
    assert result.status_code == 201
    assert Quiz.objects.get(pk=result.data["id"]).source_text == material.content


def test_analysis_uses_specific_owned_attempt(client, quiz):
    first = submit(client, quiz).data
    second = submit(client, quiz, submission(quiz, False)).data
    result = client.post(
        f"/api/quizzes/{quiz['id']}/analyze/", {"attemptId": first["id"]}, format="json"
    )
    assert result.data["overallScore"] == 100
    result = client.post(
        f"/api/quizzes/{quiz['id']}/analyze/", {"attemptId": second["id"]}, format="json"
    )
    assert result.data["overallScore"] == 0
    assert (
        client.post(
            f"/api/quizzes/{quiz['id']}/analyze/", {"attemptId": "bad"}, format="json"
        ).status_code
        == 400
    )


def test_adaptive_uses_only_last_five(client, quiz):
    for _ in range(6):
        submit(client, quiz)
    result = client.get("/api/profile/difficulty/")
    assert result.data["attemptsUsed"] == 5
    assert result.data["difficulty"] == "intermediate"
    result = client.post(
        "/api/quizzes/generate/",
        {"topic": "embeddings", "count": 2, "adaptive": True},
        format="json",
    )
    assert result.data["difficulty"] == "intermediate"
    assert result.data["adaptive"]["attemptsUsed"] == 5


def test_seed_is_idempotent(settings):
    settings.DEBUG = True
    call_command("seed_demo")
    counts = (StudyMaterial.objects.count(), Quiz.objects.count(), QuizAttempt.objects.count())
    call_command("seed_demo")
    assert counts == (5, 5, 3)
    assert counts == (
        StudyMaterial.objects.count(),
        Quiz.objects.count(),
        QuizAttempt.objects.count(),
    )


def test_bad_json_is_400(client):
    assert (
        client.post(
            "/api/quizzes/generate/", "{broken", content_type="application/json"
        ).status_code
        == 400
    )


def test_database_constraints(client, quiz):
    attempt = submit(client, quiz).data
    with pytest.raises(IntegrityError), transaction.atomic():
        QuizAttempt.objects.filter(pk=attempt["id"]).update(score=101)


@pytest.mark.parametrize(
    "question",
    [
        {},
        {"type": "short_answer"},
        {"type": "multiple_choice", "text": "Test", "expected": "A"},
        {"type": "short_answer", "text": "Test", "expected": "A", "options": ["oops"]},
    ],
)
def test_partial_nested_questions_fail_cleanly(client, quiz, question):
    response = client.patch(
        f"/api/quizzes/{quiz['id']}/",
        {"version": quiz["version"], "questions": [question]},
        format="json",
    )
    assert response.status_code == 400


def test_deleted_during_grading_returns_conflict(client, quiz, user):
    model = Quiz.objects.get(pk=quiz["id"])

    def grading(*args):
        Quiz.objects.filter(pk=quiz["id"]).delete()
        return {"verdict": "correct", "score": 1, "justification": "yes", "mode": "mock"}

    with (
        patch("quizapp.services.ThreadPoolExecutor") as pool,
        patch("quizapp.services.grade", side_effect=grading),
    ):
        pool.return_value.__enter__.return_value.map.side_effect = lambda fn, rows: map(fn, rows)
        with pytest.raises(Conflict):
            submit_quiz(user, model, submission(quiz), uuid.uuid4())
    assert not QuizAttempt.objects.exists()


def test_seeding_preserves_preexisting_private_material(settings, material):
    settings.DEBUG = True
    original = (material.id, material.owner_id, material.content)
    call_command("seed_demo")
    material.refresh_from_db()
    assert (material.id, material.owner_id, material.content) == original
    assert StudyMaterial.objects.filter(owner__isnull=True).count() == 5


def test_oversized_http_body_is_rejected_before_parsing(client):
    response = client.post(
        "/api/material/", '{"content":"' + "x" * 1_048_576 + '"}', content_type="application/json"
    )
    assert response.status_code == 413


def test_json_limit_without_content_length():
    from io import BytesIO

    from quizapp.parsers import BoundedJSONParser, PayloadTooLarge

    with pytest.raises(PayloadTooLarge):
        BoundedJSONParser().parse(BytesIO(b"x" * 1_048_577))
