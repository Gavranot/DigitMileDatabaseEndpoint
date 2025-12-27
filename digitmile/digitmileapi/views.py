# myapi/views.py
from rest_framework import generics # For ListAPIView
from .serializers import ClassroomBasicSerializer # To serialize classroom data
from .serializers import SchoolSerializer # Ensure SchoolSerializer is imported
from .serializers import RunStatisticsSerializer # Ensure RunStatisticsSerializer is imported
from rest_framework import viewsets, permissions
from .serializers import TeacherStudentManagementSerializer # Add this new serializer
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse_lazy
from .forms import SchoolRegistrationForm, TeacherRegistrationForm
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Classroom, Student, Teacher, School, RunStatistics, TeacherSchoolAssignment
from .serializers import (
    CheckClassroomResponseSerializer,
    LevelStatisticsInputSerializer,
    RunStatisticsSerializer # Import if you use it for creation validation/response
)
from django.core.mail import send_mail
from django.conf import settings
import logging

# Set up logger for email operations
logger = logging.getLogger(__name__)

def send_school_approval_email(school):
    """Send approval notification email to school contact person"""
    logger.info(f"Attempting to send approval email to school: {school.name} ({school.contact_person_email})")

    subject = f'School Registration Approved: {school.name}'
    message = f'''Dear {school.contact_person_name or 'School Administrator'},

Your school registration has been approved!

School Details:
- Name: {school.name}
- Municipality: {school.municipality}
- Region: {school.region}
- Address: {school.address}

You can now proceed with registering teachers for your school.

Best regards,
DigitMile Team
'''

    # Log email configuration
    logger.info(f"Email backend: {settings.EMAIL_BACKEND}")
    logger.info(f"Email host: {settings.EMAIL_HOST}")
    logger.info(f"From email: {settings.DEFAULT_FROM_EMAIL}")
    logger.info(f"To email: {school.contact_person_email}")

    try:
        result = send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [school.contact_person_email],
            fail_silently=False,
        )
        logger.info(f"Email sent successfully to {school.contact_person_email}. Result: {result}")

        # Warn if using console backend (emails won't actually be sent)
        if 'console' in settings.EMAIL_BACKEND.lower():
            logger.warning(
                f"⚠️  Using console backend - email was printed to console but NOT sent to inbox. "
                f"To send real emails, configure SMTP settings in .env"
            )
    except Exception as e:
        logger.error(f"Failed to send school approval email to {school.contact_person_email}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.exception("Full traceback:")

def send_teacher_approval_email(email, username, password, teacher):
    """Send approval notification email with credentials to teacher"""
    logger.info(f"Attempting to send approval email to teacher: {teacher.full_name} ({email})")

    subject = 'Teacher Registration Approved - Login Credentials'
    message = f'''Dear {teacher.full_name},

Your teacher registration has been approved!

Your login credentials:
- Username: {username}
- Password: {password}

Please login at: {settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'your login URL'}/admin/

For security reasons, please change your password after your first login.

Schools you're assigned to:
{chr(10).join([f"- {assignment.school.name} ({assignment.years_at_school} years)" for assignment in teacher.school_assignments.all()])}

Best regards,
DigitMile Team
'''

    # Log email configuration
    logger.info(f"Email backend: {settings.EMAIL_BACKEND}")
    logger.info(f"Email host: {settings.EMAIL_HOST}")
    logger.info(f"From email: {settings.DEFAULT_FROM_EMAIL}")
    logger.info(f"To email: {email}")

    try:
        result = send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        logger.info(f"Email sent successfully to {email}. Result: {result}")

        # Warn if using console backend (emails won't actually be sent)
        if 'console' in settings.EMAIL_BACKEND.lower():
            logger.warning(
                f"⚠️  Using console backend - email was printed to console but NOT sent to inbox. "
                f"To send real emails, configure SMTP settings in .env"
            )
    except Exception as e:
        logger.error(f"Failed to send teacher approval email to {email}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.exception("Full traceback:")

class CheckClassroomKeyView(APIView):
    """
    Checks if a classroom key exists and returns classroom, teacher, and student data.
    """
    def post(self, request, *args, **kwargs):
        classroom_key_from_request = request.data.get("classroomKey")

        if not classroom_key_from_request:
            return Response({"error": "Invalid input: classroomKey missing"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Fetch the classroom using its unique classroom_key
            # select_related fetches related Teacher objects in the same DB query
            print(Classroom.objects.count())

            classroom = Classroom.objects.select_related('teacher').get(classroom_key=classroom_key_from_request)

            # Now you can safely access classroom attributes
            print(f"Found classroom: ID={classroom.id}, Key={classroom.classroom_key}, Teacher={classroom.teacher.full_name}")

            # ... (rest of your logic to prepare response_data)
            students_queryset = Student.objects.filter(classroom=classroom)
            student_names = [student.full_name for student in students_queryset]

            # Get the school directly from the classroom
            school = classroom.school

            response_data = {
                'school': school,
                'teacher_data': classroom.teacher.full_name,
                'students': student_names
            }
            serializer = CheckClassroomResponseSerializer(response_data) # Ensure this serializer is defined
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Classroom.DoesNotExist:
            print(f"Classroom with key '{classroom_key_from_request}' does not exist.") # More informative print
            return Response({"message": "Classroom key verification failed or classroom not found"}, status=status.HTTP_404_NOT_FOUND) # 404 is often more appropriate here
        except Exception as e:
            # Catch any other unexpected errors
            print(f"An unexpected error occurred: {e}")
            import traceback
            traceback.print_exc()
            return Response({"error": "An internal server error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class InsertLevelStatisticsView(APIView):
    """
    Inserts run statistics for a student in a given classroom.
    """
    def post(self, request, *args, **kwargs):
        input_serializer = LevelStatisticsInputSerializer(data=request.data)
        if not input_serializer.is_valid():
            return Response(input_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = input_serializer.validated_data
        classroom_key = data["classroomKey"]
        user_full_name = data["user"]
        level_statistics = data['levelStatistics']

        try:
            classroom = Classroom.objects.get(classroom_key=classroom_key)
        except Classroom.DoesNotExist:
            return Response({"error": "Classroom not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            student = Student.objects.get(full_name=user_full_name, classroom=classroom)
        except Student.DoesNotExist:
            return Response({"error": "User (Student) not found in this classroom"}, status=status.HTTP_404_NOT_FOUND)

        player_won = level_statistics.get('place') == 1

        try:
            # Create RunStatistics instance using Django ORM
            run_stat = RunStatistics.objects.create(
                student=student,
                player_won=player_won,
                level=level_statistics.get('level'),
                score=level_statistics.get('score'),
                place=level_statistics.get('place'),
                correct_moves=level_statistics.get('correctMoves'),
                wrong_moves=level_statistics.get('wrongMoves'),
                time_elapsed=level_statistics.get('timeElapsed')
            )
            # Optionally, serialize and return the created object if needed by the frontend
            # run_stat_serializer = RunStatisticsSerializer(run_stat)
            # return Response(run_stat_serializer.data, status=status.HTTP_201_CREATED)
            return Response({"message": "Data inserted successfully"}, status=status.HTTP_201_CREATED)

        except Exception as e:
            # Log the exception for server-side debugging
            print(f"Error inserting run statistics: {e}")
            import traceback
            traceback.print_exc()
            return Response({"error": "Internal server error while saving statistics"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
import os

def register_school_view(request):
    if request.method == 'POST':
        form = SchoolRegistrationForm(request.POST)
        if form.is_valid():
            # Create school with PENDING status (default)
            school = form.save(commit=False)
            school.status = 'PENDING'  # Explicitly set status
            school.save()
            messages.success(request, 'School registration submitted for approval.')
            return redirect('registration_success')
    else:
        form = SchoolRegistrationForm()

    context = {
        'form': form,
        'google_maps_api_key': os.getenv('GOOGLE_MAPS_API_KEY')
    }
    return render(request, 'digitmileapi/register_school.html', context)

def register_teacher_view(request):
    if request.method == 'POST':
        form = TeacherRegistrationForm(request.POST)
        if form.is_valid():
            # Create the Teacher instance with PENDING status
            teacher = Teacher.objects.create(
                full_name=form.cleaned_data['full_name'],
                email=form.cleaned_data['email'],
                years_teaching=form.cleaned_data.get('years_teaching'),
                phone_number=form.cleaned_data.get('phone_number', ''),
                status='PENDING'
            )

            # Process selected schools (both pending and approved)
            for school in form.cleaned_data.get('schools', []):
                years_key = f'years_at_school_{school.id}'
                years_at_school = request.POST.get(years_key)
                TeacherSchoolAssignment.objects.create(
                    teacher=teacher,
                    school=school,
                    years_at_school=int(years_at_school) if years_at_school and years_at_school.isdigit() else None
                )

            messages.success(request, 'Teacher registration submitted for approval.')
            return redirect('registration_success')
    else:
        form = TeacherRegistrationForm()
    return render(request, 'digitmileapi/register_teacher.html', {'form': form})
class IsTeacher(permissions.BasePermission):
    """
    Custom permission to only allow users in the 'Teachers' group
    and who have a teacher_profile.
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.groups.filter(name='Teachers').exists() and
            hasattr(request.user, 'teacher_profile')
        )

class TeacherStudentViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows teachers to view and manage students
    within their own classrooms.
    """
    serializer_class = TeacherStudentManagementSerializer
    permission_classes = [IsTeacher] # Use the custom permission

    def get_queryset(self):
        """
        This view should return a list of all the students
        for the currently authenticated teacher's classrooms.
        """
        teacher = self.request.user.teacher_profile
        # Get all classroom IDs for this teacher
        teacher_classroom_ids = Classroom.objects.filter(teacher=teacher).values_list('id', flat=True)
        # Filter students who are in any of these classrooms
        return Student.objects.filter(classroom_id__in=teacher_classroom_ids)

    def get_serializer_context(self):
        """
        Pass request to the serializer context.
        """
        return {'request': self.request}

    def perform_create(self, serializer):
        """
        Ensure the student is created within one of the teacher's classrooms.
        The serializer already filters the classroom_id choices.
        This provides an additional check or allows setting it if not provided,
        though the serializer makes classroom_id required for write.
        """
        # The serializer's `classroom_id` field is already filtered to the teacher's classrooms.
        # So, if validation passes, it's implicitly correct.
        # If you wanted to assign to a default classroom of the teacher if not provided,
        # you'd modify the serializer or do it here, but `classroom_id` is currently required.
        serializer.save()

    # perform_update and perform_destroy will also be scoped by get_queryset implicitly
    # ensuring teachers can only modify/delete students they have access to.
class TeacherClassroomListView(generics.ListAPIView):
    """
    API endpoint that allows teachers to view a list of their own classrooms.
    """
    serializer_class = ClassroomBasicSerializer
    permission_classes = [IsTeacher]

    def get_queryset(self):
        """
        This view should return a list of all classrooms
        for the currently authenticated teacher.
        """
        teacher = self.request.user.teacher_profile
        return Classroom.objects.filter(teacher=teacher)
class TeacherSchoolView(generics.ListAPIView):
    """
    API endpoint that allows a teacher to view their assigned schools' details.
    Returns all schools (approved AND pending) assigned to the teacher.
    Teachers can work with pending schools to prepare classrooms/students before approval.
    """
    serializer_class = SchoolSerializer
    permission_classes = [IsTeacher]

    def get_queryset(self):
        """
        Returns all schools (approved and pending) associated with the currently authenticated teacher.
        Teachers should be able to work with pending schools.
        """
        teacher_profile = getattr(self.request.user, 'teacher_profile', None)
        if teacher_profile:
            # Return both APPROVED and PENDING schools, exclude REJECTED
            return teacher_profile.schools.exclude(status='REJECTED')
        return School.objects.none()
class TeacherRunStatisticsListView(generics.ListAPIView):
    """
    API endpoint that allows teachers to view run statistics
    for students in their own classrooms.
    """
    serializer_class = RunStatisticsSerializer
    permission_classes = [IsTeacher]

    def get_queryset(self):
        """
        This view should return a list of all run statistics
        for students belonging to the currently authenticated teacher's classrooms.
        """
        teacher = self.request.user.teacher_profile
        # Filter RunStatistics where the student's classroom's teacher is the current teacher
        return RunStatistics.objects.filter(student__classroom__teacher=teacher)
def registration_success(request):
    return render(request, 'digitmileapi/registration_success.html')
from django.contrib.auth.decorators import user_passes_test

@user_passes_test(lambda u: u.is_superuser)
def pending_registrations_view(request):
    pending_schools = School.objects.pending()
    pending_teachers = Teacher.objects.pending()
    context = {
        'pending_schools': pending_schools,
        'pending_teachers': pending_teachers,
    }
    return render(request, 'digitmileapi/pending_registrations.html', context)
def home_view(request):
    return render(request, 'digitmileapi/home.html')
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User

@user_passes_test(lambda u: u.is_superuser)
def approve_school(request, school_id):
    school = get_object_or_404(School, id=school_id, status='PENDING')

    # Update status to APPROVED
    school.status = 'APPROVED'
    school.save()

    # Send approval email to school contact person
    send_school_approval_email(school)

    messages.success(request, f"School '{school.name}' has been approved and notified via email.")
    return redirect('pending_registrations')

@user_passes_test(lambda u: u.is_superuser)
def reject_school(request, school_id):
    """
    Reject a school registration and cascade rejection to teachers who ONLY have this school.
    Deletes all classrooms, students, and run statistics for rejected teachers.
    """
    school = get_object_or_404(School, id=school_id, status='PENDING')

    # Find all teachers assigned to this school
    teachers_at_school = Teacher.objects.filter(schools=school)

    teachers_to_reject = []
    for teacher in teachers_at_school:
        # Check if this is the teacher's ONLY school
        school_count = teacher.schools.count()
        if school_count == 1:
            # This is their only school, they will be rejected
            teachers_to_reject.append(teacher)

    # Update status to REJECTED
    school.status = 'REJECTED'
    school.save()

    # Reject teachers who only have this school
    rejected_teacher_names = []
    for teacher in teachers_to_reject:
        # Delete all classrooms (cascades to students and run statistics)
        Classroom.objects.filter(teacher=teacher).delete()

        # Set teacher status to REJECTED
        teacher.status = 'REJECTED'
        teacher.save()

        rejected_teacher_names.append(teacher.full_name)

    # Build message
    if rejected_teacher_names:
        teachers_msg = f" The following teachers were also rejected and their data deleted: {', '.join(rejected_teacher_names)}"
    else:
        teachers_msg = " No teachers were affected (they have assignments to other schools)."

    messages.warning(
        request,
        f"School '{school.name}' has been rejected.{teachers_msg}"
    )
    return redirect('pending_registrations')

@user_passes_test(lambda u: u.is_superuser)
def approve_teacher(request, teacher_id):
    from django.contrib.auth.models import Group

    teacher = get_object_or_404(Teacher, id=teacher_id, status='PENDING')

    # Create a new user for the teacher
    username = teacher.email.split('@')[0]
    # Generate a random password
    from django.utils.crypto import get_random_string
    random_password = get_random_string(length=12)

    user = User.objects.create_user(
        username=username,
        email=teacher.email,
        password=random_password,
        is_staff=True  # Allow access to Django admin
    )

    # Add user to Teachers group
    teachers_group, created = Group.objects.get_or_create(name='Teachers')
    user.groups.add(teachers_group)

    # Link user to teacher and update status
    teacher.user = user
    teacher.status = 'APPROVED'
    teacher.save()

    # Send approval email with credentials to teacher
    send_teacher_approval_email(teacher.email, username, random_password, teacher)

    messages.success(request, f"Teacher '{teacher.full_name}' has been approved and credentials sent via email.")
    return redirect('pending_registrations')

@user_passes_test(lambda u: u.is_superuser)
def reject_teacher(request, teacher_id):
    """
    Reject a teacher registration.
    Deletes all classrooms, students, and run statistics created by this teacher.
    """
    teacher = get_object_or_404(Teacher, id=teacher_id, status='PENDING')

    # Delete all classrooms (cascades to students and run statistics)
    classrooms_deleted = Classroom.objects.filter(teacher=teacher).count()
    Classroom.objects.filter(teacher=teacher).delete()

    # Set teacher status to REJECTED
    teacher.status = 'REJECTED'
    teacher.save()

    messages.warning(
        request,
        f"Teacher '{teacher.full_name}' has been rejected. {classrooms_deleted} classroom(s) and all associated data were deleted."
    )
    return redirect('pending_registrations')

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Sum
import json

@login_required
@user_passes_test(lambda u: hasattr(u, 'teacher_profile'))
def teacher_statistics_dashboard(request):
    """
    Dashboard for teachers to view student performance statistics with interactive charts.
    """
    teacher = request.user.teacher_profile

    # Get all classrooms for this teacher
    classrooms = Classroom.objects.filter(teacher=teacher).prefetch_related('students')

    # Get all students for this teacher
    students = Student.objects.filter(classroom__teacher=teacher)

    # Prepare data for different charts
    student_data = []

    for student in students:
        stats = RunStatistics.objects.filter(student=student).order_by('level')

        if stats.exists():
            student_info = {
                'id': student.id,
                'name': student.full_name,
                'classroom': student.classroom.classroom_name,
                'classroom_key': student.classroom.classroom_key,
                'total_runs': stats.count(),
                'avg_score': stats.aggregate(Avg('score'))['score__avg'] or 0,
                'wins': stats.filter(player_won=True).count(),
                'win_rate': (stats.filter(player_won=True).count() / stats.count() * 100) if stats.count() > 0 else 0,
                'avg_time': stats.aggregate(Avg('time_elapsed'))['time_elapsed__avg'] or 0,
                'levels': list(stats.values_list('level', flat=True)),
                'scores': list(stats.values_list('score', flat=True)),
                'times': list(stats.values_list('time_elapsed', flat=True)),
                'correct_moves': list(stats.values_list('correct_moves', flat=True)),
                'wrong_moves': list(stats.values_list('wrong_moves', flat=True)),
                'places': list(stats.values_list('place', flat=True)),
            }
            student_data.append(student_info)

    # Prepare classroom-level statistics
    classroom_stats = []
    for classroom in classrooms:
        classroom_students = classroom.students.all()
        all_runs = RunStatistics.objects.filter(student__in=classroom_students)

        if all_runs.exists():
            classroom_info = {
                'name': classroom.classroom_name,
                'key': classroom.classroom_key,
                'student_count': classroom_students.count(),
                'total_runs': all_runs.count(),
                'avg_score': all_runs.aggregate(Avg('score'))['score__avg'] or 0,
                'win_rate': (all_runs.filter(player_won=True).count() / all_runs.count() * 100) if all_runs.count() > 0 else 0,
            }
            classroom_stats.append(classroom_info)

    context = {
        'teacher': teacher,
        'student_data': student_data,
        'student_data_json': json.dumps(student_data),
        'classroom_stats': classroom_stats,
        'classroom_stats_json': json.dumps(classroom_stats),
    }

    return render(request, 'digitmileapi/teacher_statistics.html', context)