# myapi/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CheckClassroomKeyView,
    InsertLevelStatisticsView,
    pending_registrations_view,
    approve_school,
    reject_school,
    approve_teacher,
    reject_teacher,
    TeacherStudentViewSet,
    TeacherClassroomListView,
    TeacherSchoolView,
    TeacherRunStatisticsListView
)

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'teacher/students', TeacherStudentViewSet, basename='teacher-student')

# The API URLs are now determined automatically by the router for TeacherStudentViewSet.
# urlpatterns will include both the manually defined paths and the router's paths.
urlpatterns = [
    # Manually defined paths
    path('checkClassroomKey/', CheckClassroomKeyView.as_view(), name='check_classroom_key'),
    path('insertLevelStatistics/', InsertLevelStatisticsView.as_view(), name='insert_level_statistics'),
    path('pending-registrations/', pending_registrations_view, name='pending_registrations'),
    path('approve-school/<int:school_id>/', approve_school, name='approve_school'),
    path('reject-school/<int:school_id>/', reject_school, name='reject_school'),
    path('approve-teacher/<int:teacher_id>/', approve_teacher, name='approve_teacher'),
    path('reject-teacher/<int:teacher_id>/', reject_teacher, name='reject_teacher'),
    path('teacher/classrooms/', TeacherClassroomListView.as_view(), name='teacher-classrooms-list'),
    path('teacher/school/', TeacherSchoolView.as_view(), name='teacher-school-detail'),
    path('teacher/run-statistics/', TeacherRunStatisticsListView.as_view(), name='teacher-run-statistics-list'), # New URL for teacher's run statistics

    # Router URLs for ViewSets
    path('', include(router.urls)),
]