# your_app_name/admin.py
from django.contrib import admin
from .models import School, Teacher, Classroom, Student, RunStatistics # Import your models
from django.contrib.auth.models import User # If you need it directly

# Make sure TeacherProfileInline and UserAdmin are set up as discussed before
# if you want to manage Teacher profiles through the User admin.

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'municipality')
    search_fields = ('name',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs # Superusers see all schools
        if hasattr(request.user, 'teacher_profile') and request.user.teacher_profile.school:
            # Teachers see only their own school
            return qs.filter(pk=request.user.teacher_profile.school.pk)
        return qs.none() # No schools if not superuser or teacher without a school

    def get_readonly_fields(self, request, obj=None):
        # If a teacher is viewing their school, make all fields read-only
        if not request.user.is_superuser and obj and hasattr(request.user, 'teacher_profile') and obj == request.user.teacher_profile.school:
            # Return a list of all model fields to make them read-only
            return [field.name for field in obj._meta.fields]
        return super().get_readonly_fields(request, obj)

    def has_add_permission(self, request):
        # Only superusers can add schools
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        # Superusers can change. Teachers can view (due to readonly_fields) but not save changes.
        if request.user.is_superuser:
            return True
        # If obj exists and belongs to the teacher, they can open the change form (which will be read-only)
        if obj and hasattr(request.user, 'teacher_profile') and obj == request.user.teacher_profile.school:
            return True # Allows opening the form, get_readonly_fields makes it read-only
        return False

    def has_delete_permission(self, request, obj=None):
        # Only superusers can delete schools
        return request.user.is_superuser

# Teacher Admin (if needed separately, or managed via UserAdmin inline)
@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'school')
    search_fields = ('full_name', 'user__username', 'school__name')
    raw_id_fields = ('user',)

@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ('classroom_key', 'classroom_name', 'teacher')
    search_fields = ('classroom_key', 'teacher__full_name', 'teacher__user__username')
    list_filter = ('teacher',) # This will be useful for superusers

    # Restrict queryset for non-superusers (teachers)
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Assuming teacher profile is linked to user via 'teacher_profile'
        if hasattr(request.user, 'teacher_profile'):
            return qs.filter(teacher=request.user.teacher_profile)
        return qs.none() # Or handle if user is staff but not teacher and not superuser

    # Teachers should not add new classrooms via this admin
    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        return False # Teachers cannot add classrooms

    # Teachers should not change classroom details (e.g., key or assigned teacher)
    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        # Allow viewing but not changing for teachers for their own classrooms
        if obj is not None and hasattr(request.user, 'teacher_profile') and obj.teacher == request.user.teacher_profile:
             # If you want them to change *some* fields, you'd need more logic or readonly_fields
             # For simplicity here, let's say they can't change anything about the classroom object itself.
             # To allow them to click into it and see students, they need view, but change is too broad.
             # This method controls if the "Save" buttons appear on the change form.
             # Perhaps a better approach is to make fields readonly for them.
            return False # No "Save" buttons for teachers on classroom edit page
        return False


    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_superuser and obj and hasattr(request.user, 'teacher_profile') and obj.teacher == request.user.teacher_profile:
            # Make all fields readonly for teachers viewing their classroom
            return [field.name for field in self.opts.fields if field.name != self.opts.pk.name]
        return super().get_readonly_fields(request, obj)


    # Teachers should not delete classrooms
    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return False

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'classroom', 'get_teacher_name')
    search_fields = ('full_name', 'classroom__classroom_key')
    list_filter = ('classroom__teacher',) # Useful for superusers

    def get_teacher_name(self, obj):
        if obj.classroom:
            return obj.classroom.teacher
        return None
    get_teacher_name.short_description = 'Teacher'
    get_teacher_name.admin_order_field = 'classroom__teacher'


    # Restrict queryset for non-superusers (teachers)
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'teacher_profile'):
            # Show only students in classrooms belonging to this teacher
            return qs.filter(classroom__teacher=request.user.teacher_profile)
        return qs.none() # No students if not superuser or not a teacher

    # Restrict classroom choices in forms (add/change student)
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "classroom":
            if not request.user.is_superuser and hasattr(request.user, 'teacher_profile'):
                # Limit choices to classrooms taught by this teacher
                kwargs["queryset"] = Classroom.objects.filter(teacher=request.user.teacher_profile)
            # For superusers, all classrooms will be available by default
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    # Control add permission
    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        # Allow teachers to add students if they have classrooms
        if hasattr(request.user, 'teacher_profile'):
            # Check if teacher has the general 'add_student' permission first
            if not request.user.has_perm(f'{self.opts.app_label}.add_student'):
                return False
            return Classroom.objects.filter(teacher=request.user.teacher_profile).exists()
        return False

    # Control change permission for specific student objects
    def has_change_permission(self, request, obj=None):
        # Base check for general 'change_student' permission
        if not request.user.has_perm(f'{self.opts.app_label}.change_student'):
            return False
        if request.user.is_superuser:
            return True
        if obj is not None and hasattr(request.user, 'teacher_profile'):
            # Teacher can change student if student is in one of their classrooms
            return obj.classroom.teacher == request.user.teacher_profile
        # If obj is None (e.g. on the changelist page), rely on get_queryset.
        # For the "add" form, this isn't called with obj, has_add_permission handles that.
        return False # Default to no permission if not superuser and no object to check or object not theirs

    # Control delete permission for specific student objects
    def has_delete_permission(self, request, obj=None):
        if not request.user.has_perm(f'{self.opts.app_label}.delete_student'):
            return False
        if request.user.is_superuser:
            return True
        if obj is not None and hasattr(request.user, 'teacher_profile'):
            # Teacher can delete student if student is in one of their classrooms
            return obj.classroom.teacher == request.user.teacher_profile
        return False

    # Ensure student is saved to one of the teacher's classrooms
    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser and hasattr(request.user, 'teacher_profile'):
            # If adding a new student or changing an existing one,
            # the classroom field should have been limited by formfield_for_foreignkey.
            # This is an additional safeguard.
            if obj.classroom.teacher != request.user.teacher_profile:
                # This should ideally not happen if formfield_for_foreignkey is working.
                # Raise an error or prevent saving.
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied("You can only assign students to your own classrooms.")
        super().save_model(request, obj, form, change)

@admin.register(RunStatistics)
class RunStatisticsAdmin(admin.ModelAdmin):
    list_display = ('student', 'player_won', 'get_classroom_from_student')
    list_filter = ('player_won', 'student__classroom__teacher')
    search_fields = ('student__full_name',)

    def get_classroom_from_student(self, obj):
        if obj.student and obj.student.classroom:
            return obj.student.classroom
        return None
    get_classroom_from_student.short_description = 'Classroom'

    # Restrict queryset for non-superusers (teachers)
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'teacher_profile'):
            # Show only stats for students in classrooms belonging to this teacher
            return qs.filter(student__classroom__teacher=request.user.teacher_profile)
        return qs.none()

    # Teachers should not add, change, or delete RunStatistics directly (it's an audit/log table)
    def has_add_permission(self, request):
        return request.user.is_superuser
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser