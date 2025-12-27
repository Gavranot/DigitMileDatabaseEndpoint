# your_app_name/admin.py
from django.contrib import admin
from django import forms
from .models import School, Teacher, Classroom, Student, RunStatistics, TeacherSchoolAssignment
from django.contrib.auth.models import User

# Make sure TeacherProfileInline and UserAdmin are set up as discussed before
# if you want to manage Teacher profiles through the User admin.

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'municipality', 'region', 'status', 'created_at')
    list_filter = ('status', 'region')
    search_fields = ('name', 'municipality', 'contact_person_name', 'director_name')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'municipality', 'region', 'address', 'google_maps_address', 'latitude', 'longitude', 'website')
        }),
        ('Contact Person (Registration)', {
            'fields': ('contact_person_name', 'contact_person_email', 'contact_person_phone')
        }),
        ('Official School Information', {
            'fields': ('director_name', 'director_email', 'school_email', 'school_phone')
        }),
        ('Status', {
            'fields': ('status', 'created_at', 'updated_at'),
            'description': '<strong style="color: #d63031;">⚠️ WARNING:</strong> Changing status to REJECTED will cascade to teachers! '
                          'Teachers who ONLY have this school will be REJECTED and all their classrooms, students, '
                          'and run statistics will be permanently DELETED.'
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs  # Superusers see all schools
        if hasattr(request.user, 'teacher_profile'):
            # Teachers see only their assigned schools
            return qs.filter(teachers=request.user.teacher_profile, status='APPROVED')
        return qs.none()

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        # Teachers cannot edit any fields
        if not request.user.is_superuser and hasattr(request.user, 'teacher_profile'):
            return [field.name for field in obj._meta.fields] if obj else readonly
        return readonly

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        # Teachers can view their schools in read-only mode
        if obj and hasattr(request.user, 'teacher_profile'):
            return obj in request.user.teacher_profile.schools.filter(status='APPROVED')
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def save_model(self, request, obj, form, change):
        """Override to show notification of cascade effects when status changes to REJECTED"""
        from django.contrib import messages

        # Track if status is changing to REJECTED
        status_changing_to_rejected = False
        if change and 'status' in form.changed_data:
            old_status = School.objects.get(pk=obj.pk).status
            if old_status != 'REJECTED' and obj.status == 'REJECTED':
                status_changing_to_rejected = True

                # Get affected teachers before save
                teachers_at_school = Teacher.objects.filter(schools=obj)
                affected_teachers = []
                total_classrooms = 0

                for teacher in teachers_at_school:
                    if teacher.schools.count() == 1:
                        classrooms_count = Classroom.objects.filter(teacher=teacher).count()
                        affected_teachers.append((teacher.full_name, classrooms_count))
                        total_classrooms += classrooms_count

        # Save the model (cascade will happen in School.save())
        super().save_model(request, obj, form, change)

        # Show warning message if cascade happened
        if status_changing_to_rejected and affected_teachers:
            teacher_details = ", ".join([f"{name} ({count} classrooms)" for name, count in affected_teachers])
            messages.warning(
                request,
                f"School '{obj.name}' status changed to REJECTED. "
                f"CASCADE EXECUTED: {len(affected_teachers)} teacher(s) were rejected and their data deleted: {teacher_details}"
            )
        elif status_changing_to_rejected:
            messages.info(
                request,
                f"School '{obj.name}' status changed to REJECTED. "
                f"No teachers were affected (they have assignments to other schools)."
            )

class TeacherSchoolAssignmentInline(admin.TabularInline):
    model = TeacherSchoolAssignment
    extra = 1
    max_num = 3

class StudentInline(admin.TabularInline):
    model = Student
    extra = 0
    fields = ('full_name', 'date_of_birth', 'grade')
    readonly_fields = ('full_name', 'date_of_birth', 'grade')
    can_delete = True

    def has_add_permission(self, request, obj=None):
        # Disable adding students via inline (use bulk_students field instead)
        return False

# Teacher Admin
@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'status', 'get_schools', 'years_teaching', 'phone_number', 'created_at')
    list_filter = ('status', 'schools')
    search_fields = ('full_name', 'email', 'user__username')
    raw_id_fields = ('user',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [TeacherSchoolAssignmentInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('full_name', 'email', 'phone_number', 'years_teaching')
        }),
        ('User Account', {
            'fields': ('user',),
            'description': 'User account is created automatically when teacher is approved'
        }),
        ('Status', {
            'fields': ('status', 'created_at', 'updated_at'),
            'description': '<strong style="color: #d63031;">⚠️ WARNING:</strong> Changing status to REJECTED will permanently DELETE '
                          'all classrooms, students, and run statistics created by this teacher!'
        }),
    )

    def get_schools(self, obj):
        schools = obj.schools.all()
        return ", ".join([f"{s.name} ({'PENDING' if s.is_pending else 'APPROVED'})" for s in schools])
    get_schools.short_description = 'Schools'

    def save_model(self, request, obj, form, change):
        """Override to show notification of cascade effects when status changes to REJECTED"""
        from django.contrib import messages

        # Track if status is changing to REJECTED
        status_changing_to_rejected = False
        classrooms_to_delete = 0

        if change and 'status' in form.changed_data:
            old_status = Teacher.objects.get(pk=obj.pk).status
            if old_status != 'REJECTED' and obj.status == 'REJECTED':
                status_changing_to_rejected = True
                classrooms_to_delete = Classroom.objects.filter(teacher=obj).count()

        # Save the model (cascade will happen in Teacher.save())
        super().save_model(request, obj, form, change)

        # Show warning message if cascade happened
        if status_changing_to_rejected:
            messages.warning(
                request,
                f"Teacher '{obj.full_name}' status changed to REJECTED. "
                f"CASCADE EXECUTED: {classrooms_to_delete} classroom(s) and all associated students and run statistics were permanently deleted."
            )

@admin.register(TeacherSchoolAssignment)
class TeacherSchoolAssignmentAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'school', 'years_at_school')
    list_filter = ('school__status',)
    search_fields = ('teacher__full_name', 'school__name')

class ClassroomAdminForm(forms.ModelForm):
    """Custom form to handle teacher auto-assignment and bulk student creation"""

    bulk_students = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 6,
            'cols': 80,
            'placeholder': 'Add multiple students (comma-separated):\nJohn Doe/2015-03-15, Jane Smith/2015-07-22, ...'
        }),
        help_text='Format: FullName/DateOfBirth (YYYY-MM-DD), comma-separated. Example: John Doe/2015-03-15, Jane Smith/2015-07-22',
        label='Bulk Add Students'
    )

    class Meta:
        model = Classroom
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean_bulk_students(self):
        """Validate and parse bulk student input"""
        bulk_data = self.cleaned_data.get('bulk_students', '').strip()
        if not bulk_data:
            return []

        students = []
        errors = []

        # Split by comma
        entries = [entry.strip() for entry in bulk_data.split(',') if entry.strip()]

        for idx, entry in enumerate(entries, 1):
            # Split by forward slash
            parts = entry.split('/')
            if len(parts) != 2:
                errors.append(f"Entry {idx} ('{entry}'): Must be in format 'FullName/DateOfBirth'")
                continue

            full_name = parts[0].strip()
            dob_str = parts[1].strip()

            if not full_name:
                errors.append(f"Entry {idx}: Name cannot be empty")
                continue

            # Parse date
            from datetime import datetime
            try:
                dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
            except ValueError:
                errors.append(f"Entry {idx} ('{entry}'): Invalid date format. Use YYYY-MM-DD (e.g., 2015-03-15)")
                continue

            students.append({
                'full_name': full_name,
                'date_of_birth': dob
            })

        if errors:
            raise forms.ValidationError('\n'.join(errors))

        return students

    def clean(self):
        cleaned_data = super().clean()
        # Auto-assign teacher if user is not superuser and has teacher_profile
        if self.request and not self.request.user.is_superuser and hasattr(self.request.user, 'teacher_profile'):
            # Set teacher before model validation
            self.instance.teacher = self.request.user.teacher_profile
        return cleaned_data

@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    form = ClassroomAdminForm
    list_display = ('classroom_key', 'classroom_name', 'grade', 'school', 'teacher')
    search_fields = ('classroom_key', 'classroom_name', 'teacher__full_name', 'school__name')
    list_filter = ('school', 'teacher', 'school__status', 'grade')
    inlines = [StudentInline]

    # Restrict queryset for non-superusers (teachers)
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'teacher_profile'):
            return qs.filter(teacher=request.user.teacher_profile)
        return qs.none()

    def get_form(self, request, obj=None, **kwargs):
        """Pass request to the form"""
        Form = super().get_form(request, obj, **kwargs)

        class FormWithRequest(Form):
            def __new__(cls, *args, **kwargs):
                kwargs['request'] = request
                return Form(*args, **kwargs)

        return FormWithRequest

    def get_fields(self, request, obj=None):
        """Control which fields are shown in the form"""
        if request.user.is_superuser:
            # Superusers see all fields including grade and bulk students
            return ['classroom_key', 'classroom_name', 'grade', 'school', 'teacher', 'bulk_students']
        else:
            # Teachers see classroom fields, grade, and bulk student creation (teacher is auto-assigned)
            return ['classroom_key', 'classroom_name', 'grade', 'school', 'bulk_students']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter school and teacher choices based on permissions"""
        if db_field.name == "school":
            if not request.user.is_superuser and hasattr(request.user, 'teacher_profile'):
                # Limit to schools assigned to this teacher (including PENDING)
                kwargs["queryset"] = request.user.teacher_profile.schools.exclude(status='REJECTED')
        if db_field.name == "teacher":
            # Only superusers see this field (see get_fields)
            if request.user.is_superuser:
                # Superusers can assign to any approved teacher
                kwargs["queryset"] = Teacher.objects.filter(status='APPROVED')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        """Auto-assign teacher for non-superusers and handle bulk student creation"""
        from django.contrib import messages

        if not request.user.is_superuser and hasattr(request.user, 'teacher_profile'):
            # Auto-assign the logged-in teacher
            obj.teacher = request.user.teacher_profile

        # Save the classroom first
        super().save_model(request, obj, form, change)

        # Handle bulk student creation
        bulk_students = form.cleaned_data.get('bulk_students', [])
        if bulk_students:
            created_count = 0
            skipped_count = 0
            errors = []

            for student_data in bulk_students:
                full_name = student_data['full_name']
                date_of_birth = student_data['date_of_birth']

                # Check if student already exists in this classroom
                if Student.objects.filter(full_name=full_name, classroom=obj).exists():
                    skipped_count += 1
                    continue

                try:
                    # Create the student with grade from classroom if available
                    Student.objects.create(
                        full_name=full_name,
                        date_of_birth=date_of_birth,
                        grade=obj.grade,  # Auto-assign classroom grade to student
                        classroom=obj
                    )
                    created_count += 1
                except Exception as e:
                    errors.append(f"{full_name}: {str(e)}")

            # Show success/info messages
            if created_count > 0:
                messages.success(request, f"Successfully created {created_count} student(s).")
            if skipped_count > 0:
                messages.info(request, f"Skipped {skipped_count} student(s) (already exist in classroom).")
            if errors:
                messages.warning(request, f"Errors occurred:\n" + "\n".join(errors))

    # Allow teachers to add classrooms to their assigned schools
    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        # Teachers can add classrooms if they have assigned schools
        if hasattr(request.user, 'teacher_profile'):
            return request.user.teacher_profile.schools.exclude(status='REJECTED').exists()
        return False

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is not None and hasattr(request.user, 'teacher_profile'):
            return obj.teacher == request.user.teacher_profile
        return False

    def get_readonly_fields(self, request, obj=None):
        """Make fields read-only when editing (not adding)"""
        if not request.user.is_superuser and obj and hasattr(request.user, 'teacher_profile'):
            # When editing, teachers can only change classroom_name and grade
            return ['classroom_key', 'school']
        return super().get_readonly_fields(request, obj)

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is not None and hasattr(request.user, 'teacher_profile'):
            return obj.teacher == request.user.teacher_profile
        return False

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'date_of_birth', 'grade', 'classroom', 'get_teacher_name')
    search_fields = ('full_name', 'classroom__classroom_key')
    list_filter = ('classroom__teacher', 'grade')
    fields = ('full_name', 'date_of_birth', 'grade', 'classroom')

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
    list_display = ('student', 'level', 'score', 'place', 'player_won', 'correct_moves', 'wrong_moves', 'time_elapsed', 'get_classroom_from_student')
    list_filter = ('player_won', 'level', 'place', 'student__classroom__teacher')
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
