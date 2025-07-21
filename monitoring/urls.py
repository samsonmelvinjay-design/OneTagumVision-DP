from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('projects/', views.project_list, name='project_list'),
    path('map/', views.map_view, name='map_view'),
    path('reports/', views.reports, name='reports'),
    path('reports/budget/', views.budget_reports, name='budget_reports'),
    path('projects/<int:pk>/api/update/', views.project_update_api, name='project_update_api'),
    
    path('projects/<int:pk>/api/delete/', views.project_delete_api, name='project_delete_api'),
    path('delayed/', views.delayed_projects, name='delayed_projects'),
    path('analytics/project-engineer/<int:pk>/', views.project_engineer_analytics, name='project_engineer_analytics'),
    path('analytics/head-engineer/', views.head_engineer_analytics, name='head_engineer_analytics'),
    path('projects/<int:pk>/', views.project_detail, name='project_detail'),
    path('monitoring/projects/<int:pk>/detail/', views.head_engineer_project_detail, name='monitoring_project_detail'),
    path('dashboard/api/card-data/', views.head_dashboard_card_data_api, name='head_dashboard_card_data_api'),
    path('api/barangay-geojson/', views.barangay_geojson_view, name='barangay_geojson'),
] 