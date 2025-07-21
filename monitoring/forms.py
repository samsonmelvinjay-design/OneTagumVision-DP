from django import forms
from projeng.models import Project
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError

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