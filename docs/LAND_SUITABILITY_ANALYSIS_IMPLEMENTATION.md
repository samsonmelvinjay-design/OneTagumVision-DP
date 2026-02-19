# 🗺️ Land Suitability Analysis Implementation Plan
## For ONETAGUMVISION System

---

## 📋 Overview

This module evaluates land suitability for infrastructure projects using multi-criteria analysis, integrating with existing zoning, barangay metadata, and project data in ONETAGUMVISION.

---

## 🎯 Goals

1. **Evaluate project locations** for suitability based on multiple factors
2. **Provide suitability scores** (0-100) with detailed breakdowns
3. **Identify risks** and constraints for project sites
4. **Support decision-making** for project planning and approval
5. **Generate suitability reports** for stakeholders

---

## 📊 Available Data Sources

### ✅ What We Have:
- **Projects**: `latitude`, `longitude`, `barangay`, `zone_type`, `status`
- **BarangayMetadata**: `population`, `density`, `elevation_type`, `economic_class`, `barangay_class`, `special_features`
- **ZoningZone**: `zone_type`, `barangay`, `location_description`, `keywords`
- **Geographic data**: Elevation types (highland, plains, coastal)

---

## 🏗️ Implementation Plan

### **Phase 1: Database Schema Extensions** (Week 1)

#### 1.1 Create Land Suitability Model
**File:** `projeng/models.py` (additions)

```python
class LandSuitabilityAnalysis(models.Model):
    """Stores land suitability analysis results for projects"""
    
    project = models.OneToOneField(
        'Project',
        on_delete=models.CASCADE,
        related_name='suitability_analysis',
        help_text="Project being analyzed"
    )
    
    # Overall Suitability Score (0-100)
    overall_score = models.FloatField(
        help_text="Overall suitability score (0-100)"
    )
    
    # Suitability Category
    SUITABILITY_CHOICES = [
        ('highly_suitable', 'Highly Suitable (80-100)'),
        ('suitable', 'Suitable (60-79)'),
        ('moderately_suitable', 'Moderately Suitable (40-59)'),
        ('marginally_suitable', 'Marginally Suitable (20-39)'),
        ('not_suitable', 'Not Suitable (0-19)'),
    ]
    suitability_category = models.CharField(
        max_length=30,
        choices=SUITABILITY_CHOICES,
        help_text="Suitability category based on score"
    )
    
    # Factor Scores (0-100 each)
    zoning_compliance_score = models.FloatField(
        help_text="Zoning compliance score (0-100)"
    )
    flood_risk_score = models.FloatField(
        help_text="Flood risk assessment score (0-100, higher = less risk)"
    )
    infrastructure_access_score = models.FloatField(
        help_text="Infrastructure access score (0-100)"
    )
    elevation_suitability_score = models.FloatField(
        help_text="Elevation suitability score (0-100)"
    )
    economic_alignment_score = models.FloatField(
        help_text="Economic zone alignment score (0-100)"
    )
    population_density_score = models.FloatField(
        help_text="Population density appropriateness score (0-100)"
    )
    
    # Risk Factors
    has_flood_risk = models.BooleanField(default=False)
    has_slope_risk = models.BooleanField(default=False)
    has_zoning_conflict = models.BooleanField(default=False)
    has_infrastructure_gap = models.BooleanField(default=False)
    
    # Recommendations
    recommendations = models.JSONField(
        default=list,
        help_text="List of recommendations for improving suitability"
    )
    constraints = models.JSONField(
        default=list,
        help_text="List of constraints or limitations"
    )
    
    # Analysis Metadata
    analyzed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    analysis_version = models.CharField(
        max_length=20,
        default='1.0',
        help_text="Version of analysis algorithm used"
    )
    
    class Meta:
        verbose_name = "Land Suitability Analysis"
        verbose_name_plural = "Land Suitability Analyses"
        ordering = ['-analyzed_at']
    
    def __str__(self):
        return f"{self.project.name} - {self.get_suitability_category_display()} ({self.overall_score:.1f})"
    
    def get_score_color(self):
        """Get color class for suitability score"""
        if self.overall_score >= 80:
            return 'success'  # Green
        elif self.overall_score >= 60:
            return 'info'  # Blue
        elif self.overall_score >= 40:
            return 'warning'  # Yellow
        elif self.overall_score >= 20:
            return 'warning'  # Orange
        else:
            return 'danger'  # Red
```

#### 1.2 Create Suitability Criteria Model
**File:** `projeng/models.py` (additions)

```python
class SuitabilityCriteria(models.Model):
    """Configurable criteria and weights for suitability analysis"""
    
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Name of criteria configuration"
    )
    
    # Weights for each factor (must sum to 1.0)
    weight_zoning = models.FloatField(
        default=0.30,
        help_text="Weight for zoning compliance (0-1)"
    )
    weight_flood_risk = models.FloatField(
        default=0.25,
        help_text="Weight for flood risk (0-1)"
    )
    weight_infrastructure = models.FloatField(
        default=0.20,
        help_text="Weight for infrastructure access (0-1)"
    )
    weight_elevation = models.FloatField(
        default=0.15,
        help_text="Weight for elevation suitability (0-1)"
    )
    weight_economic = models.FloatField(
        default=0.05,
        help_text="Weight for economic alignment (0-1)"
    )
    weight_population = models.FloatField(
        default=0.05,
        help_text="Weight for population density (0-1)"
    )
    
    # Project Type Specific Settings
    PROJECT_TYPE_CHOICES = [
        ('all', 'All Project Types'),
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
        ('industrial', 'Industrial'),
        ('infrastructure', 'Infrastructure'),
        ('institutional', 'Institutional'),
    ]
    project_type = models.CharField(
        max_length=20,
        choices=PROJECT_TYPE_CHOICES,
        default='all',
        help_text="Project type this criteria applies to"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Suitability Criteria"
        verbose_name_plural = "Suitability Criteria"
    
    def __str__(self):
        return f"{self.name} ({self.get_project_type_display()})"
    
    def clean(self):
        """Validate that weights sum to approximately 1.0"""
        from django.core.exceptions import ValidationError
        total = (
            self.weight_zoning +
            self.weight_flood_risk +
            self.weight_infrastructure +
            self.weight_elevation +
            self.weight_economic +
            self.weight_population
        )
        if abs(total - 1.0) > 0.01:  # Allow small floating point errors
            raise ValidationError(f"Weights must sum to 1.0, currently sum to {total:.2f}")
```

#### 1.3 Migration
```bash
python manage.py makemigrations projeng
python manage.py migrate
```

---

### **Phase 2: Core Analysis Engine** (Week 2)

#### 2.1 Create Suitability Analysis Module
**File:** `projeng/land_suitability.py` (new file)

```python
"""
Land Suitability Analysis Engine for ONETAGUMVISION
Evaluates project locations using multi-criteria analysis
"""

from typing import Dict, List, Tuple, Optional
from django.db.models import Q
from .models import (
    Project,
    BarangayMetadata,
    ZoningZone,
    LandSuitabilityAnalysis,
    SuitabilityCriteria
)


class LandSuitabilityAnalyzer:
    """Main engine for land suitability analysis"""
    
    def __init__(self, criteria: Optional[SuitabilityCriteria] = None):
        """
        Initialize analyzer with criteria
        
        Args:
            criteria: SuitabilityCriteria instance, or None to use default
        """
        if criteria is None:
            criteria, _ = SuitabilityCriteria.objects.get_or_create(
                name='default',
                defaults={
                    'weight_zoning': 0.30,
                    'weight_flood_risk': 0.25,
                    'weight_infrastructure': 0.20,
                    'weight_elevation': 0.15,
                    'weight_economic': 0.05,
                    'weight_population': 0.05,
                }
            )
        self.criteria = criteria
    
    def analyze_project(self, project: Project) -> Dict:
        """
        Perform comprehensive suitability analysis for a project
        
        Args:
            project: Project instance to analyze
        
        Returns:
            Dict with scores, factors, recommendations, and constraints
        """
        # Get barangay metadata
        barangay_meta = self._get_barangay_metadata(project)
        
        # Calculate factor scores
        factor_scores = {
            'zoning_compliance': self._score_zoning_compliance(project, barangay_meta),
            'flood_risk': self._score_flood_risk(project, barangay_meta),
            'infrastructure_access': self._score_infrastructure_access(project, barangay_meta),
            'elevation_suitability': self._score_elevation(project, barangay_meta),
            'economic_alignment': self._score_economic_alignment(project, barangay_meta),
            'population_density': self._score_population_density(project, barangay_meta),
        }
        
        # Calculate weighted overall score
        overall_score = (
            factor_scores['zoning_compliance'] * self.criteria.weight_zoning +
            factor_scores['flood_risk'] * self.criteria.weight_flood_risk +
            factor_scores['infrastructure_access'] * self.criteria.weight_infrastructure +
            factor_scores['elevation_suitability'] * self.criteria.weight_elevation +
            factor_scores['economic_alignment'] * self.criteria.weight_economic +
            factor_scores['population_density'] * self.criteria.weight_population
        )
        
        # Determine suitability category
        suitability_category = self._categorize_score(overall_score)
        
        # Identify risks
        risks = self._identify_risks(factor_scores, barangay_meta)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            factor_scores, 
            overall_score, 
            project, 
            barangay_meta
        )
        
        # Identify constraints
        constraints = self._identify_constraints(factor_scores, barangay_meta)
        
        return {
            'overall_score': round(overall_score, 2),
            'suitability_category': suitability_category,
            'factor_scores': {k: round(v, 2) for k, v in factor_scores.items()},
            'risks': risks,
            'recommendations': recommendations,
            'constraints': constraints,
            'barangay_metadata': {
                'name': barangay_meta.name if barangay_meta else None,
                'elevation_type': barangay_meta.elevation_type if barangay_meta else None,
                'economic_class': barangay_meta.economic_class if barangay_meta else None,
            } if barangay_meta else None,
        }
    
    def _get_barangay_metadata(self, project: Project) -> Optional[BarangayMetadata]:
        """Get barangay metadata for project"""
        if not project.barangay:
            return None
        try:
            return BarangayMetadata.objects.get(name=project.barangay)
        except BarangayMetadata.DoesNotExist:
            return None
    
    def _score_zoning_compliance(self, project: Project, barangay_meta: Optional[BarangayMetadata]) -> float:
        """
        Score zoning compliance (0-100)
        Higher score = better compliance
        """
        if not project.zone_type:
            return 50.0  # Neutral if no zone type set
        
        # Check if project zone matches barangay zoning
        if barangay_meta:
            # Check for matching zones in barangay
            matching_zones = ZoningZone.objects.filter(
                barangay=project.barangay,
                zone_type=project.zone_type,
                is_active=True
            )
            if matching_zones.exists():
                return 100.0  # Perfect match
            else:
                # Check for compatible zones
                compatible = self._check_compatible_zones(project.zone_type, project.barangay)
                if compatible:
                    return 75.0  # Compatible but not exact
                else:
                    return 30.0  # Conflict
        else:
            # No barangay metadata, assume moderate compliance
            return 60.0
    
    def _check_compatible_zones(self, zone_type: str, barangay: str) -> bool:
        """Check if zone type is compatible with barangay zones"""
        # Define compatibility rules
        compatibility_map = {
            'R-1': ['R-2', 'R-3'],  # Low density compatible with medium/high
            'R-2': ['R-1', 'R-3'],
            'C-1': ['C-2'],  # Major commercial compatible with minor
            'I-2': ['I-1'],  # Light industrial compatible with heavy
        }
        
        compatible_zones = compatibility_map.get(zone_type, [])
        if not compatible_zones:
            return False
        
        existing_zones = ZoningZone.objects.filter(
            barangay=barangay,
            zone_type__in=compatible_zones,
            is_active=True
        )
        return existing_zones.exists()
    
    def _score_flood_risk(self, project: Project, barangay_meta: Optional[BarangayMetadata]) -> float:
        """
        Score flood risk (0-100)
        Higher score = lower risk (safer)
        """
        if not barangay_meta:
            return 70.0  # Default moderate risk
        
        # Coastal areas have higher flood risk
        if barangay_meta.elevation_type == 'coastal':
            return 40.0  # Higher risk
        elif barangay_meta.elevation_type == 'plains':
            return 60.0  # Moderate risk
        elif barangay_meta.elevation_type == 'highland':
            return 90.0  # Lower risk
        
        return 70.0  # Default
    
    def _score_infrastructure_access(self, project: Project, barangay_meta: Optional[BarangayMetadata]) -> float:
        """
        Score infrastructure access (0-100)
        Higher score = better infrastructure
        """
        if not barangay_meta:
            return 60.0
        
        score = 50.0  # Base score
        
        # Urban areas typically have better infrastructure
        if barangay_meta.barangay_class == 'urban':
            score += 30.0
        elif barangay_meta.barangay_class == 'rural':
            score += 10.0
        
        # Check for special features (hospitals, markets, etc.)
        special_features = barangay_meta.special_features or []
        if special_features:
            # More features = better infrastructure
            feature_count = len(special_features)
            score += min(feature_count * 5, 20)  # Max 20 points
        
        # Economic centers have better infrastructure
        if barangay_meta.economic_class == 'growth_center':
            score += 10.0
        
        return min(score, 100.0)
    
    def _score_elevation(self, project: Project, barangay_meta: Optional[BarangayMetadata]) -> float:
        """
        Score elevation suitability (0-100)
        Higher score = more suitable elevation
        """
        if not barangay_meta:
            return 70.0
        
        elevation_type = barangay_meta.elevation_type
        
        # Different project types prefer different elevations
        project_zone = project.zone_type or ''
        
        if 'I-' in project_zone or 'AGRO' in project_zone:
            # Industrial projects prefer plains
            if elevation_type == 'plains':
                return 90.0
            elif elevation_type == 'coastal':
                return 70.0
            else:
                return 50.0
        elif 'R-' in project_zone or 'SHZ' in project_zone:
            # Residential projects prefer plains or highland
            if elevation_type == 'plains':
                return 85.0
            elif elevation_type == 'highland':
                return 75.0
            else:
                return 60.0
        elif 'C-' in project_zone:
            # Commercial projects prefer plains
            if elevation_type == 'plains':
                return 90.0
            elif elevation_type == 'coastal':
                return 70.0
            else:
                return 60.0
        else:
            # Default scoring
            if elevation_type == 'plains':
                return 80.0
            elif elevation_type == 'highland':
                return 70.0
            else:
                return 60.0
    
    def _score_economic_alignment(self, project: Project, barangay_meta: Optional[BarangayMetadata]) -> float:
        """
        Score economic zone alignment (0-100)
        Higher score = better alignment with economic development goals
        """
        if not barangay_meta:
            return 70.0
        
        score = 70.0  # Base score
        
        # Growth centers are ideal for most projects
        if barangay_meta.economic_class == 'growth_center':
            score += 20.0
        elif barangay_meta.economic_class == 'emerging':
            score += 10.0
        elif barangay_meta.economic_class == 'satellite':
            score += 5.0
        
        # Check if project type aligns with barangay industries
        project_zone = project.zone_type or ''
        primary_industries = barangay_meta.primary_industries or []
        
        if 'I-' in project_zone and 'industrial' in str(primary_industries).lower():
            score += 10.0
        elif 'C-' in project_zone and 'commercial' in str(primary_industries).lower():
            score += 10.0
        
        return min(score, 100.0)
    
    def _score_population_density(self, project: Project, barangay_meta: Optional[BarangayMetadata]) -> float:
        """
        Score population density appropriateness (0-100)
        Higher score = appropriate density for project type
        """
        if not barangay_meta or not barangay_meta.density:
            return 70.0
        
        density = float(barangay_meta.density)
        project_zone = project.zone_type or ''
        
        # High density (>5000/km²) is good for commercial/residential
        if 'C-' in project_zone or 'R-3' in project_zone:
            if density > 5000:
                return 90.0
            elif density > 2000:
                return 75.0
            else:
                return 60.0
        # Medium density (2000-5000/km²) is good for medium residential
        elif 'R-2' in project_zone:
            if 2000 <= density <= 5000:
                return 85.0
            else:
                return 65.0
        # Low density (<2000/km²) is good for low residential or industrial
        elif 'R-1' in project_zone or 'I-' in project_zone:
            if density < 2000:
                return 85.0
            elif density < 5000:
                return 70.0
            else:
                return 50.0
        else:
            return 70.0  # Default
    
    def _categorize_score(self, score: float) -> str:
        """Categorize overall score"""
        if score >= 80:
            return 'highly_suitable'
        elif score >= 60:
            return 'suitable'
        elif score >= 40:
            return 'moderately_suitable'
        elif score >= 20:
            return 'marginally_suitable'
        else:
            return 'not_suitable'
    
    def _identify_risks(self, factor_scores: Dict, barangay_meta: Optional[BarangayMetadata]) -> Dict:
        """Identify specific risks"""
        risks = {
            'has_flood_risk': factor_scores['flood_risk'] < 50,
            'has_slope_risk': False,  # Could be enhanced with actual slope data
            'has_zoning_conflict': factor_scores['zoning_compliance'] < 50,
            'has_infrastructure_gap': factor_scores['infrastructure_access'] < 50,
        }
        
        # Check elevation for slope risk
        if barangay_meta and barangay_meta.elevation_type == 'highland':
            risks['has_slope_risk'] = True
        
        return risks
    
    def _generate_recommendations(self, factor_scores: Dict, overall_score: float, 
                                 project: Project, barangay_meta: Optional[BarangayMetadata]) -> List[str]:
        """Generate recommendations for improving suitability"""
        recommendations = []
        
        if factor_scores['zoning_compliance'] < 60:
            recommendations.append(
                "Verify zoning classification matches project type. Consider applying for zone variance if needed."
            )
        
        if factor_scores['flood_risk'] < 50:
            recommendations.append(
                "Conduct detailed flood risk assessment. Consider flood mitigation measures or alternative location."
            )
        
        if factor_scores['infrastructure_access'] < 60:
            recommendations.append(
                "Assess infrastructure needs. Plan for additional utilities or road access if required."
            )
        
        if factor_scores['elevation_suitability'] < 60:
            recommendations.append(
                "Evaluate site-specific elevation and slope conditions. May require additional engineering."
            )
        
        if overall_score < 60:
            recommendations.append(
                "Consider alternative locations or project modifications to improve suitability."
            )
        
        if not recommendations:
            recommendations.append("Location appears suitable for project. Proceed with standard planning procedures.")
        
        return recommendations
    
    def _identify_constraints(self, factor_scores: Dict, barangay_meta: Optional[BarangayMetadata]) -> List[str]:
        """Identify constraints or limitations"""
        constraints = []
        
        if barangay_meta:
            if barangay_meta.elevation_type == 'coastal':
                constraints.append("Coastal location may require special materials and flood protection.")
            
            if barangay_meta.elevation_type == 'highland':
                constraints.append("Highland location may require slope stability analysis.")
            
            if barangay_meta.barangay_class == 'rural':
                constraints.append("Rural location may have limited infrastructure access.")
        
        if factor_scores['zoning_compliance'] < 50:
            constraints.append("Zoning classification may not align with project type.")
        
        return constraints
    
    def save_analysis(self, project: Project, analysis_result: Dict) -> LandSuitabilityAnalysis:
        """Save analysis results to database"""
        analysis, created = LandSuitabilityAnalysis.objects.update_or_create(
            project=project,
            defaults={
                'overall_score': analysis_result['overall_score'],
                'suitability_category': analysis_result['suitability_category'],
                'zoning_compliance_score': analysis_result['factor_scores']['zoning_compliance'],
                'flood_risk_score': analysis_result['factor_scores']['flood_risk'],
                'infrastructure_access_score': analysis_result['factor_scores']['infrastructure_access'],
                'elevation_suitability_score': analysis_result['factor_scores']['elevation_suitability'],
                'economic_alignment_score': analysis_result['factor_scores']['economic_alignment'],
                'population_density_score': analysis_result['factor_scores']['population_density'],
                'has_flood_risk': analysis_result['risks']['has_flood_risk'],
                'has_slope_risk': analysis_result['risks']['has_slope_risk'],
                'has_zoning_conflict': analysis_result['risks']['has_zoning_conflict'],
                'has_infrastructure_gap': analysis_result['risks']['has_infrastructure_gap'],
                'recommendations': analysis_result['recommendations'],
                'constraints': analysis_result['constraints'],
            }
        )
        return analysis
```

---

### **Phase 3: Management Commands** (Week 2)

#### 3.1 Create Analysis Command
**File:** `projeng/management/commands/analyze_land_suitability.py`

```python
from django.core.management.base import BaseCommand
from projeng.models import Project
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
            help='Analyze all projects',
        )
        parser.add_argument(
            '--save',
            action='store_true',
            help='Save results to database',
        )
    
    def handle(self, *args, **options):
        analyzer = LandSuitabilityAnalyzer()
        
        if options['project_id']:
            try:
                project = Project.objects.get(pk=options['project_id'])
                projects = [project]
            except Project.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Project {options["project_id"]} not found'))
                return
        elif options['all']:
            projects = Project.objects.all()
        else:
            self.stdout.write(self.style.ERROR('Specify --project-id or --all'))
            return
        
        self.stdout.write(f'Analyzing {len(projects)} project(s)...\n')
        
        for project in projects:
            result = analyzer.analyze_project(project)
            
            self.stdout.write(f'\n{project.name} (ID: {project.id})')
            self.stdout.write(f'  Overall Score: {result["overall_score"]}/100')
            self.stdout.write(f'  Category: {result["suitability_category"]}')
            self.stdout.write(f'  Factor Scores:')
            for factor, score in result['factor_scores'].items():
                self.stdout.write(f'    - {factor}: {score}/100')
            
            if result['risks']:
                self.stdout.write(f'  Risks:')
                for risk, value in result['risks'].items():
                    if value:
                        self.stdout.write(f'    - {risk}: Yes')
            
            if options['save']:
                analyzer.save_analysis(project, result)
                self.stdout.write(self.style.SUCCESS('  ✓ Saved to database'))
```

---

### **Phase 4: Views & API Integration** (Week 3)

#### 4.1 Add Analysis to Project Views
**File:** `projeng/views.py` (additions)

```python
from projeng.land_suitability import LandSuitabilityAnalyzer
from projeng.models import LandSuitabilityAnalysis

def project_detail_with_suitability(request, pk):
    """Project detail view with suitability analysis"""
    project = get_object_or_404(Project, pk=pk)
    
    # Get or perform suitability analysis
    try:
        suitability = project.suitability_analysis
    except LandSuitabilityAnalysis.DoesNotExist:
        # Perform analysis on the fly
        analyzer = LandSuitabilityAnalyzer()
        result = analyzer.analyze_project(project)
        suitability = analyzer.save_analysis(project, result)
    
    context = {
        'project': project,
        'suitability': suitability,
    }
    return render(request, 'projeng/project_detail.html', context)
```

#### 4.2 Create API Endpoint
**File:** `projeng/api_views.py` (additions)

```python
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from projeng.land_suitability import LandSuitabilityAnalyzer
from projeng.models import Project

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def analyze_suitability(request, project_id):
    """API endpoint to analyze project suitability"""
    try:
        project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        return Response({'error': 'Project not found'}, status=404)
    
    analyzer = LandSuitabilityAnalyzer()
    result = analyzer.analyze_project(project)
    
    # Save if requested
    if request.method == 'POST':
        analyzer.save_analysis(project, result)
    
    return Response(result)
```

---

### **Phase 5: Frontend Integration** (Week 3-4)

#### 5.1 Add Suitability Display to Project Detail Template
**File:** `templates/projeng/project_detail.html` (additions)

```html
<!-- Land Suitability Section -->
{% if suitability %}
<div class="card mb-4">
    <div class="card-header">
        <h3>Land Suitability Analysis</h3>
    </div>
    <div class="card-body">
        <!-- Overall Score -->
        <div class="mb-4">
            <div class="d-flex justify-content-between align-items-center mb-2">
                <span class="font-weight-bold">Overall Suitability Score</span>
                <span class="badge badge-{{ suitability.get_score_color }}">
                    {{ suitability.overall_score }}/100
                </span>
            </div>
            <div class="progress" style="height: 25px;">
                <div class="progress-bar bg-{{ suitability.get_score_color }}" 
                     style="width: {{ suitability.overall_score }}%">
                    {{ suitability.get_suitability_category_display }}
                </div>
            </div>
        </div>
        
        <!-- Factor Scores -->
        <div class="row mb-4">
            <div class="col-md-6">
                <h5>Factor Scores</h5>
                <ul class="list-group">
                    <li class="list-group-item d-flex justify-content-between">
                        <span>Zoning Compliance</span>
                        <span>{{ suitability.zoning_compliance_score }}/100</span>
                    </li>
                    <li class="list-group-item d-flex justify-content-between">
                        <span>Flood Risk</span>
                        <span>{{ suitability.flood_risk_score }}/100</span>
                    </li>
                    <li class="list-group-item d-flex justify-content-between">
                        <span>Infrastructure Access</span>
                        <span>{{ suitability.infrastructure_access_score }}/100</span>
                    </li>
                </ul>
            </div>
            <div class="col-md-6">
                <h5>Additional Factors</h5>
                <ul class="list-group">
                    <li class="list-group-item d-flex justify-content-between">
                        <span>Elevation Suitability</span>
                        <span>{{ suitability.elevation_suitability_score }}/100</span>
                    </li>
                    <li class="list-group-item d-flex justify-content-between">
                        <span>Economic Alignment</span>
                        <span>{{ suitability.economic_alignment_score }}/100</span>
                    </li>
                    <li class="list-group-item d-flex justify-content-between">
                        <span>Population Density</span>
                        <span>{{ suitability.population_density_score }}/100</span>
                    </li>
                </ul>
            </div>
        </div>
        
        <!-- Risks -->
        {% if suitability.has_flood_risk or suitability.has_slope_risk or suitability.has_zoning_conflict %}
        <div class="alert alert-warning">
            <h5>Risk Factors Identified</h5>
            <ul>
                {% if suitability.has_flood_risk %}<li>Flood Risk</li>{% endif %}
                {% if suitability.has_slope_risk %}<li>Slope Risk</li>{% endif %}
                {% if suitability.has_zoning_conflict %}<li>Zoning Conflict</li>{% endif %}
                {% if suitability.has_infrastructure_gap %}<li>Infrastructure Gap</li>{% endif %}
            </ul>
        </div>
        {% endif %}
        
        <!-- Recommendations -->
        {% if suitability.recommendations %}
        <div class="alert alert-info">
            <h5>Recommendations</h5>
            <ul>
                {% for rec in suitability.recommendations %}
                <li>{{ rec }}</li>
                {% endfor %}
            </ul>
        </div>
        {% endif %}
        
        <!-- Constraints -->
        {% if suitability.constraints %}
        <div class="alert alert-secondary">
            <h5>Constraints</h5>
            <ul>
                {% for constraint in suitability.constraints %}
                <li>{{ constraint }}</li>
                {% endfor %}
            </ul>
        </div>
        {% endif %}
    </div>
</div>
{% endif %}
```

#### 5.2 Create Suitability Dashboard
**File:** `templates/monitoring/suitability_dashboard.html` (new file)

```html
<!-- Dashboard showing suitability scores for all projects -->
<!-- Include charts, filters, and detailed views -->
```

---

### **Phase 6: Testing** (Week 4)

#### 6.1 Unit Tests
**File:** `projeng/tests/test_land_suitability.py`

```python
from django.test import TestCase
from projeng.models import Project, BarangayMetadata, ZoningZone
from projeng.land_suitability import LandSuitabilityAnalyzer


class LandSuitabilityTestCase(TestCase):
    def setUp(self):
        # Create test data
        pass
    
    def test_zoning_compliance_scoring(self):
        # Test zoning compliance calculation
        pass
    
    def test_flood_risk_scoring(self):
        # Test flood risk assessment
        pass
    
    def test_overall_score_calculation(self):
        # Test weighted score calculation
        pass
```

---

## 📅 Implementation Timeline

| Phase | Duration | Tasks |
|-------|----------|-------|
| **Phase 1** | Week 1 | Database models, migrations |
| **Phase 2** | Week 2 | Core analysis engine |
| **Phase 3** | Week 2 | Management commands |
| **Phase 4** | Week 3 | Views & API integration |
| **Phase 5** | Week 3-4 | Frontend integration |
| **Phase 6** | Week 4 | Testing & validation |

**Total Estimated Time: 4 weeks**

---

## 🚀 Quick Start

### Step 1: Run Migrations
```bash
python manage.py makemigrations projeng
python manage.py migrate
```

### Step 2: Analyze a Project
```bash
python manage.py analyze_land_suitability --project-id 1 --save
```

### Step 3: Analyze All Projects
```bash
python manage.py analyze_land_suitability --all --save
```

---

## ✅ Success Criteria

1. ✅ Projects can be analyzed for land suitability
2. ✅ Suitability scores are calculated and stored
3. ✅ Recommendations and constraints are generated
4. ✅ Suitability data is displayed in project views
5. ✅ API endpoints provide suitability data
6. ✅ Management commands allow batch analysis

---

## 🔄 Future Enhancements

1. **GIS Integration**: Use actual elevation/slope data from DEM files
2. **Flood Maps**: Integrate with flood hazard maps
3. **Machine Learning**: Train ML models on historical project success data
4. **Real-time Updates**: Auto-analyze when projects are created/updated
5. **Comparative Analysis**: Compare multiple potential sites
6. **Cost-Benefit Integration**: Factor in suitability when calculating project costs

---

**Ready to implement? Start with Phase 1!** 🎯

