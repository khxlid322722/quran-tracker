from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import DailyLog, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'username',
        'email',
        'role',
        'teacher',
        'teacher_approved',
        'is_staff',
        'is_active',
    )
    list_filter = ('role', 'teacher_approved', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            'Quran Tracker',
            {
                'fields': ('role', 'teacher', 'teacher_approved'),
                'description': (
                    'Students are assigned to a teacher. Teacher accounts must be '
                    'approved here before they can access the teacher dashboard.'
                ),
            },
        ),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Quran Tracker', {'fields': ('role', 'teacher', 'teacher_approved')}),
    )

    def save_model(self, request, obj, form, change):
        if obj.role == User.Role.STUDENT:
            obj.teacher_approved = False
            if not obj.teacher_id:
                class_teacher = User.get_class_teacher()
                if class_teacher:
                    obj.teacher = class_teacher
        elif obj.role == User.Role.TEACHER:
            obj.teacher = None
        super().save_model(request, obj, form, change)

        if obj.role == User.Role.TEACHER and obj.teacher_approved:
            approved_teachers = User.objects.filter(
                role=User.Role.TEACHER,
                teacher_approved=True,
                is_active=True,
            )
            if approved_teachers.count() == 1:
                User.objects.filter(
                    role=User.Role.STUDENT,
                    teacher__isnull=True,
                    is_active=True,
                ).update(teacher=obj)


@admin.register(DailyLog)
class DailyLogAdmin(admin.ModelAdmin):
    list_display = (
        'student',
        'date',
        'reading_type',
        'minutes_read',
        'amount_read',
        'unit',
    )
    list_filter = ('date', 'reading_type', 'unit')
    search_fields = ('student__username', 'student__first_name', 'student__last_name')
    date_hierarchy = 'date'
