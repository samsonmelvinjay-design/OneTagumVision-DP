"""
Management command to recalculate suitability analysis for projects
Usage:
    python manage.py recalculate_suitability --all
    python manage.py recalculate_suitability --project-id 1
    python manage.py recalculate_suitability --barangay "Magugpo Poblacion"
"""

from django.core.management.base import BaseCommand
from projeng.models import Project, LandSuitabilityAnalysis
from projeng.land_suitability import LandSuitabilityAnalyzer


class Command(BaseCommand):
    help = 'Recalculate land suitability analysis for projects'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--project-id',
            type=int,
            help='Recalculate specific project by ID',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Recalculate all projects with existing analysis',
        )
        parser.add_argument(
            '--barangay',
            type=str,
            help='Recalculate all projects in a specific barangay',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output for each project',
        )
    
    def handle(self, *args, **options):
        analyzer = LandSuitabilityAnalyzer()
        
        # Determine which projects to recalculate
        if options['project_id']:
            try:
                project = Project.objects.get(pk=options['project_id'])
                projects = [project]
            except Project.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Project {options["project_id"]} not found'))
                return
        elif options['barangay']:
            projects = Project.objects.filter(
                barangay=options['barangay'],
                suitability_analysis__isnull=False
            )
            if not projects.exists():
                self.stdout.write(self.style.WARNING(f'No projects found in {options["barangay"]} with existing analysis'))
                return
        elif options['all']:
            projects = Project.objects.filter(
                suitability_analysis__isnull=False
            )
        else:
            self.stdout.write(self.style.ERROR('Specify --project-id, --barangay, or --all'))
            return
        
        total_projects = projects.count()
        if total_projects == 0:
            self.stdout.write(self.style.WARNING('No projects with existing analysis found'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'\nRecalculating suitability for {total_projects} project(s)...\n'))
        
        # Statistics
        stats = {
            'recalculated': 0,
            'errors': 0,
            'score_changes': 0,
            'category_changes': 0,
        }
        
        # Recalculate each project
        for idx, project in enumerate(projects, 1):
            try:
                if options['verbose']:
                    self.stdout.write(f'\n[{idx}/{total_projects}] Recalculating: {project.name} (ID: {project.id})')
                
                # Get old analysis
                old_analysis = project.suitability_analysis
                old_score = old_analysis.overall_score
                old_category = old_analysis.suitability_category
                
                # Perform new analysis
                result = analyzer.analyze_project(project)
                new_score = result['overall_score']
                new_category = result['suitability_category']
                
                # Save new analysis
                analyzer.save_analysis(project, result)
                stats['recalculated'] += 1
                
                # Check for changes
                score_changed = abs(old_score - new_score) > 0.1
                category_changed = old_category != new_category
                
                if score_changed:
                    stats['score_changes'] += 1
                if category_changed:
                    stats['category_changes'] += 1
                
                if options['verbose']:
                    if score_changed or category_changed:
                        self.stdout.write(f'  Old Score: {old_score:.1f}/100 ({old_category})')
                        self.stdout.write(f'  New Score: {new_score:.1f}/100 ({new_category})')
                        if category_changed:
                            self.stdout.write(self.style.WARNING(f'  ⚠️  Category changed!'))
                    else:
                        self.stdout.write(f'  Score: {new_score:.1f}/100 (unchanged)')
                    self.stdout.write(self.style.SUCCESS('  ✓ Recalculated and saved'))
                
            except Exception as e:
                stats['errors'] += 1
                self.stdout.write(self.style.ERROR(f'  ✗ Error recalculating project {project.id}: {str(e)}'))
                if options['verbose']:
                    import traceback
                    self.stdout.write(traceback.format_exc())
        
        # Print summary
        self.stdout.write(self.style.SUCCESS(f'\n{"="*60}'))
        self.stdout.write(self.style.SUCCESS('Recalculation Summary'))
        self.stdout.write(self.style.SUCCESS(f'{"="*60}'))
        self.stdout.write(f'Total Projects Recalculated: {stats["recalculated"]}')
        self.stdout.write(f'Score Changes: {stats["score_changes"]}')
        self.stdout.write(f'Category Changes: {stats["category_changes"]}')
        self.stdout.write(f'Errors: {stats["errors"]}')

