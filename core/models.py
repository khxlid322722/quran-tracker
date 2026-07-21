from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = 'student', 'Student'
        TEACHER = 'teacher', 'Teacher'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
    )
    teacher = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students',
        limit_choices_to={'role': Role.TEACHER},
    )
    teacher_approved = models.BooleanField(
        default=False,
        help_text='Only admin can approve teacher accounts.',
    )

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_teacher(self):
        return self.role == self.Role.TEACHER

    @property
    def is_approved_teacher(self):
        return self.is_teacher and self.teacher_approved

    @classmethod
    def get_class_teacher(cls):
        return cls.objects.filter(
            role=cls.Role.TEACHER,
            teacher_approved=True,
            is_active=True,
        ).first()

    def get_dashboard_url_name(self):
        if self.is_superuser:
            return 'admin:index'
        if self.is_student:
            return 'core:student_dashboard'
        if self.is_approved_teacher:
            return 'core:teacher_dashboard'
        if self.is_teacher:
            return 'core:teacher_pending'
        return 'core:login'

    @property
    def display_name(self):
        full_name = self.get_full_name().strip()
        return full_name or self.username

    def clean(self):
        super().clean()
        if self.is_student and self.teacher_id:
            if self.teacher.role != self.Role.TEACHER:
                raise ValidationError({'teacher': 'Assigned user must be a teacher.'})
            if not self.teacher.teacher_approved:
                raise ValidationError({'teacher': 'Assigned teacher must be approved.'})
        if self.is_teacher and self.teacher_id:
            raise ValidationError({'teacher': 'Teachers cannot be assigned to a teacher.'})


class DailyLog(models.Model):
    class ReadingType(models.TextChoices):
        MEMORIZATION = 'memorization', 'Memorization'
        QURAN_READING = 'quran_reading', 'Quran Reading'
        QAIDA_BOOK = 'qaida_book', 'Qaida/Book Reading'

    class Unit(models.TextChoices):
        PAGES = 'pages', 'Pages'
        AYAHS = 'ayahs', 'Ayahs'

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='daily_logs',
        limit_choices_to={'role': User.Role.STUDENT},
    )
    date = models.DateField(default=timezone.localdate)
    reading_type = models.CharField(max_length=20, choices=ReadingType.choices)
    minutes_read = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    amount_read = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit = models.CharField(max_length=10, choices=Unit.choices)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-date', '-pk']
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'date'],
                name='unique_daily_log_per_student',
            ),
        ]

    def __str__(self):
        return f'{self.student.display_name} · {self.date}'

    @property
    def amount_display(self):
        return f'{self.amount_read} {self.get_unit_display()}'
