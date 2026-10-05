"""Study notes → a reviewed quiz → immutable attempts and answer snapshots."""

from django.conf import settings
from django.db import models

DIFFICULTIES = [(x, x.title()) for x in ("beginner", "intermediate", "advanced")]
QUESTION_TYPES = [(x, x) for x in ("multiple_choice", "short_answer")]


class StudyMaterial(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True)
    topic = models.CharField(max_length=100, db_index=True)
    title = models.CharField(max_length=180)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["topic", "id"]

    def __str__(self):
        return self.title


class Quiz(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True)
    title = models.CharField(max_length=180)
    topic = models.CharField(max_length=100, db_index=True)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTIES, db_index=True)
    status = models.CharField(
        max_length=12, choices=[("draft", "Draft"), ("published", "Published")], default="draft"
    )
    source_text = (
        models.TextField()
    )  # Snapshot: later note edits cannot change the grading context.
    ai_mode = models.CharField(max_length=20, default="mock")
    ai_notice = models.CharField(max_length=240, blank=True)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["owner", "status"])]

    def __str__(self):
        return self.title


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, related_name="questions", on_delete=models.CASCADE)
    position = models.PositiveSmallIntegerField()
    type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    text = models.TextField()
    options = models.JSONField(default=list)
    expected = models.TextField()
    source_quote = models.TextField(blank=True)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(fields=["quiz", "position"], name="unique_question_position")
        ]


class QuizAttempt(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="attempts", on_delete=models.CASCADE
    )
    quiz = models.ForeignKey(Quiz, related_name="attempts", on_delete=models.PROTECT)
    score = models.DecimalField(max_digits=5, decimal_places=2)
    correct_count = models.PositiveSmallIntegerField()
    total_questions = models.PositiveSmallIntegerField()
    time_spent = models.PositiveIntegerField(default=0)
    idempotency_key = models.UUIDField()
    payload_hash = models.CharField(max_length=64)
    ai_mode = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["user", "-created_at"])]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "idempotency_key"], name="unique_user_submission"
            ),
            models.CheckConstraint(
                condition=models.Q(score__gte=0, score__lte=100), name="score_range"
            ),
        ]


class UserAnswer(models.Model):
    attempt = models.ForeignKey(QuizAttempt, related_name="answers", on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.PROTECT)
    selected_answer = models.TextField(blank=True)
    expected = models.TextField()
    question_text = models.TextField()
    question_type = models.CharField(max_length=20)
    time_spent = models.PositiveIntegerField(default=0)
    verdict = models.CharField(max_length=12)
    credit = models.FloatField()
    justification = models.TextField()
    ai_mode = models.CharField(max_length=20)

    class Meta:
        ordering = ["question__position"]
        constraints = [
            models.UniqueConstraint(fields=["attempt", "question"], name="unique_attempt_answer"),
            models.CheckConstraint(
                condition=models.Q(credit__gte=0, credit__lte=1), name="credit_range"
            ),
        ]
