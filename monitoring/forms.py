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
            'status', 'project_type', 'zone_type', 'latitude', 'longitude', 'start_date', 'end_date', 'image', 'assigned_engineers'
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
        
        # Make location required - must be selected via map picker
        self.fields['latitude'].required = True
        self.fields['longitude'].required = True
        self.fields['latitude'].help_text = 'Click "Select Location on Map" to set coordinates'
        self.fields['longitude'].help_text = 'Click "Select Location on Map" to set coordinates'
        self.fields['latitude'].widget.attrs['readonly'] = True
        self.fields['longitude'].widget.attrs['readonly'] = True
        self.fields['latitude'].widget.attrs['placeholder'] = 'Click map to set'
        self.fields['longitude'].widget.attrs['placeholder'] = 'Click map to set'
        
        # Configure project_type field
        if 'project_type' in self.fields:
            from projeng.models import ProjectType
            self.fields['project_type'].queryset = ProjectType.objects.all().order_by('name')
            self.fields['project_type'].required = False
            self.fields['project_type'].help_text = 'Select the type of project for zone compatibility recommendations'
            self.fields['project_type'].widget.attrs['class'] = 'rounded-lg border border-gray-300 px-4 py-2.5 focus:ring-2 focus:ring-blue-400 focus:border-blue-400 outline-none'
        
        # Configure zone_type field
        if 'zone_type' in self.fields:
            self.fields['zone_type'].required = False
            self.fields['zone_type'].help_text = 'Recommended zone will be shown after selecting project type and location'
            self.fields['zone_type'].widget.attrs['class'] = 'rounded-lg border border-gray-300 px-4 py-2.5 focus:ring-2 focus:ring-blue-400 focus:border-blue-400 outline-none'

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status', '').lower()
        barangay = cleaned_data.get('barangay')
        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')
        
        # Location is always required
        errors = {}
        if not latitude or latitude == '':
            errors['latitude'] = 'Location is required. Please select a location on the map using the "Select Location on Map" button.'
        if not longitude or longitude == '':
            errors['longitude'] = 'Location is required. Please select a location on the map using the "Select Location on Map" button.'
        
        # Validate coordinate ranges (Tagum City is approximately 7.3-7.5°N, 125.7-125.9°E)
        if latitude:
            try:
                lat_float = float(latitude)
                if lat_float < 7.0 or lat_float > 8.0:
                    errors['latitude'] = 'Latitude must be within Tagum City bounds (approximately 7.0-8.0°N). Please select a valid location on the map.'
            except (ValueError, TypeError):
                errors['latitude'] = 'Invalid latitude value. Please select a location on the map.'
        
        if longitude:
            try:
                lng_float = float(longitude)
                if lng_float < 125.0 or lng_float > 126.0:
                    errors['longitude'] = 'Longitude must be within Tagum City bounds (approximately 125.0-126.0°E). Please select a valid location on the map.'
            except (ValueError, TypeError):
                errors['longitude'] = 'Invalid longitude value. Please select a location on the map.'
        
        if status == 'delayed':
            if not barangay:
                errors['barangay'] = 'Barangay is required for delayed projects.'
        
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
            # Add user to Project Engineer group (create it if missing)
            project_engineer_group, _ = Group.objects.get_or_create(name='Project Engineer')
            user.groups.add(project_engineer_group)
        return user


class EngineerEditForm(forms.ModelForm):
    """Form for editing an existing Project Engineer account"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.password_updated = False

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
    new_password = forms.CharField(
        required=False,
        min_length=8,
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter new password'}),
        label='New Password',
        help_text='Leave blank to keep the current password.'
    )
    confirm_new_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm new password'}),
        label='Confirm New Password'
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

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_new_password = cleaned_data.get('confirm_new_password')

        if new_password or confirm_new_password:
            if not new_password:
                self.add_error('new_password', 'Please enter a new password.')
            elif not confirm_new_password:
                self.add_error('confirm_new_password', 'Please confirm the new password.')
            elif new_password != confirm_new_password:
                self.add_error('confirm_new_password', 'Passwords do not match.')
            else:
                try:
                    validate_password(new_password, self.instance)
                except ValidationError as e:
                    self.add_error('new_password', e)

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        new_password = self.cleaned_data.get('new_password')
        self.password_updated = False

        if new_password:
            user.set_password(new_password)
            self.password_updated = True

        if commit:
            user.save()

        return user
