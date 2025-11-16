"""
Zone Compatibility Recommendation Engine

This module provides zone validation and recommendation functionality using
Multi-Criteria Decision Analysis (MCDA) to suggest optimal zones for projects.
"""

from typing import Dict, List, Optional, Tuple
from django.db.models import Q, Count, Avg
from .models import (
    Project,
    ProjectType,
    ZoneAllowedUse,
    ZoneRecommendation,
    BarangayMetadata,
    ZoningZone,
    LandSuitabilityAnalysis
)


class ZoneCompatibilityEngine:
    """
    Engine for validating project-zone compatibility and recommending optimal zones.
    
    This engine:
    1. Validates if a project type is allowed in a selected zone
    2. Finds all allowed zones for a project type
    3. Scores each zone using MCDA (Multi-Criteria Decision Analysis)
    4. Provides ranked recommendations
    """
    
    # MCDA Factor Weights (must sum to 1.0)
    WEIGHT_ZONING_COMPLIANCE = 0.40  # 40% - Is project type allowed?
    WEIGHT_LAND_AVAILABILITY = 0.20  # 20% - How much land is available?
    WEIGHT_ACCESSIBILITY = 0.20      # 20% - How accessible is the zone?
    WEIGHT_COMMUNITY_IMPACT = 0.10   # 10% - Positive community impact?
    WEIGHT_INFRASTRUCTURE = 0.10     # 10% - Infrastructure support?
    
    def __init__(self):
        """Initialize the engine"""
        pass
    
    @staticmethod
    def normalize_zone_type(zone_type: str) -> str:
        """
        Normalize zone type format for ZoneAllowedUse queries.
        Converts hyphenated format (R-1, C-1, I-1) to non-hyphenated (R1, C1, I1).
        Also handles special cases and legacy formats.
        
        Args:
            zone_type: Zone type code (can be R-1, R1, etc.)
        
        Returns:
            Normalized zone type code for ZoneAllowedUse queries
        """
        if not zone_type:
            return zone_type
        
        # Remove hyphens for standard zone types
        # R-1 -> R1, C-1 -> C1, I-1 -> I1, etc.
        normalized = zone_type.replace('-', '')
        
        # Handle special zone types that don't use hyphens
        # INS-1 should become In (legacy format used in ZoneAllowedUse)
        if normalized == 'INS1' or normalized == 'INS-1':
            normalized = 'In'  # Legacy format used in ZoneAllowedUse
        
        # Handle AGRO vs Al (Agro-Industrial)
        if normalized == 'AGRO':
            normalized = 'Al'  # Legacy format used in ZoneAllowedUse
        
        return normalized
    
    @staticmethod
    def format_zone_type_for_display(zone_type: str) -> str:
        """
        Format zone type for display (convert to hyphenated format).
        Converts non-hyphenated (R1, C1, I1) to hyphenated (R-1, C-1, I-1).
        
        Args:
            zone_type: Zone type code (can be R1, R-1, etc.)
        
        Returns:
            Formatted zone type code for display (R-1, C-1, etc.)
        """
        if not zone_type:
            return zone_type
        
        # If already hyphenated, return as-is (except special cases)
        if '-' in zone_type:
            return zone_type
        
        # Convert non-hyphenated to hyphenated
        # R1 -> R-1, C1 -> C-1, I1 -> I-1, R2 -> R-2, etc.
        import re
        # Match pattern: letter(s) followed by number(s)
        match = re.match(r'^([A-Z]+)(\d+)$', zone_type)
        if match:
            prefix = match.group(1)
            number = match.group(2)
            # Only add hyphen for standard residential/commercial/industrial zones
            if prefix in ['R', 'C', 'I']:
                return f'{prefix}-{number}'
        
        # Handle special cases
        # In -> INS-1 (Institutional)
        if zone_type == 'In':
            return 'INS-1'
        # Al -> AGRO (Agro-Industrial)
        if zone_type == 'Al':
            return 'AGRO'
        
        # Special zones that don't need hyphenation
        return zone_type
    
    @staticmethod
    def get_zone_display_name(zone_type: str) -> str:
        """
        Get human-readable display name for a zone type.
        
        Args:
            zone_type: Zone type code (can be R-1, R1, etc.)
        
        Returns:
            Human-readable zone name
        """
        if not zone_type:
            return zone_type
        
        # Normalize zone type first
        normalized = ZoneCompatibilityEngine.normalize_zone_type(zone_type)
        
        # Zone name mapping
        zone_names = {
            'R1': 'Low Density Residential',
            'R2': 'Medium Density Residential',
            'R3': 'High Density Residential',
            'SHZ': 'Socialized Housing',
            'C1': 'Major Commercial',
            'C2': 'Minor Commercial',
            'I1': 'Heavy Industrial',
            'I2': 'Light/Medium Industrial',
            'Al': 'Agro-Industrial',
            'AGRO': 'Agro-Industrial',
            'In': 'Institutional',
            'INS-1': 'Institutional',
            'Ag': 'Agricultural',
            'AGRICULTURAL': 'Agricultural / SAFDZ',
            'Cu': 'Cultural',
            'PARKS': 'Parks & Open Spaces',
            'ECO-TOURISM': 'Eco-tourism',
            'SPECIAL': 'Special Use',
            'COASTAL': 'Coastal Zone',
            'RECLAMATION': 'Reclamation Proposed Zone',
            'CEMETERY': 'Cemetery / Memorial Park',
        }
        
        return zone_names.get(normalized, zone_names.get(zone_type, zone_type))
    
    def validate_project_zone(
        self,
        project_type_code: str,
        zone_type: str
    ) -> Dict:
        """
        Validate if a project type is allowed in a selected zone.
        
        Args:
            project_type_code: Code of the project type (e.g., 'apartment_building')
            zone_type: Zone type code (e.g., 'R1', 'R3', 'C1')
        
        Returns:
            Dict with validation results:
            {
                'is_allowed': bool,
                'is_primary': bool,
                'is_conditional': bool,
                'message': str,
                'conditions': str,
                'max_density': str,
                'max_height': str
            }
        """
        try:
            project_type = ProjectType.objects.get(code=project_type_code)
        except ProjectType.DoesNotExist:
            return {
                'is_allowed': False,
                'is_primary': False,
                'is_conditional': False,
                'message': f'Project type "{project_type_code}" not found',
                'conditions': '',
                'max_density': '',
                'max_height': ''
            }
        
        # Normalize zone type for ZoneAllowedUse query (R-1 -> R1)
        normalized_zone_type = self.normalize_zone_type(zone_type)
        
        try:
            allowed_use = ZoneAllowedUse.objects.get(
                zone_type=normalized_zone_type,
                project_type=project_type
            )
            
            return {
                'is_allowed': True,
                'is_primary': allowed_use.is_primary_use,
                'is_conditional': allowed_use.is_conditional,
                'message': (
                    f'Project type "{project_type.name}" is '
                    f'{"conditionally " if allowed_use.is_conditional else ""}'
                    f'allowed in {self.format_zone_type_for_display(zone_type)} zone'
                ),
                'conditions': allowed_use.conditions,
                'max_density': allowed_use.max_density,
                'max_height': allowed_use.max_height
            }
        except ZoneAllowedUse.DoesNotExist:
            return {
                'is_allowed': False,
                'is_primary': False,
                'is_conditional': False,
                'message': (
                    f'Project type "{project_type.name}" is NOT allowed in {self.format_zone_type_for_display(zone_type)} zone'
                ),
                'conditions': '',
                'max_density': '',
                'max_height': ''
            }
    
    def find_allowed_zones(
        self,
        project_type_code: str,
        include_conditional: bool = True
    ) -> List[Dict]:
        """
        Find all zones where a project type is allowed.
        
        Args:
            project_type_code: Code of the project type
            include_conditional: Whether to include conditional uses
        
        Returns:
            List of dicts with zone information:
            [
                {
                    'zone_type': str,
                    'zone_name': str,
                    'is_primary': bool,
                    'is_conditional': bool,
                    'conditions': str,
                    'max_density': str,
                    'max_height': str
                },
                ...
            ]
        """
        try:
            project_type = ProjectType.objects.get(code=project_type_code)
        except ProjectType.DoesNotExist:
            return []
        
        query = Q(project_type=project_type)
        if not include_conditional:
            query &= Q(is_conditional=False)
        
        allowed_uses = ZoneAllowedUse.objects.filter(query).select_related('project_type')
        
        # Zone name mapping (using display format)
        zone_names = {
            'R1': 'Low Density Residential',
            'R2': 'Medium Density Residential',
            'R3': 'High Density Residential',
            'SHZ': 'Socialized Housing Zone',
            'C1': 'Major Commercial Zone',
            'C2': 'Minor Commercial Zone',
            'I1': 'Heavy Industrial Zone',
            'I2': 'Light and Medium Industrial Zone',
            'Al': 'Agro-Industrial',
            'In': 'Institutional',
            'Ag': 'Agricultural',
            'Cu': 'Cultural',
        }
        
        results = []
        for allowed_use in allowed_uses:
            # Convert to display format (R1 -> R-1) for consistency with map
            display_zone_type = self.format_zone_type_for_display(allowed_use.zone_type)
            results.append({
                'zone_type': display_zone_type,  # Use hyphenated format for display
                'zone_name': zone_names.get(allowed_use.zone_type, allowed_use.zone_type),
                'is_primary': allowed_use.is_primary_use,
                'is_conditional': allowed_use.is_conditional,
                'conditions': allowed_use.conditions,
                'max_density': allowed_use.max_density,
                'max_height': allowed_use.max_height
            })
        
        # Sort by primary first, then by zone type
        results.sort(key=lambda x: (not x['is_primary'], x['zone_type']))
        
        return results
    
    def score_zoning_compliance(
        self,
        project_type_code: str,
        zone_type: str
    ) -> float:
        """
        Score zoning compliance (0-100).
        
        - 100: Primary use allowed
        - 70: Conditional use allowed
        - 0: Not allowed
        """
        # Normalize zone type for validation
        normalized_zone_type = self.normalize_zone_type(zone_type)
        validation = self.validate_project_zone(project_type_code, normalized_zone_type)
        
        if not validation['is_allowed']:
            return 0.0
        
        if validation['is_primary'] and not validation['is_conditional']:
            return 100.0
        elif validation['is_conditional']:
            return 70.0
        else:
            return 50.0  # Fallback
    
    def score_land_availability(
        self,
        zone_type: str,
        barangay: Optional[str] = None
    ) -> float:
        """
        Score land availability (0-100).
        
        Based on:
        - Number of existing projects in the zone
        - Barangay land area and density
        """
        # Normalize zone type for query
        normalized_zone_type = self.normalize_zone_type(zone_type)
        display_zone_type = self.format_zone_type_for_display(zone_type)
        # Query using both formats to handle existing data
        from django.db.models import Q
        projects_in_zone = Project.objects.filter(
            Q(zone_type=zone_type) | 
            Q(zone_type=normalized_zone_type) |
            Q(zone_type=display_zone_type)
        ).count()
        
        # Base score: fewer projects = more available land
        if projects_in_zone == 0:
            base_score = 100.0
        elif projects_in_zone < 5:
            base_score = 85.0
        elif projects_in_zone < 10:
            base_score = 70.0
        elif projects_in_zone < 20:
            base_score = 55.0
        else:
            base_score = 40.0
        
        # Adjust based on barangay if provided
        if barangay:
            try:
                barangay_meta = BarangayMetadata.objects.get(name=barangay)
                # Lower density = more available land
                if barangay_meta.density and barangay_meta.density > 0:
                    if barangay_meta.density < 1000:  # Low density
                        base_score = min(100.0, base_score + 15.0)
                    elif barangay_meta.density > 5000:  # High density
                        base_score = max(30.0, base_score - 15.0)
            except BarangayMetadata.DoesNotExist:
                pass
        
        return max(0.0, min(100.0, base_score))
    
    def score_accessibility(
        self,
        zone_type: str,
        barangay: Optional[str] = None
    ) -> float:
        """
        Score accessibility (0-100).
        
        Based on:
        - Barangay class (urban vs rural)
        - Economic class
        - Special features (roads, transportation)
        """
        base_score = 50.0  # Default
        
        if barangay:
            try:
                barangay_meta = BarangayMetadata.objects.get(name=barangay)
                
                # Barangay class impact
                if barangay_meta.barangay_class == 'Urban':
                    base_score += 30.0
                elif barangay_meta.barangay_class == 'Semi-Urban':
                    base_score += 15.0
                
                # Economic class impact
                if barangay_meta.economic_class in ['First Class', 'Second Class']:
                    base_score += 15.0
                elif barangay_meta.economic_class == 'Third Class':
                    base_score += 5.0
                
                # Special features
                if barangay_meta.special_features:
                    features = str(barangay_meta.special_features).lower()
                    if 'road' in features or 'highway' in features:
                        base_score += 10.0
                    if 'transportation' in features or 'terminal' in features:
                        base_score += 10.0
            except BarangayMetadata.DoesNotExist:
                pass
        
        # Zone type impact (commercial zones typically more accessible)
        # Normalize for comparison
        normalized = self.normalize_zone_type(zone_type)
        if normalized in ['C1', 'C2']:
            base_score += 20.0
        elif normalized in ['R3', 'In']:
            base_score += 10.0
        
        return max(0.0, min(100.0, base_score))
    
    def score_community_impact(
        self,
        project_type_code: str,
        zone_type: str,
        barangay: Optional[str] = None
    ) -> float:
        """
        Score community impact (0-100).
        
        Based on:
        - Project type alignment with zone purpose
        - Population density appropriateness
        """
        try:
            project_type = ProjectType.objects.get(code=project_type_code)
        except ProjectType.DoesNotExist:
            return 50.0
        
        base_score = 70.0  # Default positive
        
        # Check if project type matches zone purpose
        # Normalize zone type for validation
        normalized_zone_type = self.normalize_zone_type(zone_type)
        validation = self.validate_project_zone(project_type_code, normalized_zone_type)
        if validation['is_primary']:
            base_score += 20.0
        elif validation['is_allowed']:
            base_score += 10.0
        
        # Population density alignment
        if barangay:
            try:
                barangay_meta = BarangayMetadata.objects.get(name=barangay)
                if barangay_meta.density:
                    # High density projects in high density areas = good
                    if project_type.density_level == 'high' and barangay_meta.density > 3000:
                        base_score += 10.0
                    # Low density projects in low density areas = good
                    elif project_type.density_level == 'low' and barangay_meta.density < 2000:
                        base_score += 10.0
            except BarangayMetadata.DoesNotExist:
                pass
        
        return max(0.0, min(100.0, base_score))
    
    def score_infrastructure(
        self,
        zone_type: str,
        barangay: Optional[str] = None
    ) -> float:
        """
        Score infrastructure support (0-100).
        
        Based on:
        - Barangay economic class
        - Special features (utilities, services)
        """
        base_score = 50.0  # Default
        
        if barangay:
            try:
                barangay_meta = BarangayMetadata.objects.get(name=barangay)
                
                # Economic class impact
                if barangay_meta.economic_class == 'First Class':
                    base_score += 30.0
                elif barangay_meta.economic_class == 'Second Class':
                    base_score += 20.0
                elif barangay_meta.economic_class == 'Third Class':
                    base_score += 10.0
                
                # Special features
                if barangay_meta.special_features:
                    features = str(barangay_meta.special_features).lower()
                    if 'water' in features or 'electricity' in features:
                        base_score += 10.0
                    if 'hospital' in features or 'school' in features:
                        base_score += 10.0
            except BarangayMetadata.DoesNotExist:
                pass
        
        # Zone type impact (commercial and institutional zones have better infrastructure)
        # Normalize for comparison
        normalized = self.normalize_zone_type(zone_type)
        if normalized in ['C1', 'In']:
            base_score += 20.0
        elif normalized in ['C2', 'R3']:
            base_score += 10.0
        
        return max(0.0, min(100.0, base_score))
    
    def calculate_mcda_score(
        self,
        project_type_code: str,
        zone_type: str,
        barangay: Optional[str] = None
    ) -> Dict:
        """
        Calculate MCDA score for a zone.
        
        Returns:
            Dict with factor scores and overall score:
            {
                'zoning_compliance_score': float,
                'land_availability_score': float,
                'accessibility_score': float,
                'community_impact_score': float,
                'infrastructure_score': float,
                'overall_score': float
            }
        """
        # Calculate individual factor scores
        zoning_score = self.score_zoning_compliance(project_type_code, zone_type)
        land_score = self.score_land_availability(zone_type, barangay)
        accessibility_score = self.score_accessibility(zone_type, barangay)
        community_score = self.score_community_impact(project_type_code, zone_type, barangay)
        infrastructure_score = self.score_infrastructure(zone_type, barangay)
        
        # Calculate weighted overall score
        overall_score = (
            zoning_score * self.WEIGHT_ZONING_COMPLIANCE +
            land_score * self.WEIGHT_LAND_AVAILABILITY +
            accessibility_score * self.WEIGHT_ACCESSIBILITY +
            community_score * self.WEIGHT_COMMUNITY_IMPACT +
            infrastructure_score * self.WEIGHT_INFRASTRUCTURE
        )
        
        return {
            'zoning_compliance_score': round(zoning_score, 2),
            'land_availability_score': round(land_score, 2),
            'accessibility_score': round(accessibility_score, 2),
            'community_impact_score': round(community_score, 2),
            'infrastructure_score': round(infrastructure_score, 2),
            'overall_score': round(overall_score, 2)
        }
    
    def generate_reasoning(
        self,
        project_type_code: str,
        zone_type: str,
        scores: Dict,
        barangay: Optional[str] = None
    ) -> Tuple[str, List[str], List[str]]:
        """
        Generate reasoning, advantages, and constraints for a zone recommendation.
        
        Returns:
            Tuple of (reasoning, advantages, constraints)
        """
        try:
            project_type = ProjectType.objects.get(code=project_type_code)
        except ProjectType.DoesNotExist:
            return '', [], []
        
        validation = self.validate_project_zone(project_type_code, zone_type)
        
        reasoning_parts = []
        advantages = []
        constraints = []
        
        # Zoning compliance
        if scores['zoning_compliance_score'] >= 100:
            reasoning_parts.append("High zoning compliance")
            advantages.append("Project type is well-suited for this zone")
        elif scores['zoning_compliance_score'] >= 70:
            reasoning_parts.append("Conditional zoning compliance")
            constraints.append("Requires special permit/approval")
        else:
            reasoning_parts.append("Low zoning compliance")
            constraints.append("Project type may not be allowed in this zone")
        
        # Land availability
        if scores['land_availability_score'] >= 80:
            reasoning_parts.append("Good land availability")
            advantages.append("Less competition for land in this zone")
        elif scores['land_availability_score'] < 50:
            reasoning_parts.append("Limited land availability")
            constraints.append("High competition for land in this zone")
        
        # Accessibility
        if scores['accessibility_score'] >= 80:
            reasoning_parts.append("Good accessibility")
            advantages.append("Easy access to transportation and services")
        elif scores['accessibility_score'] < 50:
            reasoning_parts.append("Limited accessibility")
            constraints.append("May have limited access to transportation")
        
        # Community impact
        if scores['community_impact_score'] >= 80:
            reasoning_parts.append("Positive community impact")
            advantages.append("Project aligns well with community needs")
        
        # Infrastructure
        if scores['infrastructure_score'] >= 80:
            reasoning_parts.append("Strong infrastructure support")
            advantages.append("Good access to utilities and services")
        elif scores['infrastructure_score'] < 50:
            reasoning_parts.append("Limited infrastructure support")
            constraints.append("May require additional infrastructure development")
        
        # Conditions
        if validation.get('conditions'):
            constraints.append(f"Conditions: {validation['conditions']}")
        
        # Max density/height
        if validation.get('max_density'):
            constraints.append(f"Maximum density: {validation['max_density']}")
        if validation.get('max_height'):
            constraints.append(f"Maximum height: {validation['max_height']}")
        
        reasoning = ". ".join(reasoning_parts) + "."
        
        return reasoning, advantages, constraints
    
    def recommend_zones(
        self,
        project_type_code: str,
        selected_zone: Optional[str] = None,
        barangay: Optional[str] = None,
        limit: int = 5
    ) -> Dict:
        """
        Main method to get zone recommendations for a project type.
        
        Args:
            project_type_code: Code of the project type
            selected_zone: Optional selected zone to validate
            barangay: Optional barangay name for location-specific scoring
            limit: Maximum number of recommendations to return
        
        Returns:
            Dict with validation and recommendations:
            {
                'selected_zone_validation': {...},
                'allowed_zones': [...],
                'recommendations': [
                    {
                        'rank': int,
                        'zone_type': str,
                        'zone_name': str,
                        'overall_score': float,
                        'factor_scores': {...},
                        'reasoning': str,
                        'advantages': [...],
                        'constraints': [...]
                    },
                    ...
                ],
                'top_recommendation': {...}
            }
        """
        # Validate selected zone if provided
        selected_zone_validation = None
        if selected_zone:
            selected_zone_validation = self.validate_project_zone(
                project_type_code,
                selected_zone
            )
        
        # Find all allowed zones
        allowed_zones = self.find_allowed_zones(project_type_code, include_conditional=True)
        
        # Score each allowed zone
        scored_zones = []
        for zone_info in allowed_zones:
            zone_type = zone_info['zone_type']
            scores = self.calculate_mcda_score(project_type_code, zone_type, barangay)
            reasoning, advantages, constraints = self.generate_reasoning(
                project_type_code,
                zone_type,
                scores,
                barangay
            )
            
            scored_zones.append({
                'zone_type': zone_type,
                'zone_name': zone_info['zone_name'],
                'overall_score': scores['overall_score'],
                'factor_scores': {
                    'zoning_compliance': scores['zoning_compliance_score'],
                    'land_availability': scores['land_availability_score'],
                    'accessibility': scores['accessibility_score'],
                    'community_impact': scores['community_impact_score'],
                    'infrastructure': scores['infrastructure_score']
                },
                'reasoning': reasoning,
                'advantages': advantages,
                'constraints': constraints,
                'is_primary': zone_info['is_primary'],
                'is_conditional': zone_info['is_conditional']
            })
        
        # Sort by overall score (descending)
        scored_zones.sort(key=lambda x: x['overall_score'], reverse=True)
        
        # Add rank
        for i, zone in enumerate(scored_zones, 1):
            zone['rank'] = i
        
        # Limit results
        recommendations = scored_zones[:limit]
        
        # Get top recommendation
        top_recommendation = recommendations[0] if recommendations else None
        
        return {
            'selected_zone_validation': selected_zone_validation,
            'allowed_zones': allowed_zones,
            'recommendations': recommendations,
            'top_recommendation': {
                'zone_type': top_recommendation['zone_type'],
                'overall_score': top_recommendation['overall_score']
            } if top_recommendation else None
        }
    
    def save_recommendations(
        self,
        project: Project,
        project_type_code: str,
        barangay: Optional[str] = None
    ) -> List[ZoneRecommendation]:
        """
        Generate and save zone recommendations for a project.
        
        Returns:
            List of saved ZoneRecommendation objects
        """
        # Get recommendations
        result = self.recommend_zones(
            project_type_code=project_type_code,
            barangay=barangay or project.barangay,
            limit=10
        )
        
        # Delete existing recommendations
        ZoneRecommendation.objects.filter(project=project).delete()
        
        # Save new recommendations
        saved_recommendations = []
        for rec in result['recommendations']:
            zone_rec = ZoneRecommendation.objects.create(
                project=project,
                recommended_zone=rec['zone_type'],
                overall_score=rec['overall_score'],
                zoning_compliance_score=rec['factor_scores']['zoning_compliance'],
                land_availability_score=rec['factor_scores']['land_availability'],
                accessibility_score=rec['factor_scores']['accessibility'],
                community_impact_score=rec['factor_scores']['community_impact'],
                infrastructure_score=rec['factor_scores']['infrastructure'],
                rank=rec['rank'],
                reasoning=rec['reasoning'],
                advantages=rec['advantages'],
                constraints=rec['constraints']
            )
            saved_recommendations.append(zone_rec)
        
        return saved_recommendations

