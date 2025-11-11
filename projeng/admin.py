from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import Layer, Project, ProjectProgress, ProjectCost, ProgressPhoto, BarangayMetadata
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
            'fields': ('barangay', 'latitude', 'longitude')
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

@admin.register(ProjectProgress)
class ProjectProgressAdmin(admin.ModelAdmin):
    list_display = ('project', 'date', 'percentage_complete', 'created_by', 'created_at')
    list_filter = ('date', 'created_at')
    search_fields = ('project__name', 'description')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Progress Information', {
            'fields': ('project', 'date', 'percentage_complete', 'description')
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