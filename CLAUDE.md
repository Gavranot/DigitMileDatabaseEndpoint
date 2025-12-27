# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DigitMile Database Endpoint is a Django REST Framework API for managing educational game statistics. The system tracks schools, teachers, classrooms, students, and their game run statistics. It includes a registration workflow where schools and teachers can register for approval by administrators.

## Development Commands

### Environment Setup
```bash
# Activate virtual environment (from project root)
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Unix/MacOS

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
# Copy .env-template to .env and configure:
# - DB_HOST, DB_NAME, DB_USER, DB_PASS, DB_PORT (PostgreSQL)
# - SERVER_IP (for ALLOWED_HOSTS)
# - GOOGLE_MAPS_API_KEY (for school registration with Places API)
# - EMAIL_* settings (for approval notifications)
#
# Email Configuration:
# - Development: Use console.EmailBackend (emails print to console, not sent)
# - Production: Use smtp.EmailBackend (emails actually sent via SMTP)
# - Gmail requires App Password: https://myaccount.google.com/apppasswords
```

### Running the Server
```bash
# Navigate to Django project directory
cd digitmile

# Run development server
python manage.py runserver

# Run on specific host/port
python manage.py runserver 0.0.0.0:8000
```

### Database Operations
```bash
# Create migrations after model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser for admin access
python manage.py createsuperuser

# Set up Teachers group with proper permissions
python manage.py setup_teachers_group

# Clean expired captchas
python manage.py captcha_clean

# Pre-generate captcha pool
python manage.py captcha_create_pool
```

### Debugging & Logging
```bash
# View email logs (detailed email sending information)
# Logs are written to: digitmile/logs/email.log
tail -f digitmile/logs/email.log  # Unix/MacOS
Get-Content digitmile/logs/email.log -Wait  # Windows PowerShell

# Console output also shows all email attempts with:
# - Email configuration (backend, host, from/to addresses)
# - Success/failure status
# - Full error tracebacks on failure
```

### Testing & Validation
```bash
# Check for common Django issues
python manage.py check

# Access Django admin
# Navigate to http://localhost:8000/admin/
```

## Architecture

### Project Structure
```
digitmile/                     # Django project root
  manage.py                    # Django management script
  digitmile/                   # Project settings package
    settings.py                # Django settings (uses .env for config)
    urls.py                    # Root URL configuration
    wsgi.py, asgi.py          # WSGI/ASGI applications
  digitmileapi/                # Main application
    models.py                  # Data models
    views.py                   # API views and form views
    serializers.py             # DRF serializers
    urls.py                    # API URL routing
    admin.py                   # Django admin configuration
    forms.py                   # Django forms for registration
    templates/                 # HTML templates
    migrations/                # Database migrations
```

### Data Model Hierarchy

The system uses a strict hierarchical model with status-based registration:

1. **School** - Educational institutions with location data and status tracking
   - Status: PENDING, APPROVED, REJECTED
   - Stores contact person info (who registered) and official school info (director, emails, phones)
   - Custom manager methods: `School.objects.approved()`, `.pending()`, `.rejected()`

2. **Teacher** - Linked to a User account (created on approval) and assigned to 1-3 Schools
   - Status: PENDING, APPROVED, REJECTED
   - User account is `null` until approved
   - Can be assigned to multiple schools via `TeacherSchoolAssignment` through model
   - Each assignment tracks `years_at_school` for that specific school
   - Custom manager methods: `Teacher.objects.approved()`, `.pending()`, `.rejected()`

3. **TeacherSchoolAssignment** - Through model linking Teacher to School with additional data
   - Tracks `years_at_school` for each teacher-school relationship
   - Allows teachers to work at up to 3 schools (enforced in forms)

4. **Classroom** - Has unique `classroom_key`, belongs to one Teacher
   - Teacher can have classrooms across multiple schools

5. **Student** - Belongs to one Classroom, identified by `full_name`

6. **RunStatistics** - Game run records for Students (tracks `player_won`)

**Registration Flow:**
- Schools and Teachers register directly with status='PENDING'
- Schools created with contact person details + official school details
- Teachers created with email (required), no user account yet
- Teachers can select 1-3 schools (including pending schools)
- Admin approves by changing status to 'APPROVED'
- On Teacher approval: User account created, random password generated, email sent with credentials
- On School approval: Email sent to contact person
- Rejected registrations kept for audit trail with status='REJECTED'

### API Endpoints

**Public Endpoints (no authentication):**
- `POST /api/checkClassroomKey/` - Verify classroom key and fetch classroom data
- `POST /api/insertLevelStatistics/` - Submit game run statistics for a student

**Teacher-Only Endpoints (requires authentication + Teachers group):**
- `GET /api/teacher/school/` - View own schools' details (returns list of approved schools)
- `GET /api/teacher/classrooms/` - List own classrooms
- `GET/POST/PUT/PATCH/DELETE /api/teacher/students/` - CRUD students in own classrooms
- `GET /api/teacher/run-statistics/` - View statistics for own students

**Admin-Only Endpoints (superuser required):**
- `GET /api/pending-registrations/` - View pending school/teacher registrations
- `POST /api/approve-school/<id>/` - Approve school registration
- `POST /api/approve-teacher/<id>/` - Approve teacher registration

**Registration Pages:**
- `/register/school/` - School registration form with:
  - Google Maps Places API autocomplete to search for existing schools
  - Draggable marker to set location
  - Auto-fills address, municipality, region from selected place
  - Captcha validation
  - Fields for contact person and official school information

- `/register/teacher/` - Teacher registration form with:
  - Multi-school selection (1-3 schools, both approved and pending)
  - Pending schools shown with warning badge and tooltip
  - Years at each school input (appears when school selected)
  - Selection counter showing X/3 selected
  - Captcha validation

### Authentication & Permissions

**Custom Permission Class:** `IsTeacher`
- Requires user to be authenticated
- Requires user to be in "Teachers" group
- Requires user to have a `teacher_profile` attribute

**Data Scoping:**
- Teachers can only access/modify data within their own classrooms
- Classroom choices are filtered in serializers based on the authenticated teacher
- Django Admin is configured with row-level permissions for teachers

### Key Settings

- **Database:** PostgreSQL (configured via .env)
- **CORS:** Enabled for all origins (`CORS_ALLOW_ALL_ORIGINS=True`)
- **APPEND_SLASH:** Disabled (`APPEND_SLASH=False`)
- **Server IP:** Resolved from `SERVER_IP` environment variable
- **Installed Apps:** DRF, CORS headers, django-simple-captcha

### Important Implementation Notes

1. **Unique Constraints:**
   - School: `(name, municipality, region)` - ensures no duplicate schools
   - Teacher: `email` (unique) - one email per teacher
   - TeacherSchoolAssignment: `(teacher, school)` - one assignment per teacher-school pair
   - Student: `(full_name, classroom)` - unique within classroom

2. **Database Port Handling:**
   - Settings include special logic to handle empty/invalid `DB_PORT` values
   - Defaults to 5432 for PostgreSQL if not specified

3. **Teacher User Creation & Email Notifications:**
   - Username derived from email (part before @)
   - Random 12-character password generated on approval
   - Email sent with credentials to teacher's email address
   - School approval emails sent to contact person
   - Email backend configurable via .env (console for dev, SMTP for production)

4. **Admin Interface:**
   - School and Teacher admins show status in list view
   - Admins can filter by status (PENDING, APPROVED, REJECTED)
   - Teachers have read-only access to their assigned approved schools
   - Teachers can manage students/classrooms with restricted querysets
   - Teachers cannot modify RunStatistics (audit log)
   - Superusers have full access to all models and statuses
   - TeacherSchoolAssignment inline on Teacher admin (max 3)

5. **ViewSets vs APIViews:**
   - `TeacherStudentViewSet` uses ModelViewSet for full CRUD
   - Other teacher endpoints use generic views (ListAPIView, RetrieveAPIView)
   - Public game endpoints use APIView for custom logic

## Development Guidelines

- Models use `related_name` for reverse relationships consistently
- Serializers separate read/write fields (`read_only=True`, `write_only=True`)
- Forms include captcha validation for public registration
- Admin uses `get_queryset()` to scope data access by user role
- Error handling includes traceback printing for debugging
