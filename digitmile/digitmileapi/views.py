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
from .forms import TeacherRegistrationForm
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Classroom, Student, Teacher, School, RunStatistics
from .serializers import (
    CheckClassroomResponseSerializer,
    LevelStatisticsInputSerializer,
    RunStatisticsSerializer # Import if you use it for creation validation/response
)

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
            # select_related fetches related Teacher and School objects in the same DB query
            print(Classroom.objects.count())

            classroom = Classroom.objects.select_related('teacher', 'teacher__school').get(classroom_key=classroom_key_from_request)

            # Now you can safely access classroom attributes
            print(f"Found classroom: ID={classroom.id}, Key={classroom.classroom_key}, Teacher={classroom.teacher.full_name}")

            # ... (rest of your logic to prepare response_data)
            students_queryset = Student.objects.filter(classroom=classroom)
            student_names = [student.full_name for student in students_queryset]

            response_data = {
                'school': classroom.teacher.school,
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
                player_won=player_won
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
def teacher_registration_view(request):
    if request.method == 'POST':
        form = TeacherRegistrationForm(request.POST)
        if form.is_valid():
            user, teacher_profile = form.save()
            messages.success(request, f'Account created for {user.username}! You can now log in.')
            # Redirect to login page or a dashboard.
            # For now, redirecting to Django admin login.
            # You might want to change this to a custom login page later.
            return redirect(reverse_lazy('admin:index')) 
        else:
            # Form is not valid, add a generic error message for now
            # Specific field errors will be displayed by the form in the template
            messages.error(request, 'Please correct the errors below.')
    else:
        form = TeacherRegistrationForm()
    
    return render(request, 'digitmileapi/teacher_registration.html', {'form': form})
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
class TeacherSchoolView(generics.RetrieveAPIView):
    """
    API endpoint that allows a teacher to view their own school's details.
    """
    serializer_class = SchoolSerializer
    permission_classes = [IsTeacher]

    def get_object(self):
        """
        Returns the school associated with the currently authenticated teacher.
        """
        # Ensure the teacher profile and school exist to prevent errors
        teacher_profile = getattr(self.request.user, 'teacher_profile', None)
        if teacher_profile and teacher_profile.school:
            return teacher_profile.school
        # This case should ideally not be reached if IsTeacher permission works correctly
        # and data integrity is maintained (teacher always has a school).
        # Consider raising Http404 if school is not found.
        from django.http import Http404
        raise Http404("School not found for this teacher.")
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