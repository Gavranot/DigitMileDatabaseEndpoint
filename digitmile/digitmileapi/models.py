from django.contrib.auth.models import User
from django.db import models

class School(models.Model):
    # id SERIAL PRIMARY KEY -> Django adds an AutoField 'id' by default
    name = models.CharField(max_length=255)  # VARCHAR NOT NULL
    municipality = models.CharField(max_length=255)  # VARCHAR NOT NULL

    def __str__(self):
        return self.name

class Teacher(models.Model):
    # Link to the built-in User model
    # This means each Teacher will have an associated User account for login, etc.
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='teacher_profile')

    # Existing fields - consider if full_name is still needed or if you'll rely on User.first_name and User.last_name
    full_name = models.CharField(max_length=255) # You might deprecate this later
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='teachers'
    )

    def __str__(self):
        # Prefer using the user's username or full name if available
        return self.user.get_full_name() or self.user.username

class Classroom(models.Model):
    # id SERIAL PRIMARY KEY -> Django adds an AutoField 'id' by default
    classroom_key = models.CharField(max_length=100, unique=True)  # VARCHAR NOT NULL UNIQUE
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,  # Corresponds to REFERENCES TEACHER(id)
                                   # If a Teacher is deleted, their Classrooms are also deleted.
        related_name='classrooms'  # Optional: for easier reverse access from Teacher
    ) # teacher_ref INTEGER NOT NULL

    def __str__(self):
        return f"{self.classroom_key} (Teacher: {self.teacher.full_name})"

class Student(models.Model):
    # id SERIAL PRIMARY KEY -> Django adds an AutoField 'id' by default
    full_name = models.CharField(max_length=255)  # VARCHAR NOT NULL
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,  # Corresponds to REFERENCES CLASSROOM(id)
                                   # If a Classroom is deleted, its Students are also deleted.
        related_name='students'    # Optional: for easier reverse access from Classroom
    ) # classroom_ref INTEGER NOT NULL

    def __str__(self):
        return self.full_name

class RunStatistics(models.Model):
    # id SERIAL PRIMARY KEY -> Django adds an AutoField 'id' by default
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,  # Corresponds to REFERENCES STUDENT(id)
                                   # If a Student is deleted, their RunStatistics are also deleted.
        related_name='run_statistics' # Optional: for easier reverse access from Student
    ) # student_ref INTEGER NOT NULL
    player_won = models.BooleanField() # BOOLEAN NOT NULL

    def __str__(self):
        return f"Run for {self.student.full_name} - Won: {self.player_won}"