import json
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest
from ai_service.analysis import validate_narrative
from ai_service.client import ModelUnavailable, complete_json
from ai_service.generation import generate, validate_questions
from ai_service.grading import grade, validate_grade
from ai_service.recommendations import recommend

SOURCE = "Embeddings represent meaning as numerical vectors. Similar meanings are mapped to nearby vectors."
VALID = {
    "questions": [
        {
            "type": "multiple_choice",
            "text": "What does an embedding represent?",
            "options": ["meaning", "File size"],
            "expected": "meaning",
            "source_quote": "Embeddings represent meaning as numerical vectors.",
        },
        {
            "type": "short_answer",
            "text": "Where are similar meanings mapped?",
            "options": [],
            "expected": "nearby vectors",
            "source_quote": "Similar meanings are mapped to nearby vectors.",
        },
    ]
}


def test_valid_grounded_generation():
    with patch("ai_service.client.complete_json", return_value=VALID):
        result, metadata = generate(
            SOURCE, "embeddings", "beginner", 2, ["multiple_choice", "short_answer"]
        )
    assert metadata["mode"] == "live"
    assert result[0]["expected"] == "meaning"


@pytest.mark.parametrize(
    "mutation",
    [
        "empty",
        "count",
        "type",
        "missing_expected",
        "wrong_expected",
        "duplicate_option",
        "duplicate_question",
        "ungrounded",
        "non_object",
        "options_string",
        "short_options",
    ],
)
def test_invalid_generation_falls_back(mutation):
    data = json.loads(json.dumps(VALID))
    if mutation == "empty":
        data = {}
    if mutation == "count":
        data["questions"].pop()
    if mutation == "type":
        data["questions"][0]["type"] = "essay"
    if mutation == "missing_expected":
        del data["questions"][0]["expected"]
    if mutation == "wrong_expected":
        data["questions"][0]["expected"] = "Not an option"
    if mutation == "duplicate_option":
        data["questions"][0]["options"] = ["meaning", "meaning"]
    if mutation == "duplicate_question":
        data["questions"][1]["text"] = data["questions"][0]["text"]
    if mutation == "ungrounded":
        data["questions"][0]["source_quote"] = "Invented evidence."
    if mutation == "non_object":
        data["questions"][0] = 42
    if mutation == "options_string":
        data["questions"][0]["options"] = "bad"
    if mutation == "short_options":
        data["questions"][1]["options"] = ["bad"]
    with patch("ai_service.client.complete_json", return_value=data):
        result, metadata = generate(
            SOURCE, "embeddings", "beginner", 2, ["multiple_choice", "short_answer"]
        )
    assert metadata["mode"] == "mock"
    assert len(result) == 2
    assert all(q["source_quote"] in SOURCE for q in result)


@pytest.mark.parametrize("score", [float("nan"), float("inf"), -1, 1.01, True, "0.8", None])
def test_invalid_model_scores(score):
    with pytest.raises(ValueError):
        validate_grade({"score": score, "verdict": "correct", "justification": "a reason"})


def test_inconsistent_verdict_rejected():
    with pytest.raises(ValueError):
        validate_grade({"score": 0.2, "verdict": "correct", "justification": "wrong"})


def test_mc_never_calls_model():
    question = SimpleNamespace(type="multiple_choice", expected="B", text="Choose")
    with patch(
        "ai_service.client.complete_json", side_effect=AssertionError("Model should not be called")
    ):
        assert grade(question, "B", SOURCE)["score"] == 1
        assert grade(question, "b", SOURCE)["score"] == 0


def test_semantic_paraphrase_and_wrong_answer():
    question = SimpleNamespace(
        type="short_answer",
        expected="Similar meanings map to nearby vectors.",
        text="How are related texts represented?",
    )
    with patch(
        "ai_service.client.complete_json",
        return_value={
            "score": 0.95,
            "verdict": "correct",
            "justification": "Captures the same semantic relationship.",
        },
    ):
        assert (
            grade(question, "Related texts occupy neighboring points in numerical space.", SOURCE)[
                "mode"
            ]
            == "live"
        )
    with patch(
        "ai_service.client.complete_json",
        return_value={
            "score": 0,
            "verdict": "incorrect",
            "justification": "Unrelated to the concept.",
        },
    ):
        assert grade(question, "They are sorted by shoe size.", SOURCE)["verdict"] == "incorrect"


def test_mock_deterministic_and_negation():
    question = SimpleNamespace(
        type="short_answer",
        expected="Embeddings represent meaning as numerical vectors.",
        text="Define embeddings",
    )
    first = grade(question, question.expected, SOURCE)
    assert first == grade(question, question.expected, SOURCE)
    assert first["score"] == 1
    assert (
        grade(question, "Embeddings do not represent meaning as numerical vectors.", SOURCE)[
            "score"
        ]
        == 0
    )


def test_timeout_connection_refusal_and_malformed_json(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    for failure in [httpx.ConnectError("down"), httpx.ReadTimeout("slow"), ValueError("malformed")]:
        with patch("ai_service.client.httpx.Client") as client:
            client.return_value.__enter__.return_value.stream.side_effect = failure
            result, metadata = generate(
                SOURCE, "embeddings", "beginner", 2, ["multiple_choice", "short_answer"]
            )
            assert metadata["mode"] == "fallback"
            assert len(result) == 2


def test_http_boundary_optional_auth_and_no_secret_leak(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    response = httpx.Response(
        200,
        request=httpx.Request("POST", "http://localhost:11434/v1/chat/completions"),
        json={"choices": [{"message": {"content": '{"ok":true}'}}]},
    )
    with patch("ai_service.client.httpx.Client") as client:
        stream = client.return_value.__enter__.return_value.stream
        stream.return_value.__enter__.return_value = response
        assert complete_json("JSON only", {}) == {"ok": True}
        assert "Authorization" not in stream.call_args.kwargs["headers"]
        assert stream.call_args.kwargs["json"]["model"] == "test-model"
    monkeypatch.setenv("LLM_API_KEY", "example-test-key")
    with patch("ai_service.client.httpx.Client") as client:
        stream = client.return_value.__enter__.return_value.stream
        stream.return_value.__enter__.return_value = httpx.Response(
            429, request=httpx.Request("POST", "http://localhost"), json={"error": "rate limit"}
        )
        with pytest.raises(ModelUnavailable) as error:
            complete_json("JSON only", {})
        assert "example-test-key" not in str(error.value)
        assert stream.call_args.kwargs["headers"]["Authorization"] == "Bearer example-test-key"


def test_oversized_model_output(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost/v1")
    monkeypatch.setenv("LLM_MODEL", "test")
    with patch("ai_service.client.httpx.Client") as client:
        response = (
            client.return_value.__enter__.return_value.stream.return_value.__enter__.return_value
        )
        response.iter_bytes.return_value = [b"x" * 150001]
        with pytest.raises(ModelUnavailable):
            complete_json("JSON", {})


def test_narrative_cannot_supply_numeric_metrics():
    with pytest.raises(ValueError):
        validate_narrative(
            {
                "strengths": ["Your score is 99%"],
                "weaknesses": ["none"],
                "recommendations": ["Practice"],
                "nextSteps": "Review",
            }
        )


@pytest.mark.django_db
def test_recommendations_reject_invented_ids(client, quiz, user):
    from quizapp.models import Quiz

    with patch(
        "ai_service.client.complete_json",
        return_value={"recommendations": [{"quizId": 99999, "reason": "invented"}]},
    ):
        result = recommend(user, Quiz.objects.all())
    assert result["recommendations"][0]["quizId"] == quiz["id"]
    assert result["ai"]["mode"] == "mock"


def test_known_template_envelope_is_normalized():
    assert (
        len(
            validate_questions(
                {"quizTemplate": VALID}, 2, ["multiple_choice", "short_answer"], SOURCE
            )
        )
        == 2
    )


def test_unfilled_placeholders_are_rejected():
    data = json.loads(json.dumps(VALID))
    data["questions"][0]["text"] = "WRITE_QUESTION"
    with pytest.raises(ValueError):
        validate_questions(data, 2, ["multiple_choice", "short_answer"], SOURCE)


def test_one_schema_repair_but_no_network_retry():
    with patch("ai_service.client.complete_json", side_effect=[{}, VALID]) as model:
        _, metadata = generate(
            SOURCE, "embeddings", "beginner", 2, ["multiple_choice", "short_answer"]
        )
    assert model.call_count == 2
    assert metadata["mode"] == "live"
    with patch("ai_service.client.complete_json", side_effect=ModelUnavailable("offline")) as model:
        _, metadata = generate(
            SOURCE, "embeddings", "beginner", 2, ["multiple_choice", "short_answer"]
        )
    assert model.call_count == 1
    assert metadata["mode"] == "mock"
