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
class ClassroomBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Classroom
        fields = ['id', 'classroom_key']

class TeacherStudentManagementSerializer(serializers.ModelSerializer):
    # Display classroom details in a nested way for reads
    classroom = ClassroomBasicSerializer(read_only=True) 
    # Allow setting classroom by ID for writes (create/update)
    classroom_id = serializers.PrimaryKeyRelatedField(
        queryset=Classroom.objects.all(), source='classroom', write_only=True
    )

    class Meta:
        model = Student
        fields = ['id', 'full_name', 'classroom', 'classroom_id']
        read_only_fields = ['id']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically filter classroom_id queryset if a teacher is provided in context
        # This is crucial for ensuring teachers can only assign students to their own classrooms.
        request = self.context.get('request', None)
        if request and hasattr(request.user, 'teacher_profile'):
            teacher = request.user.teacher_profile
            self.fields['classroom_id'].queryset = Classroom.objects.filter(teacher=teacher)
        elif request and request.method in ['POST', 'PUT', 'PATCH'] and not (request.user.is_staff or request.user.is_superuser):
            # If it's a write operation by a non-staff user without a teacher_profile,
            # they shouldn't be able to set any classroom.
            # This scenario should ideally be caught by permissions in the view.
            self.fields['classroom_id'].queryset = Classroom.objects.none()


# Make sure this is below the new serializers if they are referenced by existing ones.
# For now, placing it at the end of the new additions.