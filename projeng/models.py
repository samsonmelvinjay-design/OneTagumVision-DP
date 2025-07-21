from django.db import models
from django.contrib.gis.db import models as gis_models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings

class Layer(models.Model):
    LAYER_TYPES = [
        ('project', 'Project'),
        ('area', 'Area'),
        ('point', 'Point of Interest'),
    ]

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=20, choices=LAYER_TYPES)
    geometry = gis_models.GeometryField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"

class Project(models.Model):
    STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('delayed', 'Delayed'),
    ]

    prn = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    barangay = models.CharField(max_length=255, blank=True, null=True)
    project_cost = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    source_of_funds = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    image = models.ImageField(upload_to='project_images/', blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_projects')
    assigned_engineers = models.ManyToManyField(User, related_name='assigned_projects', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_update = models.DateField(blank=True, null=True)
    progress = models.PositiveIntegerField(default=0, help_text="Project progress in percentage (0-100)", blank=True, null=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_status_display_class(self):
        status_classes = {
            'completed': 'success',
            'in_progress': 'info',
            'planned': 'warning',
            'cancelled': 'danger',
            'delayed': 'danger'
        }
        return status_classes.get(self.status, 'secondary')

class ProjectProgress(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='progress_updates')
    date = models.DateField()
    percentage_complete = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Percentage of project completion (0-100)"
    )
    description = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        verbose_name_plural = "Project Progress"

    def __str__(self):
        return f"{self.project.name} - {self.date} ({self.percentage_complete}%)"

class ProjectCost(models.Model):
    COST_TYPES = [
        ('material', 'Material'),
        ('labor', 'Labor'),
        ('equipment', 'Equipment'),
        ('other', 'Other'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='costs')
    date = models.DateField()
    cost_type = models.CharField(max_length=20, choices=COST_TYPES)
    description = models.TextField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    receipt = models.FileField(upload_to='cost_receipts/', blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.project.name} - {self.get_cost_type_display()} ({self.amount})"

class ProgressPhoto(models.Model):
    progress_update = models.ForeignKey(ProjectProgress, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='progress_photos/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Photo for {self.progress_update.project.name} on {self.uploaded_at.strftime('%Y-%m-%d')}"

class ProjectDocument(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='documents')
    file = models.FileField(upload_to='project_documents/')
    name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.name 

class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f'Notification for {self.recipient.username}: {self.message[:50]}' 