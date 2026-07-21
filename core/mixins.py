from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.shortcuts import redirect

from .models import User


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    required_role = None

    def test_func(self):
        if self.required_role is None:
            return False
        return self.request.user.role == self.required_role

    def handle_no_permission(self):
        user = self.request.user
        if user.is_authenticated:
            messages.error(
                self.request,
                'You do not have permission to access that page.',
            )
            return redirect(user.get_dashboard_url_name())
        return super().handle_no_permission()


class StudentRequiredMixin(RoleRequiredMixin):
    required_role = User.Role.STUDENT


class TeacherRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return user.is_approved_teacher

    def handle_no_permission(self):
        user = self.request.user
        if user.is_authenticated and user.is_teacher and not user.teacher_approved:
            return redirect('core:teacher_pending')
        if user.is_authenticated:
            messages.error(
                self.request,
                'You do not have permission to access that page.',
            )
            return redirect(user.get_dashboard_url_name())
        return super().handle_no_permission()
