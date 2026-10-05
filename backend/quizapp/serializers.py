from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import (
    DIFFICULTIES,
    QUESTION_TYPES,
    Question,
    Quiz,
    QuizAttempt,
    StudyMaterial,
    UserAnswer,
)

User = get_user_model()


def normalize_topic(value):
    return " ".join(value.strip().casefold().split())


class RegisterSerializer(serializers.Serializer):
    username = serializers.RegexField(r"^[A-Za-z0-9_]{3,30}$")
    password = serializers.CharField(write_only=True, max_length=128, trim_whitespace=False)

    def validate_username(self, value):
        value = value.lower()
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate(self, attrs):
        try:
            validate_password(attrs["password"], User(username=attrs["username"]))
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128, trim_whitespace=False)


class MaterialSerializer(serializers.ModelSerializer):
    content = serializers.CharField(min_length=30, max_length=20000, required=False)
    file = serializers.FileField(write_only=True, required=False)

    class Meta:
        model = StudyMaterial
        fields = ["id", "topic", "title", "content", "file", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_topic(self, value):
        return normalize_topic(value)

    def validate(self, attrs):
        upload = attrs.pop("file", None)
        if upload:
            if attrs.get("content"):
                raise serializers.ValidationError("Use either text or a file, not both.")
            if upload.size > 100_000 or not upload.name.lower().endswith((".txt", ".md")):
                raise serializers.ValidationError(
                    "Upload a UTF-8 .txt or .md file, at most 100 KB."
                )
            try:
                attrs["content"] = upload.read().decode("utf-8-sig").strip()
            except UnicodeDecodeError as exc:
                raise serializers.ValidationError("The file must be UTF-8 text.") from exc
        content = attrs.get("content", "")
        if not 30 <= len(content) <= 20000 or "\x00" in content:
            raise serializers.ValidationError(
                {"content": "Provide 30–20,000 characters of readable study notes."}
            )
        return attrs


class GenerateSerializer(serializers.Serializer):
    topic = serializers.CharField(max_length=100)
    difficulty = serializers.ChoiceField(choices=DIFFICULTIES, default="beginner")
    count = serializers.IntegerField(min_value=1, max_value=10, default=5)
    types = serializers.ListField(
        child=serializers.ChoiceField(choices=QUESTION_TYPES),
        min_length=1,
        max_length=2,
        default=["multiple_choice", "short_answer"],
    )
    adaptive = serializers.BooleanField(default=False)

    def validate_topic(self, value):
        return normalize_topic(value)

    def validate(self, attrs):
        if len(set(attrs["types"])) != len(attrs["types"]) or attrs["count"] < len(attrs["types"]):
            raise serializers.ValidationError(
                "Choose distinct types and at least one question per type."
            )
        return attrs


class QuestionWriteSerializer(serializers.ModelSerializer):
    text = serializers.CharField(max_length=2000)
    expected = serializers.CharField(max_length=2000)
    source_quote = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    options = serializers.ListField(
        child=serializers.CharField(max_length=2000), max_length=6, default=list
    )

    class Meta:
        model = Question
        fields = ["type", "text", "options", "expected", "source_quote"]

    def validate(self, attrs):
        required = {"type", "text", "expected"}
        if not required.issubset(attrs):
            raise serializers.ValidationError(
                "Each replacement question needs type, text and expected."
            )
        options = attrs.setdefault("options", [])
        if attrs["type"] == "multiple_choice":
            if (
                len(options) < 2
                or len(set(x.casefold() for x in options)) != len(options)
                or attrs["expected"] not in options
            ):
                raise serializers.ValidationError(
                    "Provide 2–6 distinct options and an expected answer matching one option exactly."
                )
        elif options:
            raise serializers.ValidationError("Short answers must have an empty options array.")
        return attrs


class QuizWriteSerializer(serializers.ModelSerializer):
    questions = QuestionWriteSerializer(many=True, min_length=1, max_length=10)
    version = serializers.IntegerField(min_value=1, required=False)
    source_text = serializers.CharField(min_length=30, max_length=20000, required=False)

    class Meta:
        model = Quiz
        fields = ["title", "topic", "difficulty", "status", "questions", "version", "source_text"]

    def validate_topic(self, value):
        return normalize_topic(value)

    def validate(self, attrs):
        questions = attrs.get("questions")
        if questions and len({q["text"].casefold() for q in questions}) != len(questions):
            raise serializers.ValidationError("Question texts must be distinct.")
        return attrs


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ["id", "type", "text", "options", "expected", "source_quote"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not self.context.get("review"):
            data.pop("expected")
            data.pop("source_quote")
        return data


class QuizSerializer(serializers.ModelSerializer):
    quizId = serializers.IntegerField(source="id", read_only=True)
    questions = QuestionSerializer(many=True, read_only=True)
    questionCount = serializers.SerializerMethodField()
    editable = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = [
            "id",
            "quizId",
            "title",
            "topic",
            "difficulty",
            "status",
            "questions",
            "questionCount",
            "ai_mode",
            "ai_notice",
            "version",
            "created_at",
            "editable",
        ]

    def get_questionCount(self, obj):
        return obj.questions.count()

    def get_editable(self, obj):
        request = self.context.get("request")
        return bool(request and obj.owner_id == request.user.id and not obj.attempts.exists())


class AnswerInputSerializer(serializers.Serializer):
    questionId = serializers.IntegerField(min_value=1)
    selectedAnswer = serializers.CharField(max_length=4000, allow_blank=True, trim_whitespace=False)
    timeSpent = serializers.IntegerField(min_value=0, max_value=86400, default=0)


class SubmitSerializer(serializers.Serializer):
    quizId = serializers.IntegerField(min_value=1, required=False)
    answers = AnswerInputSerializer(many=True, min_length=1, max_length=10)

    def validate_answers(self, answers):
        ids = [a["questionId"] for a in answers]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("Each question must appear exactly once.")
        return answers


class UserAnswerSerializer(serializers.ModelSerializer):
    questionId = serializers.IntegerField(source="question_id")
    question = serializers.CharField(source="question_text")
    type = serializers.CharField(source="question_type")
    selectedAnswer = serializers.CharField(source="selected_answer")
    timeSpent = serializers.IntegerField(source="time_spent")
    score = serializers.FloatField(source="credit")

    class Meta:
        model = UserAnswer
        fields = [
            "questionId",
            "question",
            "type",
            "selectedAnswer",
            "expected",
            "timeSpent",
            "verdict",
            "score",
            "justification",
            "ai_mode",
        ]


class AttemptSerializer(serializers.ModelSerializer):
    quizId = serializers.IntegerField(source="quiz_id")
    title = serializers.CharField(source="quiz.title")
    topic = serializers.CharField(source="quiz.topic")
    difficulty = serializers.CharField(source="quiz.difficulty")
    score = serializers.FloatField()
    answers = UserAnswerSerializer(many=True)

    class Meta:
        model = QuizAttempt
        fields = [
            "id",
            "quizId",
            "title",
            "topic",
            "difficulty",
            "score",
            "correct_count",
            "total_questions",
            "time_spent",
            "created_at",
            "ai_mode",
            "answers",
        ]
