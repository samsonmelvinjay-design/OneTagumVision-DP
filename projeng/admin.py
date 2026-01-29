from django.contrib import admin
from django.contrib.admin.exceptions import AlreadyRegistered
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import (
    Layer, Project, ProjectProgress, ProjectProgressEditHistory, ProjectCost, ProgressPhoto, 
    BarangayMetadata, ZoningZone, ProjectMilestone,
    ProjectType, ZoneAllowedUse, ZoneRecommendation,
    UserSpatialAssignment,
    BudgetRequest, BudgetRequestAttachment, BudgetRequestStatusHistory,
    LandSuitabilityAnalysis, SuitabilityCriteria,
    SourceOfFunds
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
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Progress Information', {
            'fields': ('project', 'date', 'percentage_complete', 'description', 'milestone', 'justification')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at', 'updated_by', 'is_edited', 'last_edit_reason')
        }),
    )

@admin.register(ProjectProgressEditHistory)
class ProjectProgressEditHistoryAdmin(admin.ModelAdmin):
    list_display = ('progress_update', 'edited_at', 'edited_by', 'from_percentage', 'to_percentage', 'added_photos_count')
    list_filter = ('edited_at',)
    search_fields = ('progress_update__project__name', 'edit_reason')
    readonly_fields = (
        'progress_update', 'edited_by', 'edited_at',
        'from_percentage', 'to_percentage',
        'from_description', 'to_description',
        'from_justification', 'to_justification',
        'edit_reason', 'added_photos_count',
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


@admin.register(BudgetRequest)
class BudgetRequestAdmin(admin.ModelAdmin):
    list_display = ('project', 'status', 'requested_amount', 'approved_amount', 'requested_by', 'reviewed_by', 'created_at')
    list_filter = ('status', 'created_at', 'reviewed_at')
    search_fields = ('project__name', 'project__prn', 'requested_by__username', 'reason', 'decision_notes')
    readonly_fields = ('created_at', 'updated_at', 'reviewed_at')
    list_select_related = ('project', 'requested_by', 'reviewed_by')


@admin.register(BudgetRequestAttachment)
class BudgetRequestAttachmentAdmin(admin.ModelAdmin):
    list_display = ('budget_request', 'uploaded_by', 'uploaded_at')
    list_filter = ('uploaded_at',)
    search_fields = ('budget_request__project__name', 'budget_request__project__prn')
    readonly_fields = ('uploaded_at',)
    list_select_related = ('budget_request', 'uploaded_by')


@admin.register(BudgetRequestStatusHistory)
class BudgetRequestStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('budget_request', 'from_status', 'to_status', 'action_by', 'created_at')
    list_filter = ('to_status', 'created_at')
    search_fields = ('budget_request__project__name', 'budget_request__project__prn', 'notes')
    readonly_fields = ('created_at',)
    list_select_related = ('budget_request', 'action_by')


@admin.register(SourceOfFunds)
class SourceOfFundsAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(SuitabilityCriteria)
class SuitabilityCriteriaAdmin(admin.ModelAdmin):
    list_display = ('name', 'project_type', 'is_active', 'created_at', 'updated_at')
    list_filter = ('project_type', 'is_active')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(LandSuitabilityAnalysis)
class LandSuitabilityAnalysisAdmin(admin.ModelAdmin):
    list_display = ('project', 'overall_score', 'suitability_category', 'analyzed_at', 'analysis_version')
    list_filter = ('suitability_category', 'analysis_version', 'analyzed_at')
    search_fields = ('project__name', 'project__prn', 'project__barangay')
    readonly_fields = ('analyzed_at', 'updated_at')
    list_select_related = ('project',)

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

@admin.register(UserSpatialAssignment)
class UserSpatialAssignmentAdmin(admin.ModelAdmin):
    """
    Admin interface for GEO-RBAC User Spatial Assignments.
    Head Engineers can assign users (engineers) to specific barangays.
    """
    list_display = [
        'user',
        'barangay',
        'is_active',
        'priority',
        'assigned_by',
        'assigned_at'
    ]
    list_filter = [
        'barangay',
        'is_active',
        'priority',
        'assigned_at'
    ]
    search_fields = [
        'user__username',
        'user__email',
        'user__first_name',
        'user__last_name',
        'barangay',
        'notes'
    ]
    readonly_fields = ['assigned_at']
    fieldsets = (
        ('Assignment', {
            'fields': ('user', 'barangay', 'is_active', 'priority')
        }),
        ('Metadata', {
            'fields': ('assigned_by', 'assigned_at', 'notes')
        }),
    )
    list_per_page = 25
    ordering = ['user', 'barangay']
    
    def save_model(self, request, obj, form, change):
        """Automatically set assigned_by to current user if not set"""
        if not obj.assigned_by:
            obj.assigned_by = request.user
        super().save_model(request, obj, form, change)

# Register ZoneRecommendation with safe duplicate check
try:
    admin.site.register(ZoneRecommendation, ZoneRecommendationAdmin)
except AlreadyRegistered:
    # Already registered, skip
    pass