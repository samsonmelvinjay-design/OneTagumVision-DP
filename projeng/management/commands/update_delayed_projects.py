from django.core.management.base import BaseCommand
from projeng.models import Project, ProjectProgress
from django.utils import timezone

class Command(BaseCommand):
    help = 'Update status of all overdue projects to delayed (does not touch other statuses)'

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        updated = 0
        for project in Project.objects.all():
            latest_progress = ProjectProgress.objects.filter(project=project).order_by('-date').first()
            progress = int(latest_progress.percentage_complete) if latest_progress else 0
            if progress < 99 and project.end_date and project.end_date < today:
                if project.status != 'delayed':
                    project.status = 'delayed'
                    project.save(update_fields=['status'])
                    updated += 1
        self.stdout.write(self.style.SUCCESS(f'Updated {updated} projects to delayed.')) 