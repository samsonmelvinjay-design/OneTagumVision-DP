from django.core.management.base import BaseCommand
from projeng.models import Project, ProjectProgress, ProjectCost
from django.db.models import Q, Count, Sum, Max, Avg
import json
import csv
import os
from django.conf import settings
from datetime import datetime
from collections import defaultdict

def get_zone_display_name(zone_type):
    """Helper function to get display name for zone type"""
    zone_names = {
        'R-1': 'Low Density Residential',
        'R-2': 'Medium Density Residential',
        'R-3': 'High Density Residential',
        'SHZ': 'Socialized Housing',
        'C-1': 'Major Commercial',
        'C-2': 'Minor Commercial',
        'I-1': 'Heavy Industrial',
        'I-2': 'Light/Medium Industrial',
        'AGRO': 'Agro-Industrial',
        'INS-1': 'Institutional',
        'PARKS': 'Parks & Open Spaces',
        'AGRICULTURAL': 'Agricultural',
        'ECO-TOURISM': 'Eco-tourism',
        'SPECIAL': 'Special Use',
    }
    return zone_names.get(zone_type, zone_type)


class Command(BaseCommand):
    help = 'Export ALL analytics data for Google Colab testing (comprehensive export)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            type=str,
            default='.',
            help='Directory to save exported files (default: current directory)'
        )
    
    def handle(self, *args, **options):
        output_dir = options['output_dir']
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('EXPORTING ALL ANALYTICS DATA'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        # Get all projects
        projects = Project.objects.all().select_related('project_type', 'created_by').prefetch_related('assigned_engineers')
        total_projects = projects.count()
        
        self.stdout.write(f'\nFound {total_projects} total projects')
        
        if total_projects == 0:
            self.stdout.write(self.style.WARNING('No projects found!'))
            return
        
        # ========================================================================
        # EXPORT 1: Complete Project Data (CSV) - For all analytics
        # ========================================================================
        self.stdout.write(f'\n📊 Exporting complete project data...')
        csv_filename = os.path.join(output_dir, f'all_projects_data_{timestamp}.csv')
        
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'id', 'name', 'prn', 'description', 'barangay', 
                'zone_type', 'zone_validated', 'status', 
                'project_cost', 'source_of_funds',
                'latitude', 'longitude',
                'start_date', 'end_date', 'created_at',
                'project_type_name', 'created_by_username',
                'assigned_engineers_count', 'assigned_engineers_names',
                'latest_progress', 'total_spent', 'budget_remaining'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for project in projects:
                # Get latest progress
                latest_progress = ProjectProgress.objects.filter(project=project).order_by('-date').first()
                latest_progress_pct = latest_progress.percentage_complete if latest_progress else 0
                
                # Get total spent
                total_spent = ProjectCost.objects.filter(project=project).aggregate(total=Sum('amount'))['total'] or 0
                
                # Get assigned engineers
                assigned_engineers = project.assigned_engineers.all()
                engineers_names = ', '.join([e.username for e in assigned_engineers])
                
                writer.writerow({
                    'id': project.id,
                    'name': project.name,
                    'prn': project.prn or '',
                    'description': (project.description or '')[:500],  # Limit description length
                    'barangay': project.barangay or '',
                    'zone_type': project.zone_type or '',
                    'zone_validated': project.zone_validated,
                    'status': project.status or '',
                    'project_cost': float(project.project_cost) if project.project_cost else 0.0,
                    'source_of_funds': project.source_of_funds or '',
                    'latitude': project.latitude or '',
                    'longitude': project.longitude or '',
                    'start_date': project.start_date.isoformat() if project.start_date else '',
                    'end_date': project.end_date.isoformat() if project.end_date else '',
                    'created_at': project.created_at.isoformat() if project.created_at else '',
                    'project_type_name': project.project_type.name if project.project_type else '',
                    'created_by_username': project.created_by.username if project.created_by else '',
                    'assigned_engineers_count': assigned_engineers.count(),
                    'assigned_engineers_names': engineers_names,
                    'latest_progress': latest_progress_pct,
                    'total_spent': float(total_spent),
                    'budget_remaining': float(project.project_cost) - float(total_spent) if project.project_cost else 0.0,
                })
        
        self.stdout.write(self.style.SUCCESS(f'✅ CSV exported: {csv_filename}'))
        
        # ========================================================================
        # EXPORT 2: Progress Data (CSV)
        # ========================================================================
        self.stdout.write(f'\n📈 Exporting progress data...')
        progress_csv = os.path.join(output_dir, f'progress_data_{timestamp}.csv')
        
        progress_updates = ProjectProgress.objects.select_related('project', 'created_by').all()
        
        with open(progress_csv, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['project_id', 'project_name', 'date', 'percentage_complete', 
                         'description', 'created_by', 'created_at']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for progress in progress_updates:
                writer.writerow({
                    'project_id': progress.project.id,
                    'project_name': progress.project.name,
                    'date': progress.date.isoformat(),
                    'percentage_complete': progress.percentage_complete,
                    'description': (progress.description or '')[:500],
                    'created_by': progress.created_by.username if progress.created_by else '',
                    'created_at': progress.created_at.isoformat(),
                })
        
        self.stdout.write(self.style.SUCCESS(f'✅ Progress CSV exported: {progress_csv}'))
        
        # ========================================================================
        # EXPORT 3: Cost Data (CSV)
        # ========================================================================
        self.stdout.write(f'\n💰 Exporting cost data...')
        cost_csv = os.path.join(output_dir, f'cost_data_{timestamp}.csv')
        
        costs = ProjectCost.objects.select_related('project', 'created_by').all()
        
        with open(cost_csv, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['project_id', 'project_name', 'date', 'cost_type', 
                         'amount', 'description', 'created_by', 'created_at']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for cost in costs:
                writer.writerow({
                    'project_id': cost.project.id,
                    'project_name': cost.project.name,
                    'date': cost.date.isoformat(),
                    'cost_type': cost.get_cost_type_display(),
                    'amount': float(cost.amount),
                    'description': (cost.description or '')[:500],
                    'created_by': cost.created_by.username if cost.created_by else '',
                    'created_at': cost.created_at.isoformat(),
                })
        
        self.stdout.write(self.style.SUCCESS(f'✅ Cost CSV exported: {cost_csv}'))
        
        # ========================================================================
        # EXPORT 4: Analytics Summary (JSON) - All analytics categories
        # ========================================================================
        self.stdout.write(f'\n📊 Calculating analytics summaries...')
        json_filename = os.path.join(output_dir, f'all_analytics_{timestamp}.json')
        
        analytics_data = {
            'export_date': datetime.now().isoformat(),
            'total_projects': total_projects,
            
            # 1. ZONING ANALYTICS
            'zoning_analytics': self._calculate_zoning_analytics(projects),
            
            # 2. CLUSTERING ANALYTICS (Barangay-based)
            'clustering_analytics': self._calculate_clustering_analytics(projects),
            
            # 3. SUITABILITY ANALYTICS (if available)
            'suitability_analytics': self._calculate_suitability_analytics(projects),
            
            # 4. FINANCIAL ANALYTICS
            'financial_analytics': self._calculate_financial_analytics(projects),
            
            # 5. STATUS ANALYTICS
            'status_analytics': self._calculate_status_analytics(projects),
            
            # 6. TIMELINE ANALYTICS
            'timeline_analytics': self._calculate_timeline_analytics(projects),
            
            # 7. PROGRESS ANALYTICS
            'progress_analytics': self._calculate_progress_analytics(projects),
            
            # 8. INTEGRATED ANALYTICS
            'integrated_analytics': self._calculate_integrated_analytics(projects),
        }
        
        with open(json_filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(analytics_data, jsonfile, indent=2, ensure_ascii=False, default=str)
        
        self.stdout.write(self.style.SUCCESS(f'✅ Analytics JSON exported: {json_filename}'))
        
        # ========================================================================
        # EXPORT 5: Summary Report (TXT)
        # ========================================================================
        summary_filename = os.path.join(output_dir, f'analytics_summary_{timestamp}.txt')
        self._write_summary_report(summary_filename, analytics_data, timestamp)
        
        self.stdout.write(self.style.SUCCESS(f'✅ Summary report exported: {summary_filename}'))
        
        # ========================================================================
        # COMPLETION
        # ========================================================================
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 70))
        self.stdout.write(self.style.SUCCESS('EXPORT COMPLETE!'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'\n📁 Files saved in: {os.path.abspath(output_dir)}')
        self.stdout.write(f'\n📄 Exported Files:')
        self.stdout.write(f'   1. {os.path.basename(csv_filename)} - Complete project data')
        self.stdout.write(f'   2. {os.path.basename(progress_csv)} - Progress updates')
        self.stdout.write(f'   3. {os.path.basename(cost_csv)} - Cost entries')
        self.stdout.write(f'   4. {os.path.basename(json_filename)} - All analytics (JSON)')
        self.stdout.write(f'   5. {os.path.basename(summary_filename)} - Summary report')
        self.stdout.write(f'\n🚀 Next steps:')
        self.stdout.write(f'   1. Upload all CSV files to Google Colab')
        self.stdout.write(f'   2. Use the JSON file to verify results')
        self.stdout.write(f'   3. Run the comprehensive analytics notebook!')
    
    def _calculate_zoning_analytics(self, projects):
        """Calculate zoning analytics"""
        projects_with_zones = projects.filter(zone_type__isnull=False).exclude(zone_type='')
        
        zone_stats = projects_with_zones.values('zone_type').annotate(
            total_projects=Count('id'),
            completed=Count('id', filter=Q(status='completed')),
            in_progress=Count('id', filter=Q(status__in=['in_progress', 'ongoing'])),
            planned=Count('id', filter=Q(status__in=['planned', 'pending'])),
            delayed=Count('id', filter=Q(status='delayed')),
            total_cost=Sum('project_cost')
        ).order_by('zone_type')
        
        zones = []
        for stat in zone_stats:
            zones.append({
                'zone_type': stat['zone_type'],
                'display_name': get_zone_display_name(stat['zone_type']),
                'total_projects': stat['total_projects'],
                'completed': stat['completed'],
                'in_progress': stat['in_progress'],
                'planned': stat['planned'],
                'delayed': stat.get('delayed', 0),
                'total_cost': float(stat['total_cost'] or 0)
            })
        
        return {
            'total_projects_with_zones': projects_with_zones.count(),
            'zones': zones,
            'zone_validation_rate': (projects_with_zones.filter(zone_validated=True).count() / projects_with_zones.count() * 100) if projects_with_zones.count() > 0 else 0
        }
    
    def _calculate_clustering_analytics(self, projects):
        """Calculate clustering analytics (barangay-based)"""
        barangay_stats = projects.values('barangay').annotate(
            total_projects=Count('id'),
            avg_latitude=Avg('latitude'),
            avg_longitude=Avg('longitude'),
        ).order_by('barangay')
        
        barangays = []
        for stat in barangay_stats:
            if stat['barangay']:  # Only include projects with barangay
                barangays.append({
                    'barangay': stat['barangay'],
                    'total_projects': stat['total_projects'],
                    'avg_latitude': float(stat['avg_latitude'] or 0),
                    'avg_longitude': float(stat['avg_longitude'] or 0),
                })
        
        return {
            'total_clusters': len(barangays),
            'clusters': barangays
        }
    
    def _calculate_suitability_analytics(self, projects):
        """Calculate suitability analytics (placeholder - add if LandSuitabilityAnalysis exists)"""
        # Try to import and calculate if model exists
        try:
            from projeng.models import LandSuitabilityAnalysis
            suitability_analyses = LandSuitabilityAnalysis.objects.select_related('project').all()
            
            suitability_distribution = defaultdict(int)
            for analysis in suitability_analyses:
                score = analysis.overall_score or 0
                if score >= 80:
                    suitability_distribution['highly_suitable'] += 1
                elif score >= 60:
                    suitability_distribution['suitable'] += 1
                elif score >= 40:
                    suitability_distribution['moderately_suitable'] += 1
                else:
                    suitability_distribution['not_suitable'] += 1
            
            return {
                'total_analyses': suitability_analyses.count(),
                'distribution': dict(suitability_distribution),
                'avg_score': float(suitability_analyses.aggregate(avg=Avg('overall_score'))['avg'] or 0)
            }
        except:
            return {
                'total_analyses': 0,
                'distribution': {},
                'avg_score': 0,
                'note': 'Suitability analysis model not found'
            }
    
    def _calculate_financial_analytics(self, projects):
        """Calculate financial analytics"""
        total_budget = projects.aggregate(total=Sum('project_cost'))['total'] or 0
        
        # Calculate total spent
        all_costs = ProjectCost.objects.all()
        total_spent = all_costs.aggregate(total=Sum('amount'))['total'] or 0
        
        # Cost by type
        cost_by_type = defaultdict(float)
        for cost in all_costs:
            cost_by_type[cost.get_cost_type_display()] += float(cost.amount)
        
        # Budget utilization per project
        project_financials = []
        for project in projects:
            spent = ProjectCost.objects.filter(project=project).aggregate(total=Sum('amount'))['total'] or 0
            budget = float(project.project_cost) if project.project_cost else 0
            utilization = (float(spent) / budget * 100) if budget > 0 else 0
            
            project_financials.append({
                'project_id': project.id,
                'project_name': project.name,
                'budget': budget,
                'spent': float(spent),
                'remaining': budget - float(spent),
                'utilization_percentage': utilization
            })
        
        return {
            'total_budget': float(total_budget),
            'total_spent': float(total_spent),
            'remaining_budget': float(total_budget) - float(total_spent),
            'utilization_percentage': (float(total_spent) / float(total_budget) * 100) if total_budget > 0 else 0,
            'cost_by_type': dict(cost_by_type),
            'projects': project_financials[:10]  # Top 10 for summary
        }
    
    def _calculate_status_analytics(self, projects):
        """Calculate status analytics"""
        status_counts = projects.values('status').annotate(count=Count('id'))
        
        status_distribution = {}
        for stat in status_counts:
            status_distribution[stat['status']] = stat['count']
        
        return {
            'distribution': status_distribution,
            'total': projects.count()
        }
    
    def _calculate_timeline_analytics(self, projects):
        """Calculate timeline analytics"""
        from django.utils import timezone
        today = timezone.now().date()
        
        projects_with_dates = projects.filter(start_date__isnull=False, end_date__isnull=False)
        
        timeline_stats = {
            'total_with_dates': projects_with_dates.count(),
            'on_time': 0,
            'delayed': 0,
            'upcoming': 0,
            'avg_duration_days': 0
        }
        
        durations = []
        for project in projects_with_dates:
            if project.end_date:
                if project.end_date < today:
                    # Check if completed or delayed
                    latest_progress = ProjectProgress.objects.filter(project=project).order_by('-date').first()
                    if latest_progress and latest_progress.percentage_complete >= 99:
                        timeline_stats['on_time'] += 1
                    else:
                        timeline_stats['delayed'] += 1
                else:
                    timeline_stats['upcoming'] += 1
                
                if project.start_date:
                    duration = (project.end_date - project.start_date).days
                    durations.append(duration)
        
        if durations:
            timeline_stats['avg_duration_days'] = sum(durations) / len(durations)
        
        return timeline_stats
    
    def _calculate_progress_analytics(self, projects):
        """Calculate progress analytics"""
        progress_data = []
        
        for project in projects:
            latest_progress = ProjectProgress.objects.filter(project=project).order_by('-date').first()
            progress_count = ProjectProgress.objects.filter(project=project).count()
            
            progress_data.append({
                'project_id': project.id,
                'project_name': project.name,
                'latest_progress': latest_progress.percentage_complete if latest_progress else 0,
                'progress_updates_count': progress_count
            })
        
        avg_progress = sum(p['latest_progress'] for p in progress_data) / len(progress_data) if progress_data else 0
        total_progress_updates = ProjectProgress.objects.count()
        
        return {
            'avg_progress': avg_progress,
            'total_progress_updates': total_progress_updates,
            'projects': progress_data[:10]  # Top 10 for summary
        }
    
    def _calculate_integrated_analytics(self, projects):
        """Calculate integrated analytics (health scores, trends)"""
        # Simplified health score calculation
        # In real implementation, this would combine suitability, clustering, and zone compliance
        
        return {
            'total_projects': projects.count(),
            'note': 'Integrated analytics combine suitability, clustering, and zone compliance scores'
        }
    
    def _write_summary_report(self, filename, analytics_data, timestamp):
        """Write a human-readable summary report"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('=' * 70 + '\n')
            f.write('COMPREHENSIVE ANALYTICS EXPORT SUMMARY\n')
            f.write('=' * 70 + '\n\n')
            f.write(f'Export Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
            f.write(f'Total Projects: {analytics_data["total_projects"]}\n\n')
            
            # Zoning Analytics
            f.write('1. ZONING ANALYTICS\n')
            f.write('-' * 70 + '\n')
            zoning = analytics_data['zoning_analytics']
            f.write(f'Projects with zones: {zoning["total_projects_with_zones"]}\n')
            f.write(f'Zone validation rate: {zoning["zone_validation_rate"]:.1f}%\n')
            f.write(f'Zone distribution:\n')
            for zone in zoning['zones']:
                f.write(f'  {zone["zone_type"]:8} ({zone["display_name"]:30}): {zone["total_projects"]:3} projects\n')
            f.write('\n')
            
            # Clustering Analytics
            f.write('2. CLUSTERING ANALYTICS\n')
            f.write('-' * 70 + '\n')
            clustering = analytics_data['clustering_analytics']
            f.write(f'Total clusters (barangays): {clustering["total_clusters"]}\n')
            f.write(f'Top 5 barangays by project count:\n')
            sorted_clusters = sorted(clustering['clusters'], key=lambda x: x['total_projects'], reverse=True)[:5]
            for cluster in sorted_clusters:
                f.write(f'  {cluster["barangay"]:25}: {cluster["total_projects"]:3} projects\n')
            f.write('\n')
            
            # Financial Analytics
            f.write('3. FINANCIAL ANALYTICS\n')
            f.write('-' * 70 + '\n')
            financial = analytics_data['financial_analytics']
            f.write(f'Total Budget: ${financial["total_budget"]:,.2f}\n')
            f.write(f'Total Spent: ${financial["total_spent"]:,.2f}\n')
            f.write(f'Remaining: ${financial["remaining_budget"]:,.2f}\n')
            f.write(f'Utilization: {financial["utilization_percentage"]:.1f}%\n')
            f.write('\n')
            
            # Status Analytics
            f.write('4. STATUS ANALYTICS\n')
            f.write('-' * 70 + '\n')
            status = analytics_data['status_analytics']
            total = analytics_data['total_projects']
            for status_name, count in status['distribution'].items():
                percentage = (count / total * 100) if total > 0 else 0
                f.write(f'  {status_name:15}: {count:3} ({percentage:5.1f}%)\n')
            f.write('\n')
            
            # Progress Analytics
            f.write('5. PROGRESS ANALYTICS\n')
            f.write('-' * 70 + '\n')
            progress = analytics_data['progress_analytics']
            f.write(f'Average Progress: {progress["avg_progress"]:.1f}%\n')
            f.write(f'Total Progress Updates: {progress["total_progress_updates"]}\n')
            f.write('\n')
            
            # Timeline Analytics
            f.write('6. TIMELINE ANALYTICS\n')
            f.write('-' * 70 + '\n')
            timeline = analytics_data['timeline_analytics']
            f.write(f'Projects with dates: {timeline["total_with_dates"]}\n')
            f.write(f'On time: {timeline["on_time"]}\n')
            f.write(f'Delayed: {timeline["delayed"]}\n')
            f.write(f'Upcoming: {timeline["upcoming"]}\n')
            f.write(f'Average duration: {timeline["avg_duration_days"]:.1f} days\n')
            f.write('\n')
            
            f.write('=' * 70 + '\n')
            f.write('END OF SUMMARY\n')
            f.write('=' * 70 + '\n')

