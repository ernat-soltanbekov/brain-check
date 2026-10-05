import uuid
from datetime import timedelta

from ai_service.analysis import analyze
from ai_service.generation import generate
from ai_service.recommendations import adaptive_difficulty, recommend
from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .errors import Conflict
from .models import Quiz, QuizAttempt, StudyMaterial
from .serializers import (
    AttemptSerializer,
    GenerateSerializer,
    LoginSerializer,
    MaterialSerializer,
    QuizSerializer,
    QuizWriteSerializer,
    RegisterSerializer,
    SubmitSerializer,
)
from .services import replace_questions, submit_quiz


def accessible_quizzes(user):
    return Quiz.objects.filter(
        Q(owner=user) | Q(owner__isnull=True, status="published")
    ).prefetch_related("questions")


class HealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        import os

        from ai_service.client import fallback_metadata

        mode = "configured" if os.getenv("LLM_BASE_URL") else "mock"
        return Response(
            {
                "status": "ok",
                "modelMode": mode,
                "notice": "Real model configured; each response reports actual mode."
                if mode == "configured"
                else fallback_metadata()["notice"],
            }
        )


class AuthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request, operation):
        serializer = (RegisterSerializer if operation == "register" else LoginSerializer)(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if operation == "register":
            try:
                user = get_user_model().objects.create_user(**data)
            except IntegrityError as exc:
                raise ValidationError({"username": "This username is already taken."}) from exc
        else:
            user = authenticate(username=data["username"].lower(), password=data["password"])
            if user is None:
                return Response({"detail": "Incorrect username or password."}, status=400)
        with transaction.atomic():
            token, _ = Token.objects.get_or_create(user=user)
            if token.created < timezone.now() - timedelta(hours=24):
                token.delete()
                token = Token.objects.create(user=user)
        return Response(
            {"token": token.key, "user": {"id": user.id, "username": user.username}},
            status=201 if operation == "register" else 200,
        )


class SessionView(APIView):
    def get(self, request):
        return Response({"id": request.user.id, "username": request.user.username})

    def post(self, request):
        request.auth.delete()
        return Response(status=204)


class MaterialViewSet(viewsets.ModelViewSet):
    serializer_class = MaterialSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return StudyMaterial.objects.filter(Q(owner=self.request.user) | Q(owner__isnull=True))

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class QuizViewSet(viewsets.ModelViewSet):
    throttle_scope = None
    serializer_class = QuizSerializer

    def get_queryset(self):
        qs = accessible_quizzes(self.request.user)
        for field in ("topic", "difficulty", "status"):
            value = self.request.query_params.get(field)
            if value:
                qs = qs.filter(**{f"{field}__iexact": value.strip()})
        search = self.request.query_params.get("search", "").strip()[:100]
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(topic__icontains=search))
        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["review"] = self.action in (
            "generate",
            "create",
            "update",
            "partial_update",
            "review",
        )
        return context

    def owner_only(self, quiz):
        if quiz.owner_id != self.request.user.id:
            raise PermissionDenied("Only the quiz owner can edit or review it.")

    @action(detail=True, methods=["get"])
    def review(self, request, pk=None):
        quiz = self.get_object()
        self.owner_only(quiz)
        return Response(self.get_serializer(quiz).data)

    @action(
        detail=False, methods=["post"], throttle_classes=[ScopedRateThrottle], throttle_scope="ai"
    )
    def generate(self, request):
        serializer = GenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        # Personal notes take precedence over seeded notes for the same topic.
        notes = StudyMaterial.objects.filter(owner=request.user, topic=data["topic"])
        if not notes.exists():
            notes = StudyMaterial.objects.filter(owner__isnull=True, topic=data["topic"])
        texts = list(notes.order_by("-created_at", "-id").values_list("content", flat=True)[:5])
        if not texts:
            raise ValidationError(
                {"topic": "Add study material for this topic first using /api/material/."}
            )
        source = "\n\n".join(texts)[:20000]
        decision = adaptive_difficulty(request.user) if data["adaptive"] else None
        difficulty = decision["difficulty"] if decision else data["difficulty"]
        questions, metadata = generate(
            source, data["topic"], difficulty, data["count"], data["types"]
        )
        with transaction.atomic():
            quiz = Quiz.objects.create(
                owner=request.user,
                title=f"{data['topic'].title()} ({difficulty})",
                topic=data["topic"],
                difficulty=difficulty,
                source_text=source,
                ai_mode=metadata["mode"],
                ai_notice=metadata["notice"],
            )
            replace_questions(quiz, questions)
        return Response(
            {**self.get_serializer(quiz).data, "ai": metadata, "adaptive": decision}, status=201
        )

    def create(self, request):
        serializer = QuizWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        questions = data.pop("questions")
        data.pop("version", None)
        if not data.get("source_text"):
            raise ValidationError({"source_text": "Provide the study material for this quiz."})
        with transaction.atomic():
            quiz = Quiz.objects.create(owner=request.user, ai_mode="manual", **data)
            replace_questions(quiz, questions)
        return Response(self.get_serializer(quiz).data, status=201)

    def update(self, request, *args, **kwargs):
        quiz = self.get_object()
        self.owner_only(quiz)
        serializer = QuizWriteSerializer(data=request.data, partial=kwargs.get("partial", False))
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        with transaction.atomic():
            quiz = Quiz.objects.select_for_update().get(pk=quiz.pk)
            if data.pop("version", None) != quiz.version:
                raise Conflict("Send the current quiz version to prevent overwriting newer edits.")
            if quiz.attempts.exists():
                raise Conflict(
                    "A quiz with attempts is immutable. Generate a new quiz to revise it."
                )
            questions = data.pop("questions", None)
            for field, value in data.items():
                setattr(quiz, field, value)
            quiz.version += 1
            quiz.save()
            if questions is not None:
                replace_questions(quiz, questions)
        return Response(self.get_serializer(quiz).data)

    def destroy(self, request, *args, **kwargs):
        quiz = self.get_object()
        self.owner_only(quiz)
        with transaction.atomic():
            quiz = Quiz.objects.select_for_update().get(pk=quiz.pk)
            if quiz.attempts.exists():
                raise Conflict("Keep quizzes with attempts to preserve learning history.")
            quiz.delete()
        return Response(status=204)

    @action(
        detail=True, methods=["post"], throttle_classes=[ScopedRateThrottle], throttle_scope="ai"
    )
    def submit(self, request, pk=None):
        quiz = self.get_object()
        serializer = SubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            key = uuid.UUID(request.headers.get("Idempotency-Key", ""))
        except (ValueError, AttributeError) as exc:
            raise ValidationError(
                {
                    "Idempotency-Key": "Provide a UUID header; reuse it when retrying the same submission."
                }
            ) from exc
        attempt, created = submit_quiz(request.user, quiz, serializer.validated_data, key)
        return Response(AttemptSerializer(attempt).data, status=201 if created else 200)

    @action(
        detail=True, methods=["post"], throttle_classes=[ScopedRateThrottle], throttle_scope="ai"
    )
    def analyze(self, request, pk=None):
        quiz = self.get_object()
        attempt_id = request.data.get("attemptId")
        if attempt_id is not None and (type(attempt_id) is not int or attempt_id <= 0):
            raise ValidationError({"attemptId": "Provide a positive integer."})
        attempts = (
            quiz.attempts.filter(user=request.user)
            .select_related("quiz")
            .prefetch_related("answers")
        )
        attempt = get_object_or_404(attempts, pk=attempt_id) if attempt_id else attempts.first()
        if not attempt:
            raise ValidationError("Complete a quiz attempt before requesting analysis.")
        return Response({"attemptId": attempt.id, **analyze(attempt)})


class QuizAttemptViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AttemptSerializer

    def get_queryset(self):
        return (
            QuizAttempt.objects.filter(user=self.request.user)
            .select_related("quiz")
            .prefetch_related("answers")
        )


class UserProfileView(APIView):
    def get(self, request):
        recent = request.user.attempts.select_related("quiz").prefetch_related("answers")[:100]
        return Response(
            {
                "user": {"id": request.user.id, "username": request.user.username},
                "attempts": AttemptSerializer(recent, many=True).data,
                "totalAttempts": request.user.attempts.count(),
            }
        )


class RecommendationView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ai"

    def get(self, request):
        return Response(recommend(request.user, accessible_quizzes(request.user)))


class AdaptiveView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ai"

    def get(self, request):
        return Response(adaptive_difficulty(request.user))
