# Zone Recommendation Verification Guide

This guide explains how to verify that zone recommendations are accurate and reliable.

## Quick Start

### 1. Verify System Status
Run the comprehensive verification command:

```bash
python manage.py verify_recommendations
```

This will check:
- ✅ Data completeness (project types, zone allowed uses, barangay metadata)
- ✅ Validation functions (tests known cases)
- ✅ Scoring accuracy (verifies scores are in expected ranges)
- ✅ Recommendation generation (ensures recommendations are returned)

**Expected Output:**
```
✅ Passed: 28+
❌ Failed: 0
Success Rate: 100.0%
✅ System is highly reliable!
```

### 2. Check Specific Data

#### View Zone Mappings for a Project Type
```bash
python manage.py check_zone_data --project-type road
```

Shows all zones where a project type is allowed, including:
- Primary vs conditional uses
- Restrictions (max density, max height)
- Conditions

#### View All Project Types in a Zone
```bash
python manage.py check_zone_data --zone R1
```

Shows all project types allowed in a specific zone.

#### View Summary
```bash
python manage.py check_zone_data
```

Shows overview of all project types and their zone mappings.

---

## What Makes Recommendations "Sure" (Reliable)?

### 1. **Complete ZoneAllowedUse Data** ✅
The system needs `ZoneAllowedUse` records that define which project types are allowed in each zone.

**Check:**
```python
# Django shell
from projeng.models import ZoneAllowedUse
print(f"Zone Allowed Uses: {ZoneAllowedUse.objects.count()}")
# Should be > 0
```

**Fix if missing:**
```bash
python manage.py populate_zone_allowed_uses
```

### 2. **Accurate Validation** ✅
The `validate_project_zone()` function should return correct results.

**Test example:**
```python
# Django shell
from projeng.zone_recommendation import ZoneCompatibilityEngine

engine = ZoneCompatibilityEngine()
result = engine.validate_project_zone('road', 'R1')

# Should return:
# {'is_allowed': True, 'is_primary': True, ...}
```

### 3. **Correct Scoring** ✅
Zoning compliance scores should match expectations:
- **100**: Primary use (fully allowed)
- **70**: Conditional use (requires permit)
- **0**: Not allowed

**Verify:**
```python
engine = ZoneCompatibilityEngine()
scores = engine.calculate_mcda_score('road', 'R1')
print(f"Zoning Compliance: {scores['zoning_compliance_score']}")
# Should be 100 for primary uses
```

### 4. **Complete Project Type Coverage** ✅
All project types should have zone mappings.

**Check:**
```bash
python manage.py check_zone_data
```

Look for project types marked with ❌ (no zones mapped).

---

## Verification Checklist

Run these checks to ensure recommendations are reliable:

- [ ] **Run verification command**: `python manage.py verify_recommendations`
  - [ ] Success rate ≥ 90%
  - [ ] No failures (failed = 0)

- [ ] **Check data completeness**:
  - [ ] ZoneAllowedUse count > 0
  - [ ] All project types have zone mappings
  - [ ] Road/Highway has 12 zones (all zones)

- [ ] **Test common cases**:
  - [ ] Road in R1 → Should be allowed (primary)
  - [ ] Road in C1 → Should be allowed (primary)
  - [ ] Apartment in R3 → Should be allowed
  - [ ] Shopping Mall in C1 → Should be allowed

- [ ] **Verify scoring**:
  - [ ] Primary uses score 100 for zoning compliance
  - [ ] Conditional uses score 70 for zoning compliance
  - [ ] Overall scores are between 0-100

- [ ] **Test recommendations**:
  - [ ] Selecting a project type shows recommendations
  - [ ] Top recommendation has valid scores
  - [ ] Recommendations are ranked correctly

---

## Troubleshooting

### Problem: "No zone recommendations available"

**Solution:**
1. Check if ZoneAllowedUse data exists:
   ```bash
   python manage.py check_zone_data
   ```
2. If missing, populate data:
   ```bash
   python manage.py populate_zone_allowed_uses
   ```
3. Verify specific project type:
   ```bash
   python manage.py check_zone_data --project-type road
   ```

### Problem: Recommendations seem wrong

**Solution:**
1. Run verification:
   ```bash
   python manage.py verify_recommendations
   ```
2. Check the specific project type and zone:
   ```bash
   python manage.py check_zone_data --project-type YOUR_PROJECT_TYPE
   ```
3. Verify against Tagum City Ordinance No. 45, S-2002
4. Update ZoneAllowedUse data if needed (via Django Admin)

### Problem: Low scores on valid combinations

**Solution:**
1. Check if it's marked as conditional:
   ```bash
   python manage.py check_zone_data --project-type YOUR_PROJECT_TYPE
   ```
2. Verify primary vs conditional flags in Django Admin
3. Check if barangay metadata exists (affects scoring)

---

## Manual Verification Process

For critical decisions, manually verify:

1. **Cross-reference with Ordinance**
   - Open Tagum City Ordinance No. 45, S-2002
   - Check if recommended zone is listed for project type
   - Verify conditions match (if any)

2. **Check Recommendation Details**
   - Look at factor scores breakdown
   - Review advantages and constraints
   - Verify primary vs conditional status

3. **Test Edge Cases**
   - Try project types that should NOT be allowed
   - Test conditional uses (should show warning)
   - Test with different barangays (should affect scores)

---

## Commands Summary

| Command | Purpose |
|---------|---------|
| `python manage.py verify_recommendations` | Comprehensive system verification |
| `python manage.py check_zone_data` | View data summary |
| `python manage.py check_zone_data --project-type CODE` | View zones for specific project type |
| `python manage.py check_zone_data --zone ZONE` | View project types for specific zone |
| `python manage.py populate_zone_allowed_uses` | Populate/update zone allowed uses |

---

## Expected Behavior

### When Working Correctly:
1. ✅ Selecting a project type shows recommendations automatically
2. ✅ Top recommendations have high zoning compliance scores (≥90)
3. ✅ Primary uses rank higher than conditional uses
4. ✅ Validation messages are accurate (allowed/not allowed)
5. ✅ Recommendations update when barangay is selected

### Red Flags:
- ❌ "No zone recommendations available" (data missing)
- ❌ Primary uses scoring <90 for zoning compliance
- ❌ Recommendations not appearing after selecting project type
- ❌ Validation showing "allowed" when it should be "not allowed"

---

## Confidence Indicators

The system provides these indicators of reliability:

1. **Data Completeness**: More zones mapped = higher confidence
2. **Score Magnitude**: Higher scores (≥80) = more confident
3. **Primary vs Conditional**: Primary uses = higher confidence
4. **Barangay Context**: With barangay metadata = better accuracy

Run `python manage.py verify_recommendations` to see overall system reliability score!

