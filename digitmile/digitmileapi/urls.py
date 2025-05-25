# myapi/urls.py
from django.urls import path
from .views import CheckClassroomKeyView, InsertLevelStatisticsView

urlpatterns = [
    path('checkClassroomKey/', CheckClassroomKeyView.as_view(), name='check_classroom_key'),
    path('insertLevelStatistics/', InsertLevelStatisticsView.as_view(), name='insert_level_statistics'),
]