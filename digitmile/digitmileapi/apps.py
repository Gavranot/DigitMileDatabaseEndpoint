from django.apps import AppConfig
from django.db.models.signals import post_migrate

def create_teacher_group(sender, **kwargs):
    # Imports are placed inside the function to avoid issues if models are not yet ready
    # or if this code runs before the app registry is fully populated.
    from django.contrib.auth.models import Group, Permission
    from django.contrib.contenttypes.models import ContentType
    # Assuming your models are in 'models.py' in the same app
    from .models import Student, Classroom, School, RunStatistics

    # Get or create the 'Teachers' group
    teacher_group, created = Group.objects.get_or_create(name='Teachers')

    if created:
        print("Successfully created 'Teachers' group.")

    # It's good practice to wrap permission assignment in a try-except block
    # to handle cases where ContentTypes or Permissions might not yet exist (e.g., during initial migrations)
    try:
        # Get ContentType for each model
        student_ct = ContentType.objects.get_for_model(Student)
        classroom_ct = ContentType.objects.get_for_model(Classroom)
        school_ct = ContentType.objects.get_for_model(School)
        run_statistics_ct = ContentType.objects.get_for_model(RunStatistics)

        # Define the list of permissions to assign
        # These are model-level permissions. Object-level permissions (e.g., "can only edit own students")
        # will be enforced in views/serializers by filtering querysets.
        permissions_to_assign = [
            Permission.objects.get(codename='view_student', content_type=student_ct),
            Permission.objects.get(codename='add_student', content_type=student_ct),
            Permission.objects.get(codename='change_student', content_type=student_ct),
            Permission.objects.get(codename='delete_student', content_type=student_ct),
            Permission.objects.get(codename='view_classroom', content_type=classroom_ct),
            Permission.objects.get(codename='view_school', content_type=school_ct),
            Permission.objects.get(codename='view_runstatistics', content_type=run_statistics_ct),
        ]

        # Assign the permissions to the group.
        # .set() clears existing permissions and adds the new ones.
        teacher_group.permissions.set(permissions_to_assign)
        print("Successfully assigned/updated permissions for 'Teachers' group.")

    except ContentType.DoesNotExist as e:
        print(f"Warning: ContentType not found during permission assignment: {e}. "
              "This might be normal if migrations haven't run for all models yet. "
              "Permissions may not be fully set.")
    except Permission.DoesNotExist as e:
        print(f"Warning: Permission not found during permission assignment: {e}. "
              "Ensure all migrations are run and default permissions are created. "
              "Permissions may not be fully set.")
    except Exception as e:
        # Catch any other unexpected errors during the process
        print(f"An unexpected error occurred during permission assignment: {e}")


class DigitmileapiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'digitmileapi'

    def ready(self):
        # Connect the post_migrate signal to our function.
        # This ensures create_teacher_group is called after migrations are applied.
        post_migrate.connect(create_teacher_group, sender=self)
