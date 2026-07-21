from django.db import IntegrityError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import DailyLog, User


def create_approved_teacher(username='teacher', password='testpass123', **kwargs):
    return User.objects.create_user(
        username=username,
        password=password,
        role=User.Role.TEACHER,
        teacher_approved=True,
        **kwargs,
    )


def create_student(username, teacher, password='testpass123', **kwargs):
    return User.objects.create_user(
        username=username,
        password=password,
        role=User.Role.STUDENT,
        teacher=teacher,
        **kwargs,
    )


class AuthenticationFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.teacher = create_approved_teacher()
        self.student = create_student('student', self.teacher)

    def test_login_redirects_student_to_student_dashboard(self):
        response = self.client.post(
            reverse('core:login'),
            {'username': 'student', 'password': 'testpass123'},
        )
        self.assertRedirects(
            response,
            reverse('core:student_dashboard'),
        )

    def test_login_redirects_teacher_to_teacher_dashboard(self):
        response = self.client.post(
            reverse('core:login'),
            {'username': 'teacher', 'password': 'testpass123'},
        )
        self.assertRedirects(
            response,
            reverse('core:teacher_dashboard'),
        )

    def test_unapproved_teacher_is_sent_to_pending_page(self):
        pending_teacher = User.objects.create_user(
            username='pending',
            password='testpass123',
            role=User.Role.TEACHER,
            teacher_approved=False,
        )
        response = self.client.post(
            reverse('core:login'),
            {'username': 'pending', 'password': 'testpass123'},
        )
        self.assertRedirects(response, reverse('core:teacher_pending'))

    def test_student_cannot_access_teacher_dashboard(self):
        self.client.login(username='student', password='testpass123')
        response = self.client.get(reverse('core:teacher_dashboard'))
        self.assertRedirects(
            response,
            reverse('core:student_dashboard'),
        )

    def test_teacher_cannot_access_student_dashboard(self):
        self.client.login(username='teacher', password='testpass123')
        response = self.client.get(reverse('core:student_dashboard'))
        self.assertRedirects(
            response,
            reverse('core:teacher_dashboard'),
        )

    def test_anonymous_user_is_sent_to_login(self):
        response = self.client.get(reverse('core:student_dashboard'))
        self.assertRedirects(
            response,
            f"{reverse('core:login')}?next={reverse('core:student_dashboard')}",
        )

    def test_logout_returns_to_login(self):
        self.client.login(username='student', password='testpass123')
        response = self.client.post(reverse('core:logout'))
        self.assertRedirects(response, reverse('core:login'))


class SignUpTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.teacher = create_approved_teacher()

    def test_student_signup_assigns_class_teacher(self):
        response = self.client.post(
            reverse('core:signup'),
            {
                'username': 'newstudent',
                'first_name': 'Yusuf',
                'last_name': '',
                'password1': 'strongpass123',
                'password2': 'strongpass123',
            },
        )
        self.assertRedirects(response, reverse('core:student_dashboard'))
        student = User.objects.get(username='newstudent')
        self.assertEqual(student.role, User.Role.STUDENT)
        self.assertEqual(student.teacher, self.teacher)

    def test_signup_blocked_without_approved_teacher(self):
        self.teacher.teacher_approved = False
        self.teacher.save()
        response = self.client.post(
            reverse('core:signup'),
            {
                'username': 'blocked',
                'first_name': 'No',
                'last_name': 'Teacher',
                'password1': 'strongpass123',
                'password2': 'strongpass123',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='blocked').exists())


class DailyLogTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.teacher = create_approved_teacher()
        self.student = create_student(
            'student',
            self.teacher,
            first_name='Amina',
        )
        self.other_student = create_student('student2', self.teacher)
        self.log_data = {
            'reading_type': DailyLog.ReadingType.QURAN_READING,
            'minutes_read': 20,
            'amount_read': 2,
            'unit': DailyLog.Unit.PAGES,
            'notes': 'Completed after Maghrib.',
        }

    def test_student_can_submit_today_log(self):
        self.client.login(username='student', password='testpass123')
        response = self.client.post(
            reverse('core:student_dashboard'),
            self.log_data,
        )

        self.assertRedirects(response, reverse('core:student_dashboard'))
        log = DailyLog.objects.get(student=self.student)
        self.assertEqual(log.date, timezone.localdate())
        self.assertEqual(log.minutes_read, 20)
        self.assertEqual(log.amount_display, '2 Pages')

    def test_student_dashboard_shows_existing_log_instead_of_empty_state(self):
        DailyLog.objects.create(student=self.student, **self.log_data)
        self.client.login(username='student', password='testpass123')
        response = self.client.get(reverse('core:student_dashboard'))

        self.assertContains(response, 'Today’s reading is logged.')
        self.assertContains(response, 'Edit today’s log')
        self.assertContains(response, 'Quran Reading')

    def test_student_can_update_today_log(self):
        log = DailyLog.objects.create(student=self.student, **self.log_data)
        self.client.login(username='student', password='testpass123')

        response = self.client.post(
            reverse('core:student_dashboard'),
            {
                **self.log_data,
                'minutes_read': 30,
                'notes': 'Updated entry.',
            },
        )

        self.assertRedirects(response, reverse('core:student_dashboard'))
        log.refresh_from_db()
        self.assertEqual(log.minutes_read, 30)
        self.assertEqual(log.notes, 'Updated entry.')
        self.assertEqual(DailyLog.objects.filter(student=self.student).count(), 1)

    def test_duplicate_log_for_same_day_is_prevented(self):
        DailyLog.objects.create(student=self.student, **self.log_data)

        with self.assertRaises(IntegrityError):
            DailyLog.objects.create(
                student=self.student,
                date=timezone.localdate(),
                reading_type=DailyLog.ReadingType.MEMORIZATION,
                minutes_read=10,
                amount_read=5,
                unit=DailyLog.Unit.AYAHS,
            )

    def test_teacher_dashboard_shows_only_their_students(self):
        DailyLog.objects.create(student=self.student, **self.log_data)
        other_teacher = create_approved_teacher(username='otherteacher')
        outsider = create_student('outsider', other_teacher, first_name='Outside')

        self.client.login(username='teacher', password='testpass123')
        response = self.client.get(reverse('core:teacher_dashboard'))

        self.assertContains(response, 'Amina')
        self.assertContains(response, 'student2')
        self.assertNotContains(response, 'Outside')

    def test_student_can_log_again_on_a_new_day(self):
        yesterday = timezone.localdate() - timezone.timedelta(days=1)
        DailyLog.objects.create(student=self.student, date=yesterday, **self.log_data)

        self.client.login(username='student', password='testpass123')
        response = self.client.get(reverse('core:student_dashboard'))

        self.assertContains(response, 'Submit today’s log')
        self.assertNotContains(response, 'Today’s reading is logged.')
        response = self.client.post(
            reverse('core:student_dashboard'),
            self.log_data,
        )
        self.assertRedirects(response, reverse('core:student_dashboard'))
        self.assertEqual(DailyLog.objects.filter(student=self.student).count(), 2)

    def test_editing_today_log_does_not_change_its_date(self):
        today = timezone.localdate()
        log = DailyLog.objects.create(student=self.student, date=today, **self.log_data)
        self.client.login(username='student', password='testpass123')

        self.client.post(
            reverse('core:student_dashboard'),
            {**self.log_data, 'minutes_read': 45},
        )

        log.refresh_from_db()
        self.assertEqual(log.date, today)
        self.assertEqual(log.minutes_read, 45)

    def test_teacher_can_view_student_history(self):
        DailyLog.objects.create(student=self.student, **self.log_data)
        self.client.login(username='teacher', password='testpass123')
        response = self.client.get(
            reverse('core:teacher_student_detail', args=[self.student.id]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Select day')
        self.assertContains(response, 'Quran Reading')

    def test_teacher_can_filter_student_history_by_date(self):
        yesterday = timezone.localdate() - timezone.timedelta(days=1)
        DailyLog.objects.create(student=self.student, date=yesterday, **self.log_data)
        today_log = DailyLog.objects.create(
            student=self.student,
            reading_type=DailyLog.ReadingType.MEMORIZATION,
            minutes_read=15,
            amount_read=3,
            unit=DailyLog.Unit.AYAHS,
            notes='Today entry.',
        )

        self.client.login(username='teacher', password='testpass123')
        response = self.client.get(
            reverse('core:teacher_student_detail', args=[self.student.id]),
            {'date': yesterday.isoformat()},
        )

        self.assertContains(response, yesterday.isoformat())
        self.assertContains(response, 'Quran Reading')
        self.assertNotContains(response, 'Today entry.')

    def test_teacher_cannot_view_other_teachers_student(self):
        other_teacher = create_approved_teacher(username='otherteacher')
        outsider = create_student('outsider', other_teacher)

        self.client.login(username='teacher', password='testpass123')
        response = self.client.get(
            reverse('core:teacher_student_detail', args=[outsider.id]),
        )

        self.assertEqual(response.status_code, 404)
