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


# Zone Compatibility Matrix from Tagum City Ordinance No. 45, S-2002
# Format: (zone_from, zone_to): is_compatible
# 0 = Compatible, X = Incompatible
ZONE_COMPATIBILITY_MATRIX = {
    # R1 (Low Density Residential)
    ('R1', 'R1'): True,   # Same zone
    ('R1', 'R2'): True,   # Compatible (0)
    ('R1', 'R3'): True,   # Compatible (0)
    ('R1', 'C1'): False,  # Incompatible (X)
    ('R1', 'C2'): False,  # Incompatible (X)
    ('R1', 'I1'): False,  # Incompatible (X)
    ('R1', 'I2'): False,  # Incompatible (X)
    ('R1', 'Al'): False,  # Incompatible (X)
    ('R1', 'In'): True,   # Compatible (0)
    ('R1', 'Ag'): False,  # Incompatible (X)
    ('R1', 'Cu'): True,   # Compatible (0)
    
    # R2 (Medium Density Residential)
    ('R2', 'R1'): True,
    ('R2', 'R2'): True,
    ('R2', 'R3'): True,
    ('R2', 'C1'): True,   # Compatible (0)
    ('R2', 'C2'): True,   # Compatible (0)
    ('R2', 'I1'): False,  # Incompatible (X)
    ('R2', 'I2'): False,  # Incompatible (X)
    ('R2', 'Al'): False,  # Incompatible (X)
    ('R2', 'In'): True,   # Compatible (0)
    ('R2', 'Ag'): False,  # Incompatible (X)
    ('R2', 'Cu'): True,   # Compatible (0)
    
    # R3 (High Density Residential)
    ('R3', 'R1'): True,
    ('R3', 'R2'): True,
    ('R3', 'R3'): True,
    ('R3', 'C1'): True,   # Compatible (0)
    ('R3', 'C2'): True,   # Compatible (0)
    ('R3', 'I1'): False,  # Incompatible (X)
    ('R3', 'I2'): False,  # Incompatible (X)
    ('R3', 'Al'): False,  # Incompatible (X)
    ('R3', 'In'): True,   # Compatible (0)
    ('R3', 'Ag'): False,  # Incompatible (X)
    ('R3', 'Cu'): True,   # Compatible (0)
    
    # C1 (Major Commercial)
    ('C1', 'R1'): False,  # Incompatible (X)
    ('C1', 'R2'): True,   # Compatible (0)
    ('C1', 'R3'): True,   # Compatible (0)
    ('C1', 'C1'): True,
    ('C1', 'C2'): True,   # Compatible (0)
    ('C1', 'I1'): True,   # Compatible (0)
    ('C1', 'I2'): True,   # Compatible (0)
    ('C1', 'Al'): False,  # Incompatible (X)
    ('C1', 'In'): True,   # Compatible (0)
    ('C1', 'Ag'): False,  # Incompatible (X)
    ('C1', 'Cu'): True,   # Compatible (0)
    
    # C2 (Minor Commercial)
    ('C2', 'R1'): False,  # Incompatible (X)
    ('C2', 'R2'): True,   # Compatible (0)
    ('C2', 'R3'): True,   # Compatible (0)
    ('C2', 'C1'): True,   # Compatible (0)
    ('C2', 'C2'): True,
    ('C2', 'I1'): True,   # Compatible (0)
    ('C2', 'I2'): True,   # Compatible (0)
    ('C2', 'Al'): False,  # Incompatible (X)
    ('C2', 'In'): True,   # Compatible (0)
    ('C2', 'Ag'): False,  # Incompatible (X)
    ('C2', 'Cu'): True,   # Compatible (0)
    
    # I1 (Heavy Industrial)
    ('I1', 'R1'): False,  # Incompatible (X)
    ('I1', 'R2'): False,  # Incompatible (X)
    ('I1', 'R3'): False,  # Incompatible (X)
    ('I1', 'C1'): True,   # Compatible (0)
    ('I1', 'C2'): True,   # Compatible (0)
    ('I1', 'I1'): True,
    ('I1', 'I2'): True,   # Compatible (0)
    ('I1', 'Al'): True,   # Compatible (0)
    ('I1', 'In'): False,  # Incompatible (X)
    ('I1', 'Ag'): False,  # Incompatible (X)
    ('I1', 'Cu'): False,  # Incompatible (X)
    
    # I2 (Light and Medium Industrial)
    ('I2', 'R1'): False,  # Incompatible (X)
    ('I2', 'R2'): False,  # Incompatible (X)
    ('I2', 'R3'): False,  # Incompatible (X)
    ('I2', 'C1'): True,   # Compatible (0)
    ('I2', 'C2'): True,   # Compatible (0)
    ('I2', 'I1'): True,   # Compatible (0)
    ('I2', 'I2'): True,
    ('I2', 'Al'): True,   # Compatible (0)
    ('I2', 'In'): False,  # Incompatible (X)
    ('I2', 'Ag'): False,  # Incompatible (X)
    ('I2', 'Cu'): False,  # Incompatible (X)
    
    # Al (Agro-Industrial)
    ('Al', 'R1'): False,  # Incompatible (X)
    ('Al', 'R2'): False,  # Incompatible (X)
    ('Al', 'R3'): False,  # Incompatible (X)
    ('Al', 'C1'): False,  # Incompatible (X)
    ('Al', 'C2'): False,  # Incompatible (X)
    ('Al', 'I1'): True,   # Compatible (0)
    ('Al', 'I2'): True,   # Compatible (0)
    ('Al', 'Al'): True,
    ('Al', 'In'): False,  # Incompatible (X)
    ('Al', 'Ag'): False,  # Incompatible (X)
    ('Al', 'Cu'): True,   # Compatible (0)
    
    # In (Institutional)
    ('In', 'R1'): True,   # Compatible (0)
    ('In', 'R2'): True,   # Compatible (0)
    ('In', 'R3'): True,   # Compatible (0)
    ('In', 'C1'): True,   # Compatible (0)
    ('In', 'C2'): True,   # Compatible (0)
    ('In', 'I1'): False,  # Incompatible (X)
    ('In', 'I2'): False,  # Incompatible (X)
    ('In', 'Al'): False,  # Incompatible (X)
    ('In', 'In'): True,
    ('In', 'Ag'): False,  # Incompatible (X)
    ('In', 'Cu'): True,   # Compatible (0)
    
    # Ag (Agricultural)
    ('Ag', 'R1'): False,  # Incompatible (X)
    ('Ag', 'R2'): False,  # Incompatible (X)
    ('Ag', 'R3'): False,  # Incompatible (X)
    ('Ag', 'C1'): False,  # Incompatible (X)
    ('Ag', 'C2'): False,  # Incompatible (X)
    ('Ag', 'I1'): False,  # Incompatible (X)
    ('Ag', 'I2'): False,  # Incompatible (X)
    ('Ag', 'Al'): False,  # Incompatible (X)
    ('Ag', 'In'): False,  # Incompatible (X)
    ('Ag', 'Ag'): True,
    ('Ag', 'Cu'): False,  # Incompatible (X)
    
    # Cu (Cultural)
    ('Cu', 'R1'): True,   # Compatible (0)
    ('Cu', 'R2'): True,   # Compatible (0)
    ('Cu', 'R3'): True,   # Compatible (0)
    ('Cu', 'C1'): True,   # Compatible (0)
    ('Cu', 'C2'): True,   # Compatible (0)
    ('Cu', 'I1'): False,  # Incompatible (X)
    ('Cu', 'I2'): False,  # Incompatible (X)
    ('Cu', 'Al'): False,  # Incompatible (X)
    ('Cu', 'In'): True,   # Compatible (0)
    ('Cu', 'Ag'): False,  # Incompatible (X)
    ('Cu', 'Cu'): True,
}


def normalize_zone_type(zone_type: str) -> str:
    """
    Normalize zone type to match matrix format
    Converts 'R-1' -> 'R1', 'C-1' -> 'C1', etc.
    """
    if not zone_type:
        return ''
    # Remove hyphens and spaces
    normalized = zone_type.replace('-', '').replace(' ', '').upper()
    # Handle special cases
    if normalized.startswith('R') and len(normalized) == 2:
        return normalized
    elif normalized.startswith('C') and len(normalized) == 2:
        return normalized
    elif normalized.startswith('I') and len(normalized) == 2:
        return normalized
    # Handle other zone types
    zone_mapping = {
        'AGRO': 'Al',
        'AGROINDUSTRIAL': 'Al',
        'INSTITUTIONAL': 'In',
        'INS1': 'In',
        'AGRICULTURAL': 'Ag',
        'CULTURAL': 'Cu',
    }
    return zone_mapping.get(normalized, normalized[:2])


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
    
    def save_analysis(self, project: Project, analysis_result: Dict) -> LandSuitabilityAnalysis:
        """
        Save analysis results to database
        
        Args:
            project: Project instance
            analysis_result: Result dict from analyze_project()
        
        Returns:
            LandSuitabilityAnalysis instance
        """
        # Get or create analysis
        analysis, created = LandSuitabilityAnalysis.objects.get_or_create(
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
        
        if not created:
            # Update existing analysis
            analysis.overall_score = analysis_result['overall_score']
            analysis.suitability_category = analysis_result['suitability_category']
            analysis.zoning_compliance_score = analysis_result['factor_scores']['zoning_compliance']
            analysis.flood_risk_score = analysis_result['factor_scores']['flood_risk']
            analysis.infrastructure_access_score = analysis_result['factor_scores']['infrastructure_access']
            analysis.elevation_suitability_score = analysis_result['factor_scores']['elevation_suitability']
            analysis.economic_alignment_score = analysis_result['factor_scores']['economic_alignment']
            analysis.population_density_score = analysis_result['factor_scores']['population_density']
            analysis.has_flood_risk = analysis_result['risks']['has_flood_risk']
            analysis.has_slope_risk = analysis_result['risks']['has_slope_risk']
            analysis.has_zoning_conflict = analysis_result['risks']['has_zoning_conflict']
            analysis.has_infrastructure_gap = analysis_result['risks']['has_infrastructure_gap']
            analysis.recommendations = analysis_result['recommendations']
            analysis.constraints = analysis_result['constraints']
            analysis.save()
        
        return analysis
    
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
        Score zoning compliance (0-100) using Zone Compatibility Matrix
        Higher score = better compliance
        """
        if not project.zone_type:
            return 50.0  # Neutral if no zone type set
        
        project_zone = normalize_zone_type(project.zone_type)
        
        if not barangay_meta or not project.barangay:
            return 60.0  # Default moderate score
        
        # Get all zones in the barangay
        barangay_zones = ZoningZone.objects.filter(
            barangay=project.barangay,
            is_active=True
        )
        
        if not barangay_zones.exists():
            return 60.0  # No zone data available
        
        # Check for exact match
        exact_match = barangay_zones.filter(zone_type=project.zone_type).exists()
        if exact_match:
            return 100.0  # Perfect match
        
        # Check compatibility with existing zones using matrix
        compatible_count = 0
        incompatible_count = 0
        total_zones = 0
        
        for barangay_zone in barangay_zones:
            barangay_zone_normalized = normalize_zone_type(barangay_zone.zone_type)
            
            # Check compatibility in matrix
            compatibility_key = (project_zone, barangay_zone_normalized)
            if compatibility_key in ZONE_COMPATIBILITY_MATRIX:
                is_compatible = ZONE_COMPATIBILITY_MATRIX[compatibility_key]
                if is_compatible:
                    compatible_count += 1
                else:
                    incompatible_count += 1
                total_zones += 1
        
        if total_zones == 0:
            return 60.0  # No matching zones found
        
        # Calculate score based on compatibility ratio
        compatibility_ratio = compatible_count / total_zones
        
        if compatibility_ratio >= 0.8:  # 80%+ compatible
            return 85.0
        elif compatibility_ratio >= 0.5:  # 50-80% compatible
            return 75.0
        elif compatibility_ratio >= 0.3:  # 30-50% compatible
            return 50.0
        elif incompatible_count > compatible_count:  # More incompatible
            return 30.0  # Conflict
        else:
            return 60.0  # Mixed
    
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
        project_zone = project.zone_type or ''
        
        if 'I-' in project_zone or 'AGRO' in project_zone.upper():
            # Industrial projects prefer plains
            if elevation_type == 'plains':
                return 90.0
            elif elevation_type == 'coastal':
                return 70.0
            else:
                return 50.0
        elif 'R-' in project_zone or 'SHZ' in project_zone.upper():
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
                constraints.append("Zoning compliance issues may require variance or rezoning.")
        
        return constraints

