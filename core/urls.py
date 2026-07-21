from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('manifest.webmanifest', views.manifest, name='manifest'),
    path('login/', views.RoleLoginView.as_view(), name='login'),
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path(
        'teacher/pending/',
        views.TeacherPendingView.as_view(),
        name='teacher_pending',
    ),
    path('logout/', views.RoleLogoutView.as_view(), name='logout'),
    path(
        'dashboard/student/',
        views.StudentDashboardView.as_view(),
        name='student_dashboard',
    ),
    path(
        'dashboard/teacher/',
        views.TeacherDashboardView.as_view(),
        name='teacher_dashboard',
    ),
    path(
        'dashboard/teacher/student/<int:student_id>/',
        views.TeacherStudentDetailView.as_view(),
        name='teacher_student_detail',
    ),
]
