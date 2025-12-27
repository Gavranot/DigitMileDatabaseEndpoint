from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from digitmileapi.models import School, Classroom, Student, RunStatistics


class Command(BaseCommand):
    help = 'Sets up the Teachers group with appropriate permissions'

    def handle(self, *args, **options):
        # Create or get the Teachers group
        teachers_group, created = Group.objects.get_or_create(name='Teachers')

        if created:
            self.stdout.write(self.style.SUCCESS('Created Teachers group'))
        else:
            self.stdout.write('Teachers group already exists')

        # Get content types for our models
        school_ct = ContentType.objects.get_for_model(School)
        classroom_ct = ContentType.objects.get_for_model(Classroom)
        student_ct = ContentType.objects.get_for_model(Student)
        runstats_ct = ContentType.objects.get_for_model(RunStatistics)

        # Define permissions to add
        permissions_to_add = [
            # School - view only (read-only access)
            Permission.objects.get(content_type=school_ct, codename='view_school'),

            # Classroom - full CRUD for their own classrooms
            Permission.objects.get(content_type=classroom_ct, codename='add_classroom'),
            Permission.objects.get(content_type=classroom_ct, codename='change_classroom'),
            Permission.objects.get(content_type=classroom_ct, codename='delete_classroom'),
            Permission.objects.get(content_type=classroom_ct, codename='view_classroom'),

            # Student - full CRUD for students in their classrooms
            Permission.objects.get(content_type=student_ct, codename='add_student'),
            Permission.objects.get(content_type=student_ct, codename='change_student'),
            Permission.objects.get(content_type=student_ct, codename='delete_student'),
            Permission.objects.get(content_type=student_ct, codename='view_student'),

            # RunStatistics - view only (audit log, no modifications)
            Permission.objects.get(content_type=runstats_ct, codename='view_runstatistics'),
        ]

        # Clear existing permissions and add new ones
        teachers_group.permissions.clear()
        teachers_group.permissions.add(*permissions_to_add)

        self.stdout.write(self.style.SUCCESS(
            f'Successfully configured Teachers group with {len(permissions_to_add)} permissions:'
        ))
        for perm in permissions_to_add:
            self.stdout.write(f'  - {perm.content_type.app_label}.{perm.codename}')

        self.stdout.write(self.style.SUCCESS('\nTeachers in this group can:'))
        self.stdout.write('  ✓ View their assigned schools (read-only)')
        self.stdout.write('  ✓ Add/edit/delete classrooms in their assigned schools')
        self.stdout.write('  ✓ Add/edit/delete students in their classrooms')
        self.stdout.write('  ✓ View run statistics for their students (read-only)')
