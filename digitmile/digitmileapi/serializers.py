# myapi/serializers.py
from rest_framework import serializers
from .models import School, Teacher, Student, Classroom, RunStatistics

class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = ['name', 'municipality']

class TeacherNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Teacher
        fields = ['full_name']

class StudentNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ['full_name']

# Serializer for the output of /api/checkClassroomKey
class CheckClassroomResponseSerializer(serializers.Serializer):
    school = SchoolSerializer()
    teacher = serializers.CharField(source='teacher_data') # Expecting a string here based on your Flask code
    students = serializers.ListField(child=serializers.CharField())

# Serializer for the input of /api/insertLevelStatistics
class LevelStatisticsInputSerializer(serializers.Serializer):
    classroomKey = serializers.CharField(max_length=100)
    user = serializers.CharField(max_length=255) # This is student's full_name
    levelStatistics = serializers.DictField()

    def validate_levelStatistics(self, value):
        # Example validation: ensure 'place' exists and is an integer
        if 'place' not in value:
            raise serializers.ValidationError("The 'place' key is required in levelStatistics.")
        if not isinstance(value['place'], int):
            raise serializers.ValidationError("The 'place' for levelStatistics must be an integer.")
        # Add more validation for other expected keys in levelStatistics if needed
        # e.g., score, correctMoves, wrongMoves, timeElapsed
        return value

class RunStatisticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = RunStatistics
        # If you want to return the created object, specify fields
        # otherwise, for just a success message, this might not be strictly needed for the response
        fields = ['id', 'student', 'player_won']
        read_only_fields = ['id']