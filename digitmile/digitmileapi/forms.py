from django import forms
from captcha.fields import CaptchaField
from .models import UnregisteredSchool, UnregisteredTeacher, School

class UnregisteredSchoolForm(forms.ModelForm):
    latitude = forms.FloatField(widget=forms.HiddenInput(), required=False)
    longitude = forms.FloatField(widget=forms.HiddenInput(), required=False)
    captcha = CaptchaField()

    class Meta:
        model = UnregisteredSchool
        fields = ['name', 'municipality', 'region', 'contact_person_name', 'contact_person_email', 'latitude', 'longitude']

class UnregisteredTeacherForm(forms.ModelForm):
    school = forms.ModelChoiceField(queryset=School.objects.all(), required=True, help_text='Select the school where you work.')
    captcha = CaptchaField()
    class Meta:
        model = UnregisteredTeacher
        fields = ['full_name', 'email', 'school']
