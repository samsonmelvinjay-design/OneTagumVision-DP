from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal, InvalidOperation
from projeng.models import Project as ProjengProject
from .models import Project


def _normalize_project_cost(value):
    """Return a Decimal-compatible value for ProjEng project_cost."""
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip().replace(',', '')
        if not cleaned:
            return None
        try:
            return Decimal(cleaned)
        except (InvalidOperation, ValueError):
            return None
    return value


@receiver(post_save, sender=Project)
def sync_monitoring_to_projeng(sender, instance, **kwargs):
    projeng_project, created = ProjengProject.objects.get_or_create(
        prn=instance.prn,
        defaults={
            'name': instance.name,
            'description': instance.description,
            'barangay': instance.barangay,
            'project_cost': _normalize_project_cost(instance.project_cost),
            'source_of_funds': instance.source_of_funds,
            'status': instance.status,
            'start_date': instance.start_date,
            'end_date': instance.end_date,
            'day_count_type': instance.day_count_type,
        }
    )
    if not created:
        projeng_project.name = instance.name
        projeng_project.description = instance.description
        projeng_project.barangay = instance.barangay
        projeng_project.project_cost = _normalize_project_cost(instance.project_cost)
        projeng_project.source_of_funds = instance.source_of_funds
        projeng_project.status = instance.status
        projeng_project.start_date = instance.start_date
        projeng_project.end_date = instance.end_date
        projeng_project.day_count_type = instance.day_count_type
        projeng_project.save() 
