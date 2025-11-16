"""
Management command to verify zone recommendation system accuracy
Usage: python manage.py verify_recommendations

This command verifies that:
1. ZoneAllowedUse data is complete
2. Validation functions work correctly
3. Recommendations are accurate and reliable
4. Scoring is consistent with expected behavior
"""

from django.core.management.base import BaseCommand
from projeng.models import ZoneAllowedUse, ProjectType, BarangayMetadata
from projeng.zone_recommendation import ZoneCompatibilityEngine


class Command(BaseCommand):
    help = 'Verify zone recommendation system accuracy and reliability'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.SUCCESS("Zone Recommendation System Verification"))
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write("")
        
        engine = ZoneCompatibilityEngine()
        
        # Track results
        results = {
            'passed': 0,
            'failed': 0,
            'warnings': 0
        }
        
        # 1. Check Data Completeness
        self.stdout.write(self.style.WARNING("1. DATA COMPLETENESS CHECK"))
        self.stdout.write("-" * 70)
        results = self._check_data_completeness(results)
        self.stdout.write("")
        
        # 2. Test Validation Functions
        self.stdout.write(self.style.WARNING("2. VALIDATION FUNCTION TESTS"))
        self.stdout.write("-" * 70)
        results = self._test_validation(engine, results)
        self.stdout.write("")
        
        # 3. Test Scoring Accuracy
        self.stdout.write(self.style.WARNING("3. SCORING ACCURACY TESTS"))
        self.stdout.write("-" * 70)
        results = self._test_scoring(engine, results)
        self.stdout.write("")
        
        # 4. Test Recommendations
        self.stdout.write(self.style.WARNING("4. RECOMMENDATION TESTS"))
        self.stdout.write("-" * 70)
        results = self._test_recommendations(engine, results)
        self.stdout.write("")
        
        # 5. Summary
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.SUCCESS("VERIFICATION SUMMARY"))
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(f"✅ Passed: {results['passed']}")
        self.stdout.write(f"❌ Failed: {results['failed']}")
        self.stdout.write(f"⚠️  Warnings: {results['warnings']}")
        self.stdout.write("")
        
        total_tests = results['passed'] + results['failed']
        if total_tests > 0:
            success_rate = (results['passed'] / total_tests) * 100
            self.stdout.write(f"Success Rate: {success_rate:.1f}%")
            
            if success_rate >= 90:
                self.stdout.write(self.style.SUCCESS("\n✅ System is highly reliable!"))
            elif success_rate >= 70:
                self.stdout.write(self.style.WARNING("\n⚠️  System needs attention"))
            else:
                self.stdout.write(self.style.ERROR("\n❌ System requires fixes"))
        
        self.stdout.write("")
    
    def _check_data_completeness(self, results):
        """Check if required data is present"""
        
        # Check project types
        total_project_types = ProjectType.objects.count()
        if total_project_types == 0:
            self.stdout.write(self.style.ERROR("❌ No project types found!"))
            self.stdout.write("   Run: python manage.py populate_project_types")
            results['failed'] += 1
        else:
            self.stdout.write(self.style.SUCCESS(f"✅ Project Types: {total_project_types}"))
            results['passed'] += 1
        
        # Check zone allowed uses
        total_allowed_uses = ZoneAllowedUse.objects.count()
        if total_allowed_uses == 0:
            self.stdout.write(self.style.ERROR("❌ No zone allowed uses found!"))
            self.stdout.write("   Run: python manage.py populate_zone_allowed_uses")
            results['failed'] += 1
        else:
            self.stdout.write(self.style.SUCCESS(f"✅ Zone Allowed Uses: {total_allowed_uses}"))
            results['passed'] += 1
            
            # Check average zones per project type
            if total_project_types > 0:
                avg_zones = total_allowed_uses / total_project_types
                self.stdout.write(f"   Average zones per project type: {avg_zones:.1f}")
                if avg_zones < 3:
                    self.stdout.write(self.style.WARNING("   ⚠️  Low zone coverage (expected: 3+ zones per type)"))
                    results['warnings'] += 1
        
        # Check project types without zone mappings
        types_without_zones = []
        for pt in ProjectType.objects.all():
            zone_count = ZoneAllowedUse.objects.filter(project_type=pt).count()
            if zone_count == 0:
                types_without_zones.append(f"{pt.code} ({pt.name})")
        
        if types_without_zones:
            self.stdout.write(self.style.WARNING(f"⚠️  Project types without zone mappings: {len(types_without_zones)}"))
            for pt_name in types_without_zones[:5]:  # Show first 5
                self.stdout.write(f"   - {pt_name}")
            if len(types_without_zones) > 5:
                self.stdout.write(f"   ... and {len(types_without_zones) - 5} more")
            results['warnings'] += len(types_without_zones)
        else:
            self.stdout.write(self.style.SUCCESS("✅ All project types have zone mappings"))
            results['passed'] += 1
        
        # Check for road project type (should be in all zones)
        try:
            road_type = ProjectType.objects.get(code='road')
            road_zones = ZoneAllowedUse.objects.filter(project_type=road_type).count()
            expected_zones = 12  # R1, R2, R3, SHZ, C1, C2, I1, I2, Al, In, Ag, Cu
            if road_zones == expected_zones:
                self.stdout.write(self.style.SUCCESS(f"✅ Road/Highway: {road_zones}/{expected_zones} zones (complete)"))
                results['passed'] += 1
            elif road_zones > 0:
                self.stdout.write(self.style.WARNING(f"⚠️  Road/Highway: {road_zones}/{expected_zones} zones"))
                results['warnings'] += 1
            else:
                self.stdout.write(self.style.ERROR(f"❌ Road/Highway: No zones mapped!"))
                results['failed'] += 1
        except ProjectType.DoesNotExist:
            self.stdout.write(self.style.WARNING("⚠️  Road project type not found"))
            results['warnings'] += 1
        
        # Check barangay metadata
        barangay_count = BarangayMetadata.objects.count()
        if barangay_count == 0:
            self.stdout.write(self.style.WARNING("⚠️  No barangay metadata (recommendations will be less accurate)"))
            self.stdout.write("   Run: python manage.py populate_barangay_metadata")
            results['warnings'] += 1
        else:
            self.stdout.write(self.style.SUCCESS(f"✅ Barangay Metadata: {barangay_count}"))
            results['passed'] += 1
        
        return results
    
    def _test_validation(self, engine, results):
        """Test validation functions with known cases"""
        
        # Test cases: (project_type_code, zone_type, expected_allowed, description)
        test_cases = [
            # Roads should be allowed in all zones
            ('road', 'R1', True, 'Road/Highway in R1 (Low Density Residential)'),
            ('road', 'R3', True, 'Road/Highway in R3 (High Density Residential)'),
            ('road', 'C1', True, 'Road/Highway in C1 (Major Commercial)'),
            ('road', 'I1', True, 'Road/Highway in I1 (Heavy Industrial)'),
            
            # Residential buildings
            ('apartment_building', 'R3', True, 'Apartment Building in R3 (should be allowed)'),
            ('apartment_building', 'R2', True, 'Apartment Building in R2 (should be allowed)'),
            
            # Commercial
            ('shopping_mall', 'C1', True, 'Shopping Mall in C1 (should be allowed)'),
            ('retail_store', 'C1', True, 'Retail Store in C1 (should be allowed)'),
            ('retail_store', 'C2', True, 'Retail Store in C2 (should be allowed)'),
            
            # Industrial
            ('heavy_industrial', 'I1', True, 'Heavy Industrial in I1 (should be allowed)'),
            ('warehouse', 'I2', True, 'Warehouse in I2 (should be allowed)'),
            
            # Institutional
            ('school', 'In', True, 'School in Institutional zone (should be allowed)'),
            ('hospital', 'In', True, 'Hospital in Institutional zone (should be allowed)'),
        ]
        
        for project_type_code, zone_type, expected_allowed, description in test_cases:
            try:
                result = engine.validate_project_zone(project_type_code, zone_type)
                actual_allowed = result['is_allowed']
                
                if actual_allowed == expected_allowed:
                    self.stdout.write(self.style.SUCCESS(f"✅ PASS: {description}"))
                    results['passed'] += 1
                else:
                    self.stdout.write(self.style.ERROR(
                        f"❌ FAIL: {description}\n"
                        f"   Expected: {expected_allowed}, Got: {actual_allowed}\n"
                        f"   Message: {result['message']}"
                    ))
                    results['failed'] += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f"❌ ERROR: {description}\n"
                    f"   Exception: {str(e)}"
                ))
                results['failed'] += 1
        
        return results
    
    def _test_scoring(self, engine, results):
        """Test scoring accuracy"""
        
        test_cases = [
            # (project_type_code, zone_type, expected_zoning_score_min, description)
            ('road', 'R1', 90, 'Road in R1 - should have high zoning compliance'),
            ('road', 'C1', 90, 'Road in C1 - should have high zoning compliance'),
            ('apartment_building', 'R3', 90, 'Apartment in R3 - should have high zoning compliance'),
            ('shopping_mall', 'C1', 90, 'Shopping Mall in C1 - should have high zoning compliance'),
        ]
        
        for project_type_code, zone_type, expected_min, description in test_cases:
            try:
                scores = engine.calculate_mcda_score(project_type_code, zone_type)
                zoning_score = scores['zoning_compliance_score']
                
                if zoning_score >= expected_min:
                    self.stdout.write(self.style.SUCCESS(
                        f"✅ PASS: {description}\n"
                        f"   Zoning Compliance: {zoning_score:.1f}/100"
                    ))
                    results['passed'] += 1
                else:
                    self.stdout.write(self.style.WARNING(
                        f"⚠️  WARNING: {description}\n"
                        f"   Zoning Compliance: {zoning_score:.1f}/100 (expected: {expected_min}+)"
                    ))
                    results['warnings'] += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f"❌ ERROR: {description}\n"
                    f"   Exception: {str(e)}"
                ))
                results['failed'] += 1
        
        # Test overall score calculation
        try:
            scores = engine.calculate_mcda_score('road', 'R1')
            overall = scores['overall_score']
            
            # Overall score should be weighted sum (0-100)
            if 0 <= overall <= 100:
                self.stdout.write(self.style.SUCCESS(
                    f"✅ PASS: Overall score calculation\n"
                    f"   Score: {overall:.1f}/100 (valid range)"
                ))
                results['passed'] += 1
            else:
                self.stdout.write(self.style.ERROR(
                    f"❌ FAIL: Overall score out of range: {overall}"
                ))
                results['failed'] += 1
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ ERROR in score calculation: {str(e)}"))
            results['failed'] += 1
        
        return results
    
    def _test_recommendations(self, engine, results):
        """Test recommendation generation"""
        
        test_cases = [
            ('road', 'Road/Highway should have recommendations in all zones'),
            ('apartment_building', 'Apartment Building should have recommendations'),
            ('shopping_mall', 'Shopping Mall should have recommendations'),
        ]
        
        for project_type_code, description in test_cases:
            try:
                rec_result = engine.recommend_zones(project_type_code, limit=5)
                
                if rec_result['recommendations'] and len(rec_result['recommendations']) > 0:
                    rec_count = len(rec_result['recommendations'])
                    top_rec = rec_result['recommendations'][0]
                    
                    self.stdout.write(self.style.SUCCESS(
                        f"✅ PASS: {description}\n"
                        f"   Found {rec_count} recommendations\n"
                        f"   Top: {top_rec['zone_type']} (Score: {top_rec['overall_score']:.1f})"
                    ))
                    results['passed'] += 1
                    
                    # Verify top recommendation has valid scores
                    if top_rec['overall_score'] > 0 and top_rec['factor_scores']['zoning_compliance'] > 0:
                        self.stdout.write(self.style.SUCCESS(
                            f"   ✅ Top recommendation has valid scores"
                        ))
                        results['passed'] += 1
                    else:
                        self.stdout.write(self.style.WARNING(
                            f"   ⚠️  Top recommendation has low/invalid scores"
                        ))
                        results['warnings'] += 1
                else:
                    self.stdout.write(self.style.ERROR(
                        f"❌ FAIL: {description}\n"
                        f"   No recommendations returned!"
                    ))
                    results['failed'] += 1
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f"❌ ERROR: {description}\n"
                    f"   Exception: {str(e)}"
                ))
                results['failed'] += 1
        
        # Test with barangay (should improve accuracy)
        try:
            # Try to find a barangay with metadata
            barangay_with_meta = BarangayMetadata.objects.first()
            if barangay_with_meta:
                rec_result = engine.recommend_zones(
                    'road',
                    barangay=barangay_with_meta.name,
                    limit=3
                )
                
                if rec_result['recommendations']:
                    self.stdout.write(self.style.SUCCESS(
                        f"✅ PASS: Recommendations with barangay context\n"
                        f"   Barangay: {barangay_with_meta.name}\n"
                        f"   Recommendations: {len(rec_result['recommendations'])}"
                    ))
                    results['passed'] += 1
                else:
                    self.stdout.write(self.style.WARNING(
                        f"⚠️  WARNING: No recommendations with barangay context"
                    ))
                    results['warnings'] += 1
            else:
                self.stdout.write(self.style.WARNING(
                    "⚠️  SKIP: No barangay metadata available for testing"
                ))
        except Exception as e:
            self.stdout.write(self.style.WARNING(
                f"⚠️  WARNING: Error testing barangay context: {str(e)}"
            ))
            results['warnings'] += 1
        
        return results

