from django.urls import path
from . import views
from monitoring.views.finance_manager import finance_dashboard, finance_projects, finance_cost_management, finance_notifications, finance_project_detail
from monitoring.views.budget_approval import approve_budget_request, reject_budget_request

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
    path('reports/budget/chart-data/', views.budget_reports_chart_data_api, name='budget_reports_chart_data_api'),
    path('reports/budget/export/csv/', views.export_budget_reports_csv, name='export_budget_reports_csv'),
    path('reports/budget/export/excel/', views.export_budget_reports_excel, name='export_budget_reports_excel'),
    path('reports/budget/export/pdf/', views.export_budget_reports_pdf, name='export_budget_reports_pdf'),
    path('projects/<int:pk>/api/get/', views.project_get_api, name='project_get_api'),
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
    path('dashboard/collab-analytics-data/', views.dashboard_collab_analytics_data, name='dashboard_collab_analytics_data'),
    path('dashboard/cost-breakdown-data/', views.dashboard_cost_breakdown_data, name='dashboard_cost_breakdown_data'),
    path('dashboard/monthly-spending-data/', views.dashboard_monthly_spending_data, name='dashboard_monthly_spending_data'),
    path('dashboard/projects-created-data/', views.dashboard_projects_created_data, name='dashboard_projects_created_data'),
    path('api/barangay-geojson/', views.barangay_geojson_view, name='barangay_geojson'),
    path('api/tagum-city-boundary-geojson/', views.tagum_city_boundary_geojson_view, name='tagum_city_boundary_geojson'),
    path('api/overall-project-metrics/', views.overall_project_metrics_api, name='overall_project_metrics_api'),
    path('api/barangay-ranking/', views.barangay_ranking_api, name='barangay_ranking_api'),
    path('api/barangay-equity-summary/', views.barangay_equity_summary_api, name='barangay_equity_summary_api'),
    path('projects/<int:pk>/export-timeline-pdf/', views.export_project_timeline_pdf, name='export_project_timeline_pdf'),
    path('projects/<int:pk>/export-comprehensive-pdf/', views.export_project_comprehensive_pdf, name='export_project_comprehensive_pdf'),
    path('projects/<int:pk>/export-comprehensive-excel/', views.export_project_comprehensive_excel, name='export_project_comprehensive_excel'),
    path('projects/<int:pk>/export-comprehensive-csv/', views.export_project_comprehensive_csv, name='export_project_comprehensive_csv'),

    # API: create new ProjectType from UI (modal "Add new type")
    path('api/project-types/create/', views.create_project_type_api, name='create_project_type_api'),
    # API: generate a PRN for new projects (auto-generated PRN UX)
    path('api/prn/generate/', views.generate_prn_api, name='generate_prn_api'),
    path('finance/dashboard/', finance_dashboard, name='finance_dashboard'),
    path('finance/projects/', finance_projects, name='finance_projects'),
    path('finance/cost-management/', finance_cost_management, name='finance_cost_management'),
    path('finance/notifications/', finance_notifications, name='finance_notifications'),
    path('finance/project/<int:project_id>/', finance_project_detail, name='finance_project_detail'),
    path('finance/project/<int:project_id>/approve-budget/', approve_budget_request, name='approve_budget_request'),
    path('finance/project/<int:project_id>/reject-budget/', reject_budget_request, name='reject_budget_request'),
    
    # Engineer Management URLs
    path('engineers/', views.engineer_list, name='engineer_list'),
    path('engineers/create/', views.engineer_create, name='engineer_create'),
    path('engineers/<int:engineer_id>/', views.engineer_detail, name='engineer_detail'),
    path('engineers/<int:engineer_id>/edit/', views.engineer_edit, name='engineer_edit'),
    path('engineers/<int:engineer_id>/deactivate/', views.engineer_deactivate, name='engineer_deactivate'),
    path('engineers/<int:engineer_id>/activate/', views.engineer_activate, name='engineer_activate'),
    path('engineers/<int:engineer_id>/delete/', views.engineer_delete, name='engineer_delete'),
] 