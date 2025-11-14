"""
Management command to analyze land suitability for projects
Usage:
    python manage.py analyze_land_suitability --all --save
    python manage.py analyze_land_suitability --project-id 1 --save
    python manage.py analyze_land_suitability --barangay "Magugpo Poblacion" --save
"""

from django.core.management.base import BaseCommand
from django.db.models import Q
from projeng.models import Project, LandSuitabilityAnalysis
from projeng.land_suitability import LandSuitabilityAnalyzer


class Command(BaseCommand):
    help = 'Analyze land suitability for projects'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--project-id',
            type=int,
            help='Analyze specific project by ID',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Analyze all projects with location data',
        )
        parser.add_argument(
            '--barangay',
            type=str,
            help='Analyze all projects in a specific barangay',
        )
        parser.add_argument(
            '--save',
            action='store_true',
            help='Save results to database (default: display only)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-analyze projects that already have analysis',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output for each project',
        )
    
    def handle(self, *args, **options):
        analyzer = LandSuitabilityAnalyzer()
        
        # Determine which projects to analyze
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
                latitude__isnull=False,
                longitude__isnull=False
            )
            if not projects.exists():
                self.stdout.write(self.style.WARNING(f'No projects found in {options["barangay"]} with location data'))
                return
        elif options['all']:
            projects = Project.objects.filter(
                latitude__isnull=False,
                longitude__isnull=False,
                barangay__isnull=False
            ).exclude(barangay='')
        else:
            self.stdout.write(self.style.ERROR('Specify --project-id, --barangay, or --all'))
            self.stdout.write(self.style.WARNING('Use --save to save results to database'))
            return
        
        # Filter out projects that already have analysis (unless --force)
        if not options['force']:
            analyzed_project_ids = LandSuitabilityAnalysis.objects.values_list('project_id', flat=True)
            projects = projects.exclude(id__in=analyzed_project_ids)
        
        total_projects = projects.count()
        if total_projects == 0:
            self.stdout.write(self.style.WARNING('No projects to analyze'))
            if not options['force']:
                self.stdout.write(self.style.WARNING('Use --force to re-analyze existing projects'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'\nAnalyzing {total_projects} project(s)...\n'))
        
        # Statistics
        stats = {
            'analyzed': 0,
            'saved': 0,
            'errors': 0,
            'highly_suitable': 0,
            'suitable': 0,
            'moderate': 0,
            'marginal': 0,
            'not_suitable': 0,
        }
        
        # Analyze each project
        for idx, project in enumerate(projects, 1):
            try:
                if options['verbose']:
                    self.stdout.write(f'\n[{idx}/{total_projects}] Analyzing: {project.name} (ID: {project.id})')
                
                result = analyzer.analyze_project(project)
                stats['analyzed'] += 1
                
                # Count by category
                category = result['suitability_category']
                if category == 'highly_suitable':
                    stats['highly_suitable'] += 1
                elif category == 'suitable':
                    stats['suitable'] += 1
                elif category == 'moderately_suitable':
                    stats['moderate'] += 1
                elif category == 'marginally_suitable':
                    stats['marginal'] += 1
                elif category == 'not_suitable':
                    stats['not_suitable'] += 1
                
                if options['verbose']:
                    self.stdout.write(f'  Overall Score: {result["overall_score"]}/100')
                    self.stdout.write(f'  Category: {result["suitability_category"]}')
                    self.stdout.write(f'  Factor Scores:')
                    for factor, score in result['factor_scores'].items():
                        self.stdout.write(f'    - {factor.replace("_", " ").title()}: {score}/100')
                    
                    if any(result['risks'].values()):
                        self.stdout.write(f'  Risks:')
                        for risk, value in result['risks'].items():
                            if value:
                                self.stdout.write(f'    - {risk.replace("_", " ").title()}: Yes')
                
                if options['save']:
                    analyzer.save_analysis(project, result)
                    stats['saved'] += 1
                    if options['verbose']:
                        self.stdout.write(self.style.SUCCESS('  ✓ Saved to database'))
                else:
                    if options['verbose']:
                        self.stdout.write(self.style.WARNING('  (Not saved - use --save to save)'))
                
            except Exception as e:
                stats['errors'] += 1
                self.stdout.write(self.style.ERROR(f'  ✗ Error analyzing project {project.id}: {str(e)}'))
                if options['verbose']:
                    import traceback
                    self.stdout.write(traceback.format_exc())
        
        # Print summary
        self.stdout.write(self.style.SUCCESS(f'\n{"="*60}'))
        self.stdout.write(self.style.SUCCESS('Analysis Summary'))
        self.stdout.write(self.style.SUCCESS(f'{"="*60}'))
        self.stdout.write(f'Total Projects Analyzed: {stats["analyzed"]}')
        if options['save']:
            self.stdout.write(f'Projects Saved: {stats["saved"]}')
        self.stdout.write(f'Errors: {stats["errors"]}')
        self.stdout.write(f'\nSuitability Distribution:')
        self.stdout.write(f'  Highly Suitable (80-100): {stats["highly_suitable"]}')
        self.stdout.write(f'  Suitable (60-79): {stats["suitable"]}')
        self.stdout.write(f'  Moderately Suitable (40-59): {stats["moderate"]}')
        self.stdout.write(f'  Marginally Suitable (20-39): {stats["marginal"]}')
        self.stdout.write(f'  Not Suitable (0-19): {stats["not_suitable"]}')
        
        if not options['save']:
            self.stdout.write(self.style.WARNING('\n⚠️  Results were NOT saved. Use --save to save to database.'))

