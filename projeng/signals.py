from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Project
from monitoring.models import Project as MonitoringProject

@receiver(post_save, sender=Project)
def sync_projeng_to_monitoring(sender, instance, **kwargs):
    print(f"SIGNAL: sync_projeng_to_monitoring called for Project id={instance.id}, prn={instance.prn}")
    try:
        if instance.prn:
            monitoring_project, created = MonitoringProject.objects.get_or_create(
                prn=instance.prn,
                defaults={
                    'name': instance.name,
                    'description': instance.description,
                    'barangay': instance.barangay,
                    'project_cost': str(instance.project_cost) if instance.project_cost is not None else '',
                    'source_of_funds': instance.source_of_funds,
                    'status': instance.status,
                    'latitude': instance.latitude or 0,
                    'longitude': instance.longitude or 0,
                    'start_date': instance.start_date,
                    'end_date': instance.end_date,
                    'image': instance.image,
                }
            )
            if not created:
                monitoring_project.name = instance.name
                monitoring_project.description = instance.description
                monitoring_project.barangay = instance.barangay
                monitoring_project.project_cost = str(instance.project_cost) if instance.project_cost is not None else ''
                monitoring_project.source_of_funds = instance.source_of_funds
                monitoring_project.status = instance.status
                monitoring_project.latitude = instance.latitude or 0
                monitoring_project.longitude = instance.longitude or 0
                monitoring_project.start_date = instance.start_date
                monitoring_project.end_date = instance.end_date
                if instance.image:
                    monitoring_project.image = instance.image
                monitoring_project.save()
            # Sync assigned engineers
            if hasattr(monitoring_project, 'assigned_engineers'):
                monitoring_project.assigned_engineers.set(instance.assigned_engineers.all())
            else:
                print('Warning: MonitoringProject has no assigned_engineers field')
        print(f"SIGNAL: sync_projeng_to_monitoring completed for Project id={instance.id}, prn={instance.prn}")
    except Exception as e:
        print(f"SIGNAL ERROR: sync_projeng_to_monitoring failed for Project id={instance.id}, prn={instance.prn}: {e}") 