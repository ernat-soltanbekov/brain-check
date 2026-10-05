from django.contrib import admin

from .models import Question, Quiz, QuizAttempt, StudyMaterial, UserAnswer

for model in (StudyMaterial, Quiz, Question, QuizAttempt, UserAnswer):
    admin.site.register(model)
