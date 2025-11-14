from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import (
    Layer, Project, ProjectProgress, ProjectCost, ProgressPhoto, 
    BarangayMetadata, ZoningZone, ProjectMilestone,
    LandSuitabilityAnalysis, SuitabilityCriteria,
    ProjectType, ZoneAllowedUse, ZoneRecommendation
)
from django.contrib.auth.models import Group

@admin.register(Layer)
class LayerAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'created_by', 'created_at')
    list_filter = ('type', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'prn', 'barangay', 'status', 'start_date', 'end_date', 'created_by', 'created_at')
    list_filter = ('status', 'barangay', 'created_at', 'start_date', 'end_date')
    search_fields = ('name', 'prn', 'barangay', 'description')
    readonly_fields = ('created_at', 'updated_at', 'last_update')
    filter_horizontal = ('assigned_engineers',)
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'prn', 'description', 'image')
        }),
        ('Location', {
            'fields': ('barangay', 'latitude', 'longitude', 'zone_type', 'zone_validated')
        }),
        ('Project Details', {
            'fields': ('project_cost', 'source_of_funds', 'status', 'start_date', 'end_date')
        }),
        ('Team', {
            'fields': ('created_by', 'assigned_engineers')
        }),
        ('Timeline', {
            'fields': ('created_at', 'updated_at', 'last_update')
        }),
    )
    list_per_page = 20
    ordering = ('-created_at',)

    def get_list_display_links(self, request, list_display):
        return ['name', 'prn']

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "assigned_engineers":
            try:
                project_engineer_group = Group.objects.get(name='Project Engineer')
                kwargs["queryset"] = User.objects.filter(groups=project_engineer_group)
            except Group.DoesNotExist:
                kwargs["queryset"] = User.objects.none()
        return super().formfield_for_manytomany(db_field, request, **kwargs)

@admin.register(ProjectMilestone)
class ProjectMilestoneAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'target_date', 'is_completed', 'estimated_progress_contribution', 'created_by')
    list_filter = ('is_completed', 'target_date', 'created_at')
    search_fields = ('name', 'project__name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'target_date'

@admin.register(ProjectProgress)
class ProjectProgressAdmin(admin.ModelAdmin):
    list_display = ('project', 'date', 'percentage_complete', 'milestone', 'created_by', 'created_at')
    list_filter = ('date', 'created_at', 'milestone')
    search_fields = ('project__name', 'description', 'justification')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Progress Information', {
            'fields': ('project', 'date', 'percentage_complete', 'description', 'milestone', 'justification')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at')
        }),
    )

@admin.register(ProjectCost)
class ProjectCostAdmin(admin.ModelAdmin):
    list_display = ('project', 'date', 'cost_type', 'amount', 'created_by', 'created_at')
    list_filter = ('cost_type', 'date', 'created_at')
    search_fields = ('project__name', 'description')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Cost Information', {
            'fields': ('project', 'date', 'cost_type', 'description', 'amount', 'receipt')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at')
        }),
    )

@admin.register(ProgressPhoto)
class ProgressPhotoAdmin(admin.ModelAdmin):
    list_display = ('progress_update', 'uploaded_at')
    list_filter = ('uploaded_at',)
    search_fields = ('progress_update__project__name',)
    readonly_fields = ('uploaded_at',)

@admin.register(ZoningZone)
class ZoningZoneAdmin(admin.ModelAdmin):
    """
    Admin interface for Zoning Zones.
    Head Engineers (admins) can manage zoning classifications.
    """
    list_display = [
        'zone_type',
        'barangay',
        'location_description',
        'is_active',
        'created_at'
    ]
    list_filter = [
        'zone_type',
        'barangay',
        'is_active',
        'created_at'
    ]
    search_fields = [
        'barangay',
        'location_description',
        'zone_type'
    ]
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Zone Information', {
            'fields': ('zone_type', 'barangay', 'is_active')
        }),
        ('Location Details', {
            'fields': ('location_description', 'keywords')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    list_per_page = 25
    ordering = ['barangay', 'zone_type']

@admin.register(BarangayMetadata)
class BarangayMetadataAdmin(admin.ModelAdmin):
    """
    Admin interface for Barangay Metadata.
    Note: Head Engineers are admins (is_head_engineer checks for is_superuser),
    so they automatically have access to Django admin.
    """
    list_display = [
        'name', 
        'barangay_class', 
        'economic_class', 
        'elevation_type',
        'population',
        'density',
        'growth_rate'
    ]
    list_filter = [
        'barangay_class',
        'economic_class',
        'elevation_type',
        'data_year'
    ]
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name',)
        }),
        ('Demographics', {
            'fields': ('population', 'land_area', 'density', 'growth_rate')
        }),
        ('Zoning Classifications', {
            'fields': ('barangay_class', 'economic_class', 'elevation_type', 'industrial_zones')
        }),
        ('Additional Information', {
            'fields': ('primary_industries', 'special_features')
        }),
        ('Data Source', {
            'fields': ('data_source', 'data_year', 'created_at', 'updated_at')
        }),
    )
    list_per_page = 25

@admin.register(LandSuitabilityAnalysis)
class LandSuitabilityAnalysisAdmin(admin.ModelAdmin):
    """
    Admin interface for Land Suitability Analysis results.
    """
    list_display = [
        'project',
        'overall_score',
        'suitability_category',
        'zoning_compliance_score',
        'flood_risk_score',
        'has_zoning_conflict',
        'has_flood_risk',
        'analyzed_at'
    ]
    list_filter = [
        'suitability_category',
        'has_flood_risk',
        'has_slope_risk',
        'has_zoning_conflict',
        'has_infrastructure_gap',
        'analyzed_at'
    ]
    search_fields = [
        'project__name',
        'project__barangay',
        'project__prn'
    ]
    readonly_fields = [
        'analyzed_at',
        'updated_at',
        'analysis_version'
    ]
    fieldsets = (
        ('Project', {
            'fields': ('project',)
        }),
        ('Overall Assessment', {
            'fields': ('overall_score', 'suitability_category', 'analysis_version')
        }),
        ('Factor Scores', {
            'fields': (
                'zoning_compliance_score',
                'flood_risk_score',
                'infrastructure_access_score',
                'elevation_suitability_score',
                'economic_alignment_score',
                'population_density_score'
            )
        }),
        ('Risk Factors', {
            'fields': (
                'has_flood_risk',
                'has_slope_risk',
                'has_zoning_conflict',
                'has_infrastructure_gap'
            )
        }),
        ('Analysis Results', {
            'fields': ('recommendations', 'constraints')
        }),
        ('Timestamps', {
            'fields': ('analyzed_at', 'updated_at')
        }),
    )
    list_per_page = 25
    ordering = ['-analyzed_at']

@admin.register(SuitabilityCriteria)
class SuitabilityCriteriaAdmin(admin.ModelAdmin):
    """
    Admin interface for Suitability Criteria configuration.
    """
    list_display = [
        'name',
        'project_type',
        'weight_zoning',
        'weight_flood_risk',
        'weight_infrastructure',
        'is_active',
        'created_at'
    ]
    list_filter = [
        'project_type',
        'is_active',
        'created_at'
    ]
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'project_type', 'is_active')
        }),
        ('Factor Weights (must sum to 1.0)', {
            'fields': (
                'weight_zoning',
                'weight_flood_risk',
                'weight_infrastructure',
                'weight_elevation',
                'weight_economic',
                'weight_population'
            ),
            'description': 'All weights must sum to 1.0'
        }),
        ('Additional Parameters', {
            'fields': ('parameters',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    list_per_page = 25
    ordering = ['name']

@admin.register(ProjectType)
class ProjectTypeAdmin(admin.ModelAdmin):
    """
    Admin interface for Project Types.
    """
    list_display = [
        'name',
        'code',
        'density_level',
        'height_category',
        'requires_residential',
        'requires_commercial',
        'requires_industrial'
    ]
    list_filter = [
        'density_level',
        'height_category',
        'requires_residential',
        'requires_commercial',
        'requires_industrial'
    ]
    search_fields = ['name', 'code', 'description']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'description')
        }),
        ('Characteristics', {
            'fields': ('density_level', 'height_category')
        }),
        ('Zone Requirements', {
            'fields': ('requires_residential', 'requires_commercial', 'requires_industrial')
        }),
    )
    list_per_page = 25
    ordering = ['name']

@admin.register(ZoneAllowedUse)
class ZoneAllowedUseAdmin(admin.ModelAdmin):
    """
    Admin interface for Zone Allowed Uses.
    """
    list_display = [
        'zone_type',
        'project_type',
        'is_primary_use',
        'is_conditional',
        'max_density',
        'max_height'
    ]
    list_filter = [
        'zone_type',
        'is_primary_use',
        'is_conditional'
    ]
    search_fields = [
        'zone_type',
        'project_type__name',
        'project_type__code',
        'conditions'
    ]
    fieldsets = (
        ('Zone and Project Type', {
            'fields': ('zone_type', 'project_type')
        }),
        ('Permissions', {
            'fields': ('is_primary_use', 'is_conditional', 'conditions')
        }),
        ('Restrictions', {
            'fields': ('max_density', 'max_height')
        }),
    )
    list_per_page = 25
    ordering = ['zone_type', 'project_type__name']

@admin.register(ZoneRecommendation)
class ZoneRecommendationAdmin(admin.ModelAdmin):
    """
    Admin interface for Zone Recommendations.
    """
    list_display = [
        'project',
        'recommended_zone',
        'overall_score',
        'rank',
        'is_selected',
        'created_at'
    ]
    list_filter = [
        'recommended_zone',
        'is_selected',
        'created_at'
    ]
    search_fields = [
        'project__name',
        'project__prn',
        'recommended_zone',
        'reasoning'
    ]
    readonly_fields = ['created_at']
    fieldsets = (
        ('Project and Zone', {
            'fields': ('project', 'recommended_zone', 'rank', 'is_selected')
        }),
        ('Scores', {
            'fields': (
                'overall_score',
                'zoning_compliance_score',
                'land_availability_score',
                'accessibility_score',
                'community_impact_score',
                'infrastructure_score'
            )
        }),
        ('Analysis', {
            'fields': ('reasoning', 'advantages', 'constraints')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )
    list_per_page = 25
    ordering = ['project', 'rank'] 