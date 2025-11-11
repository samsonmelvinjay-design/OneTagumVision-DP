from django.db import models
# from django.contrib.gis.db import models as gis_models  # Temporarily disabled
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
    # geometry = gis_models.GeometryField()  # Temporarily disabled - GIS functionality
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

class BarangayMetadata(models.Model):
    """Metadata and zoning information for barangays in Tagum City"""
    
    # Basic Info
    name = models.CharField(max_length=255, unique=True, db_index=True)
    
    # Population & Demographics
    population = models.IntegerField(null=True, blank=True)
    land_area = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Land area in km²")
    density = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Population density in people/km²")
    growth_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Population growth rate in %")
    
    # Zoning Classifications
    BARANGAY_CLASS_CHOICES = [
        ('urban', 'Urban'),
        ('rural', 'Rural'),
    ]
    barangay_class = models.CharField(
        max_length=10, 
        choices=BARANGAY_CLASS_CHOICES, 
        null=True, 
        blank=True,
        help_text="Urban or Rural classification"
    )
    
    ECONOMIC_CLASS_CHOICES = [
        ('growth_center', 'Growth Center'),
        ('emerging', 'Emerging'),
        ('satellite', 'Satellite'),
    ]
    economic_class = models.CharField(
        max_length=20, 
        choices=ECONOMIC_CLASS_CHOICES, 
        null=True, 
        blank=True,
        help_text="Economic development classification"
    )
    
    ELEVATION_CHOICES = [
        ('highland', 'Highland/Rolling'),
        ('plains', 'Plains/Lowland'),
        ('coastal', 'Coastal'),
    ]
    elevation_type = models.CharField(
        max_length=20, 
        choices=ELEVATION_CHOICES, 
        null=True, 
        blank=True,
        help_text="Geographic elevation classification"
    )
    
    # Industrial Zones (can be multiple)
    INDUSTRIAL_ZONE_CHOICES = [
        ('cbd', 'Central Business District'),
        ('urban_expansion', 'Urban Expansion Area'),
        ('commercial_expansion', 'Commercial Expansion Area'),
        ('institutional_recreational', 'Institutional & Recreational'),
        ('agro_industrial', 'Agro-Industrial'),
    ]
    industrial_zones = models.JSONField(
        default=list, 
        help_text="List of industrial zone types (can be multiple)"
    )
    
    # Additional Metadata
    primary_industries = models.JSONField(
        default=list,
        help_text="List of primary industries (agriculture, tourism, etc.)"
    )
    special_features = models.JSONField(
        default=list,
        help_text="Special facilities (hospitals, markets, ports, etc.)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    data_source = models.CharField(
        max_length=255, 
        default="PSA-2020 CPH",
        help_text="Source of demographic data"
    )
    data_year = models.IntegerField(default=2020, help_text="Year of data collection")
    
    class Meta:
        ordering = ['name']
        verbose_name_plural = "Barangay Metadata"
    
    def __str__(self):
        class_display = self.get_barangay_class_display() if self.barangay_class else "Unclassified"
        return f"{self.name} ({class_display})"
    
    def get_zoning_summary(self):
        """Return a summary string of all zoning classifications"""
        parts = []
        if self.barangay_class:
            parts.append(self.get_barangay_class_display())
        if self.economic_class:
            parts.append(self.get_economic_class_display())
        if self.elevation_type:
            parts.append(self.get_elevation_type_display())
        return " | ".join(parts) if parts else "Unclassified" 