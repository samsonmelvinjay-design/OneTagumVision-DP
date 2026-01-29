from django.urls import path
from . import views
from . import realtime

urlpatterns = [
    path('dashboard/', views.dashboard, name='projeng_dashboard'),
    path('my-projects/', views.my_projects_view, name='projeng_my_projects'),
    path('map/', views.projeng_map_view, name='projeng_map'),
    path('upload-docs/', views.upload_docs_view, name='projeng_upload_docs'),
    path('my-reports/', views.my_reports_view, name='projeng_my_reports'),
    path('notifications/', views.notifications_view, name='projeng_notifications'),
    
    # Report Export URLs
    path('my-reports/export/csv/', views.export_reports_csv, name='projeng_export_reports_csv'),
    path('my-reports/export/excel/', views.export_reports_excel, name='projeng_export_reports_excel'),
    path('my-reports/export/pdf/', views.export_reports_pdf, name='projeng_export_reports_pdf'),

    path('projects/<int:pk>/detail/', views.project_detail_view, name='projeng_project_detail'),
    path('projects/<int:pk>/update_status/', views.update_project_status, name='projeng_update_project_status'),
    path('save-layer/', views.save_layer, name='save_layer'),
    path('api/engineers/', views.get_project_engineers, name='get_project_engineers'),
    
    # New URLs for reporting
    path('projects/<int:pk>/analytics/', views.project_analytics, name='projeng_project_analytics'),
    path('projects/<int:pk>/export-report/', views.export_project_report, name='projeng_export_project_report'),
    path('projects/<int:pk>/add-progress/', views.add_progress_update, name='projeng_add_progress_update'),
    path('projects/<int:pk>/progress/<int:update_id>/edit/', views.edit_progress_update, name='projeng_edit_progress_update'),
    path('projects/<int:pk>/add-cost/', views.add_cost_entry, name='projeng_add_cost_entry'),
    path('projects/<int:project_id>/budget-request/', views.create_budget_request, name='projeng_create_budget_request'),
    path('projects/<int:project_id>/send-budget-alert/', views.send_budget_alert, name='send_budget_alert'),
    path('dashboard/progress-over-time-data/', views.dashboard_progress_over_time_data, name='projeng_dashboard_progress_over_time_data'),
    path('dashboard/budget-utilization-data/', views.dashboard_budget_utilization_data, name='projeng_dashboard_budget_utilization_data'),
    path('dashboard/cost-breakdown-data/', views.dashboard_cost_breakdown_data, name='projeng_dashboard_cost_breakdown_data'),
    path('dashboard/projects-by-barangay-data/', views.dashboard_projects_by_barangay_data, name='projeng_dashboard_projects_by_barangay_data'),
    path('projects/<int:engineer_id>/', views.engineer_projects_api, name='engineer_projects_api'),
    
    # URL for project photo uploads
    path('projects/<int:pk>/upload-photo/', views.upload_project_photo, name='projeng_upload_project_photo'),
    # URL for project document uploads
    path('projects/<int:pk>/upload-document/', views.upload_project_document, name='projeng_upload_project_document'),
    # URL for getting project documents list
    path('projects/<int:pk>/documents/', views.get_project_documents, name='projeng_get_project_documents'),

    path('map/api/projects/', views.map_projects_api, name='projeng_map_projects_api'),

    path('dashboard/api/card-data/', views.dashboard_card_data_api, name='projeng_dashboard_card_data_api'),
    
    # Add project delete API endpoint
    path('projects/<int:pk>/api/delete/', views.project_delete_api, name='project_delete_api'),
    
    # Real-time SSE endpoints
    path('api/realtime/notifications/', realtime.sse_notifications, name='realtime_notifications'),
    path('api/realtime/dashboard/', realtime.sse_dashboard_updates, name='realtime_dashboard'),
    path('api/realtime/projects/', realtime.sse_project_status, name='realtime_projects'),
    path('api/realtime/projects/<int:project_id>/', realtime.sse_project_status, name='realtime_project_detail'),
    path('api/realtime/status/', realtime.realtime_api_status, name='realtime_status'),
    
    # API endpoints
    path('api/get-project-from-notification/', views.get_project_from_notification_api, name='get_project_from_notification_api'),
    
    # Phase 2: Barangay Metadata and Zoning API endpoints
    path('api/barangay-metadata/', views.barangay_metadata_api, name='barangay_metadata_api'),
    path('api/barangay-zoning-stats/', views.barangay_zoning_stats_api, name='barangay_zoning_stats_api'),
    # Phase 5: Zone Data API endpoint for map visualization
    path('api/barangay-zone-data/', views.barangay_zone_data_api, name='barangay_zone_data_api'),
    # Zone Analytics API endpoint for dashboard charts
    path('api/zone-analytics/', views.zone_analytics_api, name='zone_analytics_api'),
    
    # Zone Compatibility Recommendation API endpoints
    path('api/zone-recommendation/', views.zone_recommendation_api, name='zone_recommendation_api'),
    path('api/zone-validation/', views.zone_validation_api, name='zone_validation_api'),
    path('api/project-types/', views.project_types_api, name='project_types_api'),
    path('api/projects/<int:project_id>/zone-recommendations/', views.project_zone_recommendations_api, name='project_zone_recommendations_api'),
    
    # Clustering Algorithm Comparison
    path('clustering-comparison/', views.clustering_comparison_view, name='clustering_comparison'),
] 