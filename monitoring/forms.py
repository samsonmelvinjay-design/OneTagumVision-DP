from django import forms
from projeng.models import Project
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            'prn', 'name', 'description', 'barangay', 'project_cost', 'source_of_funds',
            'status', 'latitude', 'longitude', 'start_date', 'end_date', 'image', 'assigned_engineers'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter the queryset for assigned_engineers to only include Project Engineers
        try:
            project_engineer_group = Group.objects.get(name='Project Engineer')
            self.fields['assigned_engineers'].queryset = User.objects.filter(groups=project_engineer_group)
        except Group.DoesNotExist:
            # If the group doesn't exist, show no users in the dropdown
            self.fields['assigned_engineers'].queryset = User.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status', '').lower()
        barangay = cleaned_data.get('barangay')
        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')
        if status == 'delayed':
            errors = {}
            if not barangay:
                errors['barangay'] = 'Barangay is required for delayed projects.'
            if latitude is None or latitude == '':
                errors['latitude'] = 'Latitude is required for delayed projects.'
            if longitude is None or longitude == '':
                errors['longitude'] = 'Longitude is required for delayed projects.'
            if errors:
                raise ValidationError(errors)
        return cleaned_data


class EngineerCreateForm(forms.ModelForm):
    """Form for creating a new Project Engineer account"""
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label='Password',
        help_text='Password must be at least 8 characters long.',
        min_length=8
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label='Confirm Password'
    )
    phone = forms.CharField(
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={'placeholder': '+63 912 345 6789'})
    )
    department = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'Department'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError('A user with this username already exists.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('A user with this email already exists.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password:
            if password != confirm_password:
                raise ValidationError({'confirm_password': 'Passwords do not match.'})
            
            # Validate password using Django's password validators
            try:
                validate_password(password)
            except ValidationError as e:
                raise ValidationError({'password': e.messages})

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        # Note: phone and department fields are not saved as they're not part of User model
        # These can be added to a UserProfile model in the future if needed
        if commit:
            user.save()
            # Add user to Project Engineer group
            try:
                project_engineer_group = Group.objects.get(name='Project Engineer')
                user.groups.add(project_engineer_group)
            except Group.DoesNotExist:
                pass
        return user


class EngineerEditForm(forms.ModelForm):
    """Form for editing an existing Project Engineer account"""
    phone = forms.CharField(
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={'placeholder': '+63 912 345 6789'})
    )
    department = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'Department'})
    )

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Check if email is already taken by another user
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError('A user with this email already exists.')
        return email 