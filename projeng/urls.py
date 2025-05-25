from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='projeng_dashboard'),
    path('my-projects/', views.my_projects_view, name='projeng_my_projects'),
    path('map/', views.projeng_map_view, name='projeng_map'),
    path('upload-docs/', views.upload_docs_view, name='projeng_upload_docs'),
    path('my-reports/', views.my_reports_view, name='projeng_my_reports'),
    
    # Report Export URLs
    path('my-reports/export/csv/', views.export_reports_csv, name='projeng_export_reports_csv'),
    path('my-reports/export/excel/', views.export_reports_excel, name='projeng_export_reports_excel'),
    path('my-reports/export/pdf/', views.export_reports_pdf, name='projeng_export_reports_pdf'),

    path('projects/<int:pk>/detail/', views.project_detail_view, name='projeng_project_detail'),
    path('projects/<int:pk>/update_status/', views.update_project_status, name='projeng_update_project_status'),
    path('save-layer/', views.save_layer, name='save_layer'),
    path('api/engineers/', views.get_project_engineers, name='get_project_engineers'),
    
    # New URLs for analytics and reporting
    path('projects/<int:pk>/analytics/', views.project_analytics, name='projeng_project_analytics'),
    path('projects/<int:pk>/export-report/', views.export_project_report, name='projeng_export_project_report'),
    path('projects/<int:pk>/add-progress/', views.add_progress_update, name='projeng_add_progress_update'),
    path('projects/<int:pk>/add-cost/', views.add_cost_entry, name='projeng_add_cost_entry'),
    path('analytics/', views.analytics_overview, name='projeng_analytics_overview'),
    path('analytics/overview-data/', views.analytics_overview_data, name='projeng_analytics_overview_data'),
    path('projects/<int:engineer_id>/', views.engineer_projects_api, name='engineer_projects_api'),
    
    # URL for project photo uploads
    path('projects/<int:pk>/upload-photo/', views.upload_project_photo, name='projeng_upload_project_photo'),
    # URL for project document uploads
    path('projects/<int:pk>/upload-document/', views.upload_project_document, name='projeng_upload_project_document'),

    path('map/api/projects/', views.map_projects_api, name='projeng_map_projects_api'),

    path('dashboard/api/card-data/', views.dashboard_card_data_api, name='projeng_dashboard_card_data_api'),
    
    # Add project delete API endpoint
    path('projects/<int:pk>/api/delete/', views.project_delete_api, name='project_delete_api'),
] 