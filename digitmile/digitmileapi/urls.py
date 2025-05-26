# myapi/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CheckClassroomKeyView,
    InsertLevelStatisticsView,
    teacher_registration_view,
    TeacherStudentViewSet,
    TeacherClassroomListView,
    TeacherSchoolView,
    TeacherRunStatisticsListView # Added Run Statistics List View import
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
    path('register/teacher/', teacher_registration_view, name='teacher_register'),
    path('teacher/classrooms/', TeacherClassroomListView.as_view(), name='teacher-classrooms-list'),
    path('teacher/school/', TeacherSchoolView.as_view(), name='teacher-school-detail'),
    path('teacher/run-statistics/', TeacherRunStatisticsListView.as_view(), name='teacher-run-statistics-list'), # New URL for teacher's run statistics

    # Router URLs for ViewSets
    path('', include(router.urls)),
]