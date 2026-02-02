from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()

# Import custom storage backend
def get_media_storage():
    """Get the appropriate storage backend for media files"""
    try:
        if getattr(settings, 'SPACES_CONFIGURED', False):
            from projeng.storage import PublicMediaStorage
            if PublicMediaStorage:
                return PublicMediaStorage()
    except (ImportError, AttributeError):
        pass
    return None

MEDIA_STORAGE = get_media_storage()

class Project(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('delayed', 'Delayed'),
    ]

    prn = models.CharField(max_length=50, blank=True, null=True, unique=True, db_index=True)
    barangay = models.CharField(max_length=100, blank=True, null=True)
    project_cost = models.CharField(max_length=100, blank=True, null=True)
    source_of_funds = models.CharField(max_length=100, blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    name = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    progress = models.PositiveIntegerField(default=0, help_text="Project progress in percentage (0-100)", blank=True, null=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to='project_images/', blank=True, null=True, storage=MEDIA_STORAGE)
    assigned_engineers = models.ManyToManyField(User, related_name="assigned_monitoring_projects", blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'

    def get_status_display_class(self):
        status_classes = {
            'completed': 'success',
            'in_progress': 'info',
            'pending': 'warning',
            'delayed': 'danger'
        }
        return status_classes.get(self.status, 'secondary') 