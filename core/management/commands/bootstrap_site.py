import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create initial admin and teacher accounts on production if missing.'

    def handle(self, *args, **options):
        if os.environ.get('DJANGO_DEBUG', 'True').lower() == 'true':
            self.stdout.write('Skipping bootstrap in DEBUG mode.')
            return

        User = get_user_model()
        admin_username = os.environ.get('BOOTSTRAP_ADMIN_USERNAME', 'khalid1')
        admin_password = os.environ.get('BOOTSTRAP_ADMIN_PASSWORD')
        teacher_username = os.environ.get('BOOTSTRAP_TEACHER_USERNAME', 'teacher')
        teacher_password = os.environ.get('BOOTSTRAP_TEACHER_PASSWORD')

        if not admin_password:
            self.stdout.write(
                self.style.WARNING(
                    'BOOTSTRAP_ADMIN_PASSWORD not set. Skipping account bootstrap.',
                )
            )
            return

        admin, created = User.objects.get_or_create(
            username=admin_username,
            defaults={
                'email': f'{admin_username}@example.com',
                'is_staff': True,
                'is_superuser': True,
                'role': User.Role.TEACHER,
                'teacher_approved': False,
            },
        )
        admin.set_password(admin_password)
        admin.is_staff = True
        admin.is_superuser = True
        admin.is_active = True
        admin.role = User.Role.TEACHER
        admin.teacher_approved = False
        admin.teacher = None
        admin.save()
        action = 'Created' if created else 'Updated'
        self.stdout.write(self.style.SUCCESS(f'{action} admin user "{admin_username}".'))

        if teacher_password:
            teacher, teacher_created = User.objects.get_or_create(
                username=teacher_username,
                defaults={
                    'email': f'{teacher_username}@example.com',
                    'role': User.Role.TEACHER,
                    'teacher_approved': True,
                },
            )
            teacher.set_password(teacher_password)
            teacher.role = User.Role.TEACHER
            teacher.teacher_approved = True
            teacher.is_staff = False
            teacher.is_superuser = False
            teacher.is_active = True
            teacher.teacher = None
            teacher.save()
            teacher_action = 'Created' if teacher_created else 'Updated'
            self.stdout.write(
                self.style.SUCCESS(
                    f'{teacher_action} approved teacher "{teacher_username}".',
                )
            )

            User.objects.filter(
                role=User.Role.STUDENT,
                teacher__isnull=True,
                is_active=True,
            ).update(teacher=teacher)

        self.stdout.write(self.style.SUCCESS('Bootstrap complete.'))
