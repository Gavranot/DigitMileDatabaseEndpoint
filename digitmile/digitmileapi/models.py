from django.contrib.auth.models import User
from django.db import models

class SchoolManager(models.Manager):
    """Custom manager to easily filter schools by status"""
    def approved(self):
        return self.filter(status='APPROVED')

    def pending(self):
        return self.filter(status='PENDING')

    def rejected(self):
        return self.filter(status='REJECTED')

class School(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    # Basic school information
    name = models.CharField(max_length=255)
    municipality = models.CharField(max_length=255)
    region = models.CharField(max_length=255, default="RegionPlaceholder")
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    address = models.CharField(max_length=500, blank=True, default='')
    google_maps_address = models.CharField(max_length=500, blank=True, default='')
    website = models.URLField(max_length=255, blank=True, default='')

    # Contact person information (who registered the school)
    contact_person_name = models.CharField(max_length=255, blank=True, default='')
    contact_person_email = models.EmailField(blank=True, default='')
    contact_person_phone = models.CharField(max_length=50, blank=True, default='')

    # Official school information
    director_name = models.CharField(max_length=255, blank=True, default='')
    director_email = models.EmailField(blank=True, default='')
    school_email = models.EmailField(blank=True, default='')
    school_phone = models.CharField(max_length=50, blank=True, default='')

    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    objects = SchoolManager()

    class Meta:
        unique_together = [['name', 'municipality', 'region']]

    def __str__(self):
        status_badge = f" [{self.get_status_display()}]" if self.status != 'APPROVED' else ""
        return f"{self.name} - {self.municipality}, {self.region}{status_badge}"

    @property
    def is_pending(self):
        return self.status == 'PENDING'

    @property
    def is_approved(self):
        return self.status == 'APPROVED'

    def save(self, *args, **kwargs):
        """Override save to handle status changes to REJECTED with cascade logic"""
        # Check if this is an existing instance and status is changing to REJECTED
        if self.pk:
            try:
                old_instance = School.objects.get(pk=self.pk)
                if old_instance.status != 'REJECTED' and self.status == 'REJECTED':
                    # Need to save first, then cascade
                    # But we need to track teachers before save
                    teachers_to_reject = []

                    # Find all teachers assigned to this school
                    from .models import Teacher, Classroom
                    teachers_at_school = Teacher.objects.filter(schools=self)

                    for teacher in teachers_at_school:
                        # Check if this is the teacher's ONLY school
                        if teacher.schools.count() == 1:
                            teachers_to_reject.append(teacher)

                    # Save school first
                    super().save(*args, **kwargs)

                    # Now cascade to teachers
                    for teacher in teachers_to_reject:
                        # Delete all classrooms (cascades to students and run statistics)
                        Classroom.objects.filter(teacher=teacher).delete()
                        # Set teacher status to REJECTED
                        teacher.status = 'REJECTED'
                        # Save without triggering cascade again
                        Teacher.objects.filter(pk=teacher.pk).update(status='REJECTED')

                    return  # Already saved above
            except School.DoesNotExist:
                pass

        super().save(*args, **kwargs)


class TeacherSchoolAssignment(models.Model):
    """Through model to track teacher assignments to schools with years at each school"""
    teacher = models.ForeignKey('Teacher', on_delete=models.CASCADE, related_name='school_assignments')
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='teacher_assignments')
    years_at_school = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = [['teacher', 'school']]

    def __str__(self):
        return f"{self.teacher.full_name} at {self.school.name} ({self.years_at_school} years)"

class TeacherManager(models.Manager):
    """Custom manager to easily filter teachers by status"""
    def approved(self):
        return self.filter(status='APPROVED')

    def pending(self):
        return self.filter(status='PENDING')

    def rejected(self):
        return self.filter(status='REJECTED')

class Teacher(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    # User account (only created when approved)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='teacher_profile')

    # Basic teacher information
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True, default='noemail@example.com')
    phone_number = models.CharField(max_length=50, blank=True, default='')
    years_teaching = models.IntegerField(null=True, blank=True, help_text="Total years of teaching experience")

    # School assignments (can include pending schools)
    schools = models.ManyToManyField(
        School,
        through='TeacherSchoolAssignment',
        related_name='teachers'
    )

    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    objects = TeacherManager()

    def __str__(self):
        status_badge = f" [{self.get_status_display()}]" if self.status != 'APPROVED' else ""
        if self.user:
            return f"{self.user.get_full_name() or self.user.username}{status_badge}"
        return f"{self.full_name}{status_badge}"

    @property
    def primary_school(self):
        """Returns the first approved school (for backwards compatibility)"""
        return self.schools.filter(status='APPROVED').first()

    @property
    def is_pending(self):
        return self.status == 'PENDING'

    @property
    def is_approved(self):
        return self.status == 'APPROVED'

    def save(self, *args, **kwargs):
        """Override save to handle status changes to REJECTED with cascade logic"""
        # Check if this is an existing instance and status is changing to REJECTED
        if self.pk:
            try:
                old_instance = Teacher.objects.get(pk=self.pk)
                if old_instance.status != 'REJECTED' and self.status == 'REJECTED':
                    # Save teacher first
                    super().save(*args, **kwargs)

                    # Delete all classrooms (cascades to students and run statistics)
                    from .models import Classroom
                    Classroom.objects.filter(teacher=self).delete()

                    return  # Already saved above
            except Teacher.DoesNotExist:
                pass

        super().save(*args, **kwargs)

class Classroom(models.Model):
    classroom_key = models.CharField(max_length=100, unique=True)
    classroom_name = models.CharField(max_length=255, default="ClassroomNamePlaceholder")
    grade = models.IntegerField(null=True, blank=True, help_text='Grade level of the classroom')
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name='classrooms'
    )
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='classrooms',
        null=True,
        blank=True,
        help_text='The school where this classroom is located'
    )

    class Meta:
        unique_together = [['classroom_key', 'school']]

    def __str__(self):
        return f"{self.classroom_key} at {self.school.name} (Teacher: {self.teacher.full_name})"

    def clean(self):
        """Validate that the teacher is assigned to this school"""
        from django.core.exceptions import ValidationError
        if self.teacher and self.school:
            if not self.teacher.schools.filter(id=self.school.id).exists():
                raise ValidationError(f"Teacher {self.teacher.full_name} is not assigned to {self.school.name}")

class Student(models.Model):
    full_name = models.CharField(max_length=255)
    date_of_birth = models.DateField(null=True, blank=True, help_text='Student date of birth')
    grade = models.IntegerField(null=True, blank=True, help_text='Student grade level')
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
    level = models.IntegerField(null=True, blank=True)
    score = models.IntegerField(null=True, blank=True)
    place = models.IntegerField(null=True, blank=True)
    correct_moves = models.IntegerField(null=True, blank=True)
    wrong_moves = models.IntegerField(null=True, blank=True)
    time_elapsed = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"Run for {self.student.full_name} - Level: {self.level} - Won: {self.player_won}"