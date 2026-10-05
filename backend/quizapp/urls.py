from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdaptiveView,
    AuthView,
    HealthView,
    MaterialViewSet,
    QuizAttemptViewSet,
    QuizViewSet,
    RecommendationView,
    SessionView,
    UserProfileView,
)

router = DefaultRouter()
router.register("material", MaterialViewSet, basename="material")
router.register("quizzes", QuizViewSet, basename="quiz")
router.register("attempts", QuizAttemptViewSet, basename="attempt")
urlpatterns = [
    path("health/", HealthView.as_view()),
    path("auth/register/", AuthView.as_view(), {"operation": "register"}),
    path("auth/login/", AuthView.as_view(), {"operation": "login"}),
    path("auth/me/", SessionView.as_view()),
    path("auth/logout/", SessionView.as_view()),
    path("profile/history/", UserProfileView.as_view()),
    path("profile/difficulty/", AdaptiveView.as_view()),
    path("recommendations/", RecommendationView.as_view()),
    path("", include(router.urls)),
]
