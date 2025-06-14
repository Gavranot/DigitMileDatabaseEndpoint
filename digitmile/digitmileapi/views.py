# myapi/views.py
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