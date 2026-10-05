import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from quizapp.models import StudyMaterial
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    cache.clear()


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user("learner", password="Practice!Since2008")


@pytest.fixture
def client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def material(user):
    return StudyMaterial.objects.create(
        owner=user,
        topic="embeddings",
        title="Semantic vectors",
        content="An embedding is a vector representing meaning. Similar texts are mapped to nearby vectors. Cosine similarity compares their direction.",
    )


@pytest.fixture
def quiz(client, material):
    response = client.post(
        "/api/quizzes/generate/",
        {"topic": "embeddings", "count": 2, "types": ["multiple_choice", "short_answer"]},
        format="json",
    )
    assert response.status_code == 201, response.data
    data = response.data
    response = client.patch(
        f"/api/quizzes/{data['id']}/",
        {"version": data["version"], "status": "published"},
        format="json",
    )
    assert response.status_code == 200, response.data
    return response.data
