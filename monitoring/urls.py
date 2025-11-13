from django.urls import path
from . import views
from monitoring.views.finance_manager import finance_dashboard, finance_projects, finance_cost_management, finance_notifications, finance_project_detail

urlpatterns = [
    path('', views.dashboard, name='dashboard'),  # Changed: /dashboard/ now goes directly to dashboard
    path('home/', views.home, name='home'),  # Moved home to /dashboard/home/
    path('projects/', views.project_list, name='project_list'),
    path('map/', views.map_view, name='map_view'),
    path('reports/', views.reports, name='reports'),
    path('reports/export/csv/', views.export_reports_csv, name='export_reports_csv'),
    path('reports/export/excel/', views.export_reports_excel, name='export_reports_excel'),
    path('reports/export/pdf/', views.export_reports_pdf, name='export_reports_pdf'),
    path('reports/budget/', views.budget_reports, name='budget_reports'),
    path('reports/budget/export/csv/', views.export_budget_reports_csv, name='export_budget_reports_csv'),
    path('reports/budget/export/excel/', views.export_budget_reports_excel, name='export_budget_reports_excel'),
    path('reports/budget/export/pdf/', views.export_budget_reports_pdf, name='export_budget_reports_pdf'),
    path('projects/<int:pk>/api/update/', views.project_update_api, name='project_update_api'),
    
    path('projects/<int:pk>/api/delete/', views.project_delete_api, name='project_delete_api'),
    path('delayed/', views.delayed_projects, name='delayed_projects'),
    path('analytics/project-engineer/<int:pk>/', views.project_engineer_analytics, name='project_engineer_analytics'),
    path('analytics/head-engineer/', views.head_engineer_analytics, name='head_engineer_analytics'),
    path('notifications/', views.head_engineer_notifications, name='head_engineer_notifications'),
    path('projects/<int:pk>/', views.project_detail, name='project_detail'),
    path('projects/<int:project_id>/forward-budget-alert/', views.forward_budget_alert_to_finance_view, name='forward_budget_alert'),
    path('monitoring/projects/<int:pk>/detail/', views.head_engineer_project_detail, name='monitoring_project_detail'),
    path('dashboard/api/card-data/', views.head_dashboard_card_data_api, name='head_dashboard_card_data_api'),
    path('dashboard/budget-utilization-data/', views.dashboard_budget_utilization_data, name='dashboard_budget_utilization_data'),
    path('dashboard/cost-breakdown-data/', views.dashboard_cost_breakdown_data, name='dashboard_cost_breakdown_data'),
    path('dashboard/monthly-spending-data/', views.dashboard_monthly_spending_data, name='dashboard_monthly_spending_data'),
    path('api/barangay-geojson/', views.barangay_geojson_view, name='barangay_geojson'),
    path('projects/<int:pk>/export-timeline-pdf/', views.export_project_timeline_pdf, name='export_project_timeline_pdf'),
    path('projects/<int:pk>/export-comprehensive-pdf/', views.export_project_comprehensive_pdf, name='export_project_comprehensive_pdf'),
    path('projects/<int:pk>/export-comprehensive-excel/', views.export_project_comprehensive_excel, name='export_project_comprehensive_excel'),
    path('projects/<int:pk>/export-comprehensive-csv/', views.export_project_comprehensive_csv, name='export_project_comprehensive_csv'),
    path('finance/dashboard/', views.finance_dashboard, name='finance_dashboard'),
    path('finance/projects/', views.finance_projects, name='finance_projects'),
    path('finance/cost-management/', views.finance_cost_management, name='finance_cost_management'),
    path('finance/notifications/', views.finance_notifications, name='finance_notifications'),
    path('finance/project/<int:project_id>/', finance_project_detail, name='finance_project_detail'),
    
    # Engineer Management URLs
    path('engineers/', views.engineer_list, name='engineer_list'),
    path('engineers/create/', views.engineer_create, name='engineer_create'),
    path('engineers/<int:engineer_id>/', views.engineer_detail, name='engineer_detail'),
    path('engineers/<int:engineer_id>/edit/', views.engineer_edit, name='engineer_edit'),
    path('engineers/<int:engineer_id>/deactivate/', views.engineer_deactivate, name='engineer_deactivate'),
    path('engineers/<int:engineer_id>/activate/', views.engineer_activate, name='engineer_activate'),
] 