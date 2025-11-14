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

    # Zoning classification (Phase 2: Simplified Zoning Integration)
    zone_type = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Zoning classification at project location (R-1, R-2, C-1, I-2, etc.)"
    )
    zone_validated = models.BooleanField(
        default=False,
        help_text="Whether zone has been validated against official zoning"
    )

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
    
    def get_barangay_metadata(self):
        """Get related BarangayMetadata if barangay name matches"""
        if not self.barangay:
            return None
        try:
            return BarangayMetadata.objects.get(name=self.barangay)
        except BarangayMetadata.DoesNotExist:
            return None
    
    def detect_and_set_zone(self, save=False):
        """
        Automatically detect and set the zone_type for this project.
        
        Args:
            save: If True, save the project after setting zone_type
            
        Returns:
            tuple: (zone_type, confidence_score) or (None, 0)
        """
        from projeng.zoning_utils import detect_zone_for_project
        
        zone_type, confidence, matched_zone = detect_zone_for_project(self)
        
        if zone_type and confidence >= 30:  # Minimum confidence threshold
            self.zone_type = zone_type
            # Only auto-validate if confidence is very high
            if confidence >= 70:
                self.zone_validated = True
            else:
                self.zone_validated = False
            
            if save:
                self.save(update_fields=['zone_type', 'zone_validated'])
        
        return zone_type, confidence

class ProjectProgress(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='progress_updates')
    date = models.DateField()
    percentage_complete = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Percentage of project completion (0-100)"
    )
    description = models.TextField(help_text="Detailed description of progress made and work completed")
    milestone = models.ForeignKey(
        'ProjectMilestone',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='progress_updates',
        help_text="Optional: Link this progress update to a specific milestone"
    )
    justification = models.TextField(
        blank=True,
        null=True,
        help_text="Justification for the progress increase (required for increases >10%)"
    )
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        verbose_name_plural = "Project Progress"

    def __str__(self):
        return f"{self.project.name} - {self.date} ({self.percentage_complete}%)"

class ProjectMilestone(models.Model):
    """Milestones for tracking project deliverables and progress"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='milestones')
    name = models.CharField(max_length=255, help_text="Name of the milestone/deliverable")
    description = models.TextField(blank=True, null=True, help_text="Description of what this milestone represents")
    target_date = models.DateField(help_text="Expected completion date for this milestone")
    completion_date = models.DateField(blank=True, null=True, help_text="Actual completion date")
    is_completed = models.BooleanField(default=False, help_text="Whether this milestone has been completed")
    estimated_progress_contribution = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Estimated percentage of project completion this milestone represents (0-100)"
    )
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_milestones')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['target_date', 'created_at']
        verbose_name = "Project Milestone"
        verbose_name_plural = "Project Milestones"

    def __str__(self):
        status = "✓" if self.is_completed else "○"
        return f"{status} {self.name} - {self.project.name}"

    def mark_completed(self, completion_date=None):
        """Mark milestone as completed"""
        if completion_date is None:
            from datetime import date
            completion_date = date.today()
        self.is_completed = True
        self.completion_date = completion_date
        self.save()

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


class ZoningZone(models.Model):
    """Detailed zoning classification for specific areas within barangays"""
    
    # Zone Classification Types
    ZONE_TYPE_CHOICES = [
        # Residential
        ('R-1', 'Low Density Residential Zone'),
        ('R-2', 'Medium Density Residential Zone'),
        ('R-3', 'High Density Residential Zone'),
        ('SHZ', 'Socialized Housing Zone'),
        # Commercial
        ('C-1', 'Major Commercial Zone'),
        ('C-2', 'Minor Commercial Zone'),
        # Industrial
        ('I-1', 'Heavy Industrial Zone'),
        ('I-2', 'Light and Medium Industrial Zone'),
        ('AGRO', 'Agro-Industrial Zone'),
        # Other
        ('INS-1', 'Institutional Zone'),
        ('PARKS', 'Parks & Playgrounds/Open Spaces'),
        ('AGRICULTURAL', 'Agricultural Zone'),
        ('ECO-TOURISM', 'Eco-tourism Zone'),
        ('SPECIAL', 'Special Use Zone'),
    ]
    
    zone_type = models.CharField(
        max_length=20, 
        choices=ZONE_TYPE_CHOICES,
        db_index=True,
        help_text="Type of zoning classification"
    )
    barangay = models.CharField(
        max_length=255, 
        db_index=True,
        help_text="Barangay name"
    )
    location_description = models.TextField(
        help_text="Specific locations: subdivisions, roads, sites"
    )
    keywords = models.JSONField(
        default=list,
        help_text="Keywords for matching (subdivision names, road names, etc.)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this zone is currently active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['barangay', 'zone_type']
        verbose_name = 'Zoning Zone'
        verbose_name_plural = 'Zoning Zones'
        indexes = [
            models.Index(fields=['barangay', 'zone_type']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.get_zone_type_display()} - {self.barangay}"
    
    def get_keywords_list(self):
        """Return keywords as a list (for compatibility)"""
        if isinstance(self.keywords, list):
            return self.keywords
        return []


class LandSuitabilityAnalysis(models.Model):
    """Stores land suitability analysis results for projects"""
    
    project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        related_name='suitability_analysis',
        help_text="Project being analyzed"
    )
    
    # Overall Suitability Score (0-100)
    overall_score = models.FloatField(
        help_text="Overall suitability score (0-100)"
    )
    
    # Suitability Category
    SUITABILITY_CHOICES = [
        ('highly_suitable', 'Highly Suitable (80-100)'),
        ('suitable', 'Suitable (60-79)'),
        ('moderately_suitable', 'Moderately Suitable (40-59)'),
        ('marginally_suitable', 'Marginally Suitable (20-39)'),
        ('not_suitable', 'Not Suitable (0-19)'),
    ]
    suitability_category = models.CharField(
        max_length=30,
        choices=SUITABILITY_CHOICES,
        help_text="Suitability category based on score"
    )
    
    # Factor Scores (0-100 each)
    zoning_compliance_score = models.FloatField(
        help_text="Zoning compliance score (0-100)"
    )
    flood_risk_score = models.FloatField(
        help_text="Flood risk assessment score (0-100, higher = less risk)"
    )
    infrastructure_access_score = models.FloatField(
        help_text="Infrastructure access score (0-100)"
    )
    elevation_suitability_score = models.FloatField(
        help_text="Elevation suitability score (0-100)"
    )
    economic_alignment_score = models.FloatField(
        help_text="Economic zone alignment score (0-100)"
    )
    population_density_score = models.FloatField(
        help_text="Population density appropriateness score (0-100)"
    )
    
    # Risk Factors
    has_flood_risk = models.BooleanField(default=False)
    has_slope_risk = models.BooleanField(default=False)
    has_zoning_conflict = models.BooleanField(default=False)
    has_infrastructure_gap = models.BooleanField(default=False)
    
    # Recommendations and Constraints
    recommendations = models.JSONField(
        default=list,
        help_text="List of recommendations for improving suitability"
    )
    constraints = models.JSONField(
        default=list,
        help_text="List of constraints or limitations"
    )
    
    # Analysis Metadata
    analyzed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    analysis_version = models.CharField(
        max_length=20,
        default='1.0',
        help_text="Version of analysis algorithm used"
    )
    
    class Meta:
        verbose_name = "Land Suitability Analysis"
        verbose_name_plural = "Land Suitability Analyses"
        ordering = ['-analyzed_at']
    
    def __str__(self):
        return f"{self.project.name} - {self.get_suitability_category_display()} ({self.overall_score:.1f})"
    
    def get_score_color(self):
        """Get color class for suitability score"""
        if self.overall_score >= 80:
            return 'success'  # Green
        elif self.overall_score >= 60:
            return 'info'  # Blue
        elif self.overall_score >= 40:
            return 'warning'  # Yellow
        elif self.overall_score >= 20:
            return 'warning'  # Orange
        else:
            return 'danger'  # Red


class SuitabilityCriteria(models.Model):
    """Configurable criteria and weights for suitability analysis"""
    
    name = models.CharField(
        max_length=100,
        unique=True,
        default='default',
        help_text="Name of criteria configuration"
    )
    
    # Weights for each factor (must sum to 1.0)
    weight_zoning = models.FloatField(
        default=0.30,
        help_text="Weight for zoning compliance (0-1)"
    )
    weight_flood_risk = models.FloatField(
        default=0.25,
        help_text="Weight for flood risk (0-1)"
    )
    weight_infrastructure = models.FloatField(
        default=0.20,
        help_text="Weight for infrastructure access (0-1)"
    )
    weight_elevation = models.FloatField(
        default=0.15,
        help_text="Weight for elevation suitability (0-1)"
    )
    weight_economic = models.FloatField(
        default=0.05,
        help_text="Weight for economic alignment (0-1)"
    )
    weight_population = models.FloatField(
        default=0.05,
        help_text="Weight for population density (0-1)"
    )
    
    # Project Type Specific Settings
    PROJECT_TYPE_CHOICES = [
        ('all', 'All Project Types'),
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
        ('industrial', 'Industrial'),
        ('infrastructure', 'Infrastructure'),
        ('institutional', 'Institutional'),
    ]
    project_type = models.CharField(
        max_length=20,
        choices=PROJECT_TYPE_CHOICES,
        default='all',
        help_text="Project type this criteria applies to"
    )
    
    # Additional parameters (stored as JSON for flexibility)
    parameters = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        help_text="Additional parameters for scoring (thresholds, ranges, etc.)"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Suitability Criteria"
        verbose_name_plural = "Suitability Criteria"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_project_type_display()})"
    
    def clean(self):
        """Validate that weights sum to approximately 1.0"""
        from django.core.exceptions import ValidationError
        total = (
            self.weight_zoning +
            self.weight_flood_risk +
            self.weight_infrastructure +
            self.weight_elevation +
            self.weight_economic +
            self.weight_population
        )
        if abs(total - 1.0) > 0.01:  # Allow small floating point errors
            raise ValidationError(f"Weights must sum to 1.0, currently sum to {total:.2f}")
    
    def save(self, *args, **kwargs):
        """Override save to validate weights"""
        self.full_clean()
        super().save(*args, **kwargs)


class ProjectType(models.Model):
    """Defines project types and their characteristics"""
    
    PROJECT_TYPE_CHOICES = [
        # Residential
        ('single_family_house', 'Single Family House'),
        ('multi_family_house', 'Multi-Family House'),
        ('apartment_building', 'Apartment Building (3-5 stories)'),
        ('high_rise_residential', 'High-Rise Residential (6+ stories)'),
        ('socialized_housing', 'Socialized Housing'),
        # Commercial
        ('retail_store', 'Retail Store'),
        ('shopping_mall', 'Shopping Mall'),
        ('office_building', 'Office Building'),
        ('hotel', 'Hotel'),
        ('restaurant', 'Restaurant'),
        # Industrial
        ('light_industrial', 'Light Industrial Facility'),
        ('heavy_industrial', 'Heavy Industrial Facility'),
        ('warehouse', 'Warehouse'),
        ('factory', 'Factory'),
        # Infrastructure
        ('road', 'Road/Highway'),
        ('bridge', 'Bridge'),
        ('water_system', 'Water System'),
        ('sewer_system', 'Sewer System'),
        # Institutional
        ('school', 'School'),
        ('hospital', 'Hospital'),
        ('government_building', 'Government Building'),
        ('church', 'Church/Religious Building'),
        # Other
        ('park', 'Park/Recreation'),
        ('cemetery', 'Cemetery'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50, unique=True, choices=PROJECT_TYPE_CHOICES)
    description = models.TextField(blank=True)
    
    # Characteristics
    density_level = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low Density'),
            ('medium', 'Medium Density'),
            ('high', 'High Density'),
        ],
        help_text="Density level of this project type"
    )
    
    height_category = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low (1-2 stories)'),
            ('medium', 'Medium (3-5 stories)'),
            ('high', 'High (6+ stories)'),
        ],
        blank=True,
        null=True
    )
    
    requires_industrial = models.BooleanField(
        default=False,
        help_text="Requires industrial zone"
    )
    
    requires_commercial = models.BooleanField(
        default=False,
        help_text="Requires commercial zone"
    )
    
    requires_residential = models.BooleanField(
        default=False,
        help_text="Requires residential zone"
    )
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Project Type'
        verbose_name_plural = 'Project Types'
    
    def __str__(self):
        return self.name


class ZoneAllowedUse(models.Model):
    """Defines which project types are allowed in each zone"""
    
    ZONE_CHOICES = [
        ('R1', 'Low Density Residential'),
        ('R2', 'Medium Density Residential'),
        ('R3', 'High Density Residential'),
        ('SHZ', 'Socialized Housing Zone'),
        ('C1', 'Major Commercial Zone'),
        ('C2', 'Minor Commercial Zone'),
        ('I1', 'Heavy Industrial Zone'),
        ('I2', 'Light and Medium Industrial Zone'),
        ('Al', 'Agro-Industrial'),
        ('In', 'Institutional'),
        ('Ag', 'Agricultural'),
        ('Cu', 'Cultural'),
    ]
    
    zone_type = models.CharField(max_length=10, choices=ZONE_CHOICES, db_index=True)
    project_type = models.ForeignKey(
        'ProjectType',
        on_delete=models.CASCADE,
        related_name='allowed_zones'
    )
    
    # Permissions
    is_primary_use = models.BooleanField(
        default=True,
        help_text="Primary allowed use (vs conditional use)"
    )
    
    is_conditional = models.BooleanField(
        default=False,
        help_text="Requires special permit/approval"
    )
    
    conditions = models.TextField(
        blank=True,
        help_text="Conditions or restrictions for this use"
    )
    
    # Density restrictions
    max_density = models.CharField(
        max_length=50,
        blank=True,
        help_text="Maximum density allowed (e.g., '50 units/hectare')"
    )
    
    max_height = models.CharField(
        max_length=50,
        blank=True,
        help_text="Maximum height allowed (e.g., '5 stories')"
    )
    
    class Meta:
        unique_together = ['zone_type', 'project_type']
        verbose_name = 'Zone Allowed Use'
        verbose_name_plural = 'Zone Allowed Uses'
        indexes = [
            models.Index(fields=['zone_type']),
        ]
    
    def __str__(self):
        return f"{self.zone_type} - {self.project_type.name}"


class ZoneRecommendation(models.Model):
    """Stores zone recommendations for projects"""
    
    project = models.ForeignKey(
        'Project',
        on_delete=models.CASCADE,
        related_name='zone_recommendations'
    )
    
    recommended_zone = models.CharField(
        max_length=10,
        help_text="Recommended zone type"
    )
    
    # Scores
    overall_score = models.FloatField(
        help_text="Overall MCDA score (0-100)"
    )
    
    # Factor scores
    zoning_compliance_score = models.FloatField(default=0)
    land_availability_score = models.FloatField(default=0)
    accessibility_score = models.FloatField(default=0)
    community_impact_score = models.FloatField(default=0)
    infrastructure_score = models.FloatField(default=0)
    
    # Ranking
    rank = models.IntegerField(
        help_text="Rank among all recommendations (1 = best)"
    )
    
    # Reasoning
    reasoning = models.TextField(
        help_text="Why this zone is recommended"
    )
    
    advantages = models.JSONField(
        default=list,
        help_text="List of advantages for this zone"
    )
    
    constraints = models.JSONField(
        default=list,
        help_text="List of constraints or limitations"
    )
    
    is_selected = models.BooleanField(
        default=False,
        help_text="Whether this recommendation was selected"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['project', 'rank']
        unique_together = ['project', 'recommended_zone']
        verbose_name = 'Zone Recommendation'
        verbose_name_plural = 'Zone Recommendations'
    
    def __str__(self):
        return f"{self.project.name} → {self.recommended_zone} (Score: {self.overall_score})" 