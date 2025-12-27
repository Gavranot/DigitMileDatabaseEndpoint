from django import forms
from captcha.fields import CaptchaField
from .models import School, Teacher

class SchoolRegistrationForm(forms.ModelForm):
    """Form for registering a new school (will be created with PENDING status)"""
    latitude = forms.FloatField(widget=forms.HiddenInput(), required=False)
    longitude = forms.FloatField(widget=forms.HiddenInput(), required=False)
    google_maps_address = forms.CharField(widget=forms.HiddenInput(), required=False)
    captcha = CaptchaField()

    class Meta:
        model = School
        fields = [
            'name', 'municipality', 'region',
            'contact_person_name', 'contact_person_email', 'contact_person_phone',
            'director_name', 'director_email',
            'school_email', 'school_phone',
            'address', 'google_maps_address', 'website',
            'latitude', 'longitude'
        ]
        labels = {
            'contact_person_name': 'Contact Person Name',
            'contact_person_email': 'Contact Person Email',
            'contact_person_phone': 'Contact Person Phone Number',
            'director_name': 'School Director Name',
            'director_email': 'School Director Email',
            'school_email': 'Official School Email',
            'school_phone': 'Official School Phone Number',
            'address': 'School Address',
            'website': 'School Website',
        }
        help_texts = {
            'address': 'Enter the school address manually',
            'google_maps_address': 'This will be automatically filled from the map pin',
            'website': 'School website URL (optional)',
            'contact_person_name': 'Person submitting this registration',
            'contact_person_email': 'Email of person submitting this registration',
            'contact_person_phone': 'Phone of person submitting this registration',
            'director_name': 'Name of the school director/principal',
            'director_email': 'Email of the school director',
            'school_email': 'Official school email address',
            'school_phone': 'Official school phone number',
        }

class TeacherRegistrationForm(forms.Form):
    """
    Custom form for teacher registration that handles multiple schools and years at each.
    We use a Form instead of ModelForm because of the complex many-to-many with extra data.
    """
    full_name = forms.CharField(max_length=255, label='Full Name')
    email = forms.EmailField(label='Email Address')
    years_teaching = forms.IntegerField(
        required=False,
        min_value=0,
        label='Total Years Teaching',
        help_text='Total years of teaching experience'
    )
    phone_number = forms.CharField(max_length=50, required=False, label='Phone Number')

    # School selection - now just one queryset with all schools (pending and approved)
    schools = forms.ModelMultipleChoiceField(
        queryset = School.objects.filter(
            status__in=['PENDING', 'APPROVED']
        ).order_by('status', 'name'),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Select Schools (minimum 1, maximum 3)',
        help_text='Select up to 3 schools where you work. Pending schools are marked with a warning.'
    )

    # Dynamic fields for years at each school will be added via JavaScript
    # and processed in the view

    captcha = CaptchaField()

    def clean(self):
        cleaned_data = super().clean()
        schools = cleaned_data.get('schools', [])

        if len(schools) == 0:
            raise forms.ValidationError('You must select at least one school.')

        if len(schools) > 3:
            raise forms.ValidationError('You can select a maximum of 3 schools.')

        return cleaned_data
