from email.policy import default

from django.contrib.auth.models import User
from django.db import models

class School(models.Model):
    name = models.CharField(max_length=255)
    municipality = models.CharField(max_length=255)

    class Meta:
        unique_together = [['name', 'municipality']] # <--- ADDED

    def __str__(self):
        return self.name

class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='teacher_profile')
    full_name = models.CharField(max_length=255)
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='teachers'
    )

    class Meta:
        unique_together = [['full_name', 'school']] # <--- ADDED

    def __str__(self):
        if self.user:
            return self.user.get_full_name() or self.user.username
        return self.full_name

class Classroom(models.Model):
    classroom_key = models.CharField(max_length=100, unique=True)
    # Note: Your SQL said class_name, your Django model says classroom_name.
    # Django will create/use classroom_name.
    classroom_name = models.CharField(max_length=255, default="ClassroomNamePlaceholder")
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name='classrooms'
    )

    def __str__(self):
        return f"{self.classroom_key} (Teacher: {self.teacher.full_name})"

class Student(models.Model):
    full_name = models.CharField(max_length=255)
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,
        related_name='students'
    )

    class Meta:
        unique_together = [['full_name', 'classroom']] # <--- ADDED

    def __str__(self):
        return self.full_name

class RunStatistics(models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='run_statistics'
    )
    player_won = models.BooleanField()

    def __str__(self):
        return f"Run for {self.student.full_name} - Won: {self.player_won}"