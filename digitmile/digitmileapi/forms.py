from django import forms
from django.contrib.auth.models import User
from .models import School, Teacher

class TeacherRegistrationForm(forms.ModelForm):
    username = forms.CharField(max_length=150, required=True, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.')
    password = forms.CharField(widget=forms.PasswordInput, help_text='Your password.')
    password_confirm = forms.CharField(widget=forms.PasswordInput, label="Confirm password", help_text='Enter the same password as before, for verification.')
    first_name = forms.CharField(max_length=30, required=False, help_text='Optional.')
    last_name = forms.CharField(max_length=150, required=False, help_text='Optional.')
    email = forms.EmailField(max_length=254, help_text='Required. Inform a valid email address.')
    school = forms.ModelChoiceField(queryset=School.objects.all(), required=True, help_text='Select the school where the teacher works.')

    class Meta:
        model = User # Base the form on User to handle username, password etc.
        fields = ['username', 'first_name', 'last_name', 'email'] # Fields from User model

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("A user with that username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email address is already in use.")
        return email

    def clean_password_confirm(self):
        password = self.cleaned_data.get("password")
        password_confirm = self.cleaned_data.get("password_confirm")
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Passwords don't match.")
        return password_confirm

    def save(self, commit=True):
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password'],
            first_name=self.cleaned_data.get('first_name', ''),
            last_name=self.cleaned_data.get('last_name', ''),
            is_staff=True  # Make the new teacher a staff member
        )
        
        # The Teacher model's full_name might be redundant if User's first/last name are used.
        # For now, let's construct it from User's names.
        # Consider if Teacher.full_name should be removed or populated differently.
        teacher_full_name = f"{user.first_name} {user.last_name}".strip()
        if not teacher_full_name and user.username: # Fallback to username if names are empty
             teacher_full_name = user.username

        teacher_profile = Teacher.objects.create(
            user=user,
            school=self.cleaned_data['school'],
            full_name=teacher_full_name # Populate Teacher.full_name
        )
        
        # Add user to "Teachers" group
        from django.contrib.auth.models import Group
        teachers_group = Group.objects.get(name='Teachers')
        user.groups.add(teachers_group)

        return user, teacher_profile
