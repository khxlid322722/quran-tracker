from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.generic import DetailView, FormView, TemplateView

from .forms import DailyLogForm, SignUpForm
from .mixins import StudentRequiredMixin, TeacherRequiredMixin
from .models import DailyLog, User


class RoleLoginView(LoginView):
    template_name = 'core/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy(self.request.user.get_dashboard_url_name())


class RoleLogoutView(LogoutView):
    next_page = reverse_lazy('core:login')


class SignUpView(FormView):
    template_name = 'core/signup.html'
    form_class = SignUpForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(request.user.get_dashboard_url_name())
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(
            self.request,
            f'Welcome, {user.display_name}! You have joined {user.teacher.display_name}\'s class.',
        )
        return redirect(user.get_dashboard_url_name())


class TeacherPendingView(LoginRequiredMixin, TemplateView):
    template_name = 'core/teacher_pending.html'

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return redirect('core:login')
        if user.is_approved_teacher:
            return redirect('core:teacher_dashboard')
        if not user.is_teacher:
            return redirect(user.get_dashboard_url_name())
        return super().dispatch(request, *args, **kwargs)


def home(request):
    if not request.user.is_authenticated:
        return redirect('core:login')
    return redirect(request.user.get_dashboard_url_name())


class StudentDashboardView(StudentRequiredMixin, TemplateView):
    template_name = 'core/student_dashboard.html'

    def get_today_log(self):
        return DailyLog.objects.filter(
            student=self.request.user,
            date=timezone.localdate(),
        ).first()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        today_log = self.get_today_log()
        context.update(
            {
                'page_title': 'Student Dashboard',
                'subtitle': f'Signed in as {self.request.user.display_name}',
                'today_log': today_log,
                'today': today,
                'form': kwargs.get('form', DailyLogForm(instance=today_log)),
                'recent_logs': DailyLog.objects.filter(
                    student=self.request.user,
                ).exclude(
                    date=today,
                ).order_by('-date')[:10],
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        today_log = self.get_today_log()
        form = DailyLogForm(request.POST, instance=today_log)

        if form.is_valid():
            log = form.save(commit=False)
            log.student = request.user
            if today_log:
                log.date = today_log.date
            else:
                log.date = timezone.localdate()
            log.save()

            if today_log:
                messages.success(request, 'Today’s log was updated successfully.')
            else:
                messages.success(request, 'Great work! Today’s Quran log was saved.')

            return redirect('core:student_dashboard')

        context = self.get_context_data(form=form)
        return self.render_to_response(context)


class TeacherDashboardView(TeacherRequiredMixin, TemplateView):
    template_name = 'core/teacher_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        students = self.request.user.students.filter(
            role=User.Role.STUDENT,
            is_active=True,
        ).order_by(
            'first_name',
            'last_name',
            'username',
        )
        logs_by_student_id = {
            log.student_id: log
            for log in DailyLog.objects.filter(date=today, student__in=students)
        }

        context.update(
            {
                'page_title': 'Teacher Dashboard',
                'subtitle': f'Daily overview for {today.strftime("%B %d, %Y")}',
                'today': today,
                'logged_count': sum(1 for log in logs_by_student_id.values() if log),
                'student_count': students.count(),
                'student_rows': [
                    {
                        'student': student,
                        'log': logs_by_student_id.get(student.id),
                    }
                    for student in students
                ],
            }
        )
        return context


class TeacherStudentDetailView(TeacherRequiredMixin, DetailView):
    model = User
    template_name = 'core/teacher_student_detail.html'
    context_object_name = 'student'
    pk_url_kwarg = 'student_id'

    def get_queryset(self):
        return self.request.user.students.filter(
            role=User.Role.STUDENT,
            is_active=True,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        log_dates = list(
            DailyLog.objects.filter(student=self.object)
            .values_list('date', flat=True)
            .order_by('-date')
            .distinct()
        )
        selected_date = self._get_selected_date(log_dates, today)
        selected_log = DailyLog.objects.filter(
            student=self.object,
            date=selected_date,
        ).first()
        today_log = DailyLog.objects.filter(
            student=self.object,
            date=today,
        ).first()

        context.update(
            {
                'today': today,
                'log_dates': log_dates,
                'selected_date': selected_date,
                'selected_log': selected_log,
                'total_logs': len(log_dates),
                'logged_today': today_log is not None,
            }
        )
        return context

    def _get_selected_date(self, log_dates, today):
        date_param = self.request.GET.get('date')
        if date_param:
            parsed = parse_date(date_param)
            if parsed and parsed in log_dates:
                return parsed

        if today in log_dates:
            return today
        if log_dates:
            return log_dates[0]
        return today
