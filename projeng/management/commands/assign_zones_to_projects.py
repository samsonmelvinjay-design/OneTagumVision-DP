from django.core.management.base import BaseCommand
from projeng.models import Project
from django.db.models import Q

class Command(BaseCommand):
    help = 'Auto-detect and assign zone types to projects that don\'t have them'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be assigned without actually saving'
        )
        parser.add_argument(
            '--min-confidence',
            type=int,
            default=30,
            help='Minimum confidence score to assign zone (default: 30)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-assign zones even if projects already have zone_type'
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        min_confidence = options['min_confidence']
        force = options['force']
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('AUTO-ASSIGNING ZONE TYPES TO PROJECTS'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        # Get projects to process
        if force:
            projects = Project.objects.all()
            self.stdout.write(f'\n📋 Processing ALL projects (force mode)...')
        else:
            projects = Project.objects.filter(
                Q(zone_type__isnull=True) | Q(zone_type='')
            )
            self.stdout.write(f'\n📋 Processing projects WITHOUT zone types...')
        
        total_projects = projects.count()
        self.stdout.write(f'   Found {total_projects} projects to process\n')
        
        if total_projects == 0:
            self.stdout.write(self.style.WARNING('⚠ No projects to process!'))
            if not force:
                self.stdout.write(self.style.WARNING('   All projects already have zone types assigned.'))
                self.stdout.write(self.style.WARNING('   Use --force to re-assign zones to all projects.'))
            return
        
        # Process each project
        assigned_count = 0
        skipped_count = 0
        low_confidence_count = 0
        results = []
        
        for project in projects:
            try:
                # Auto-detect zone
                zone_type, confidence = project.detect_and_set_zone(save=False)
                
                if zone_type and confidence >= min_confidence:
                    results.append({
                        'project': project,
                        'zone_type': zone_type,
                        'confidence': confidence,
                        'assigned': True
                    })
                    assigned_count += 1
                    
                    if not dry_run:
                        project.save(update_fields=['zone_type', 'zone_validated'])
                elif zone_type and confidence < min_confidence:
                    results.append({
                        'project': project,
                        'zone_type': zone_type,
                        'confidence': confidence,
                        'assigned': False,
                        'reason': f'Low confidence ({confidence} < {min_confidence})'
                    })
                    low_confidence_count += 1
                else:
                    results.append({
                        'project': project,
                        'zone_type': None,
                        'confidence': 0,
                        'assigned': False,
                        'reason': 'No zone detected'
                    })
                    skipped_count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   Error processing project {project.id}: {str(e)}'))
                skipped_count += 1
        
        # Display results
        self.stdout.write(f'\n📊 RESULTS:')
        self.stdout.write(f'   ✅ Assigned: {assigned_count}')
        self.stdout.write(f'   ⚠️  Low Confidence: {low_confidence_count}')
        self.stdout.write(f'   ❌ Skipped: {skipped_count}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  DRY RUN MODE - No changes were saved'))
            self.stdout.write(self.style.WARNING('   Run without --dry-run to apply changes'))
        else:
            self.stdout.write(self.style.SUCCESS(f'\n✅ Successfully assigned zones to {assigned_count} projects'))
        
        # Show detailed results for assigned projects
        if assigned_count > 0:
            self.stdout.write(f'\n📋 Assigned Zones:')
            zone_summary = {}
            for result in results:
                if result['assigned']:
                    zone = result['zone_type']
                    if zone not in zone_summary:
                        zone_summary[zone] = []
                    zone_summary[zone].append(result)
            
            for zone_type, zone_results in sorted(zone_summary.items()):
                avg_confidence = sum(r['confidence'] for r in zone_results) / len(zone_results)
                self.stdout.write(f'   {zone_type:8}: {len(zone_results):3} projects (avg confidence: {avg_confidence:.1f}%)')
        
        # Show sample of assigned projects
        if assigned_count > 0 and assigned_count <= 20:
            self.stdout.write(f'\n📝 Sample Assignments:')
            for result in results[:10]:
                if result['assigned']:
                    self.stdout.write(f'   • {result["project"].name[:50]:50} → {result["zone_type"]:8} ({result["confidence"]:3}%)')
        elif assigned_count > 20:
            self.stdout.write(f'\n📝 First 10 Assignments:')
            count = 0
            for result in results:
                if result['assigned'] and count < 10:
                    self.stdout.write(f'   • {result["project"].name[:50]:50} → {result["zone_type"]:8} ({result["confidence"]:3}%)')
                    count += 1
        
        # Show low confidence projects
        if low_confidence_count > 0:
            self.stdout.write(f'\n⚠️  Low Confidence Projects (not assigned):')
            for result in results[:5]:
                if not result['assigned'] and result.get('reason', '').startswith('Low confidence'):
                    self.stdout.write(f'   • {result["project"].name[:50]:50} → {result["zone_type"]:8} ({result["confidence"]:3}%)')
            if low_confidence_count > 5:
                self.stdout.write(f'   ... and {low_confidence_count - 5} more')
        
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 70))
        self.stdout.write(self.style.SUCCESS('PROCESSING COMPLETE!'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        if not dry_run and assigned_count > 0:
            self.stdout.write(f'\n💡 Next step: Run "python manage.py export_zone_analytics" to export the data')



