# Optimizer Merge Analysis - Old vs New Codebase

**Date**: 2026-02-01
**Analysis By**: Claude Code
**Purpose**: Document differences between booking-opt-prod (7 months old) and booking-opt-latest (current) to plan merge strategy

---

## Executive Summary

The updated optimizer codebase includes **significant enhancements** to the minimum stays calculation logic and introduces a new feasibility solver for handling new reservations. This is **not a simple update** - it's a substantial enhancement with:

- **3 new Python files** (FeasibilitySolverRunner.py, InitialSolGenerator.py, RestrictionImpact.py)
- **Major changes** to SolverRunner.py (+45 lines, +32% increase)
- **Expanded data models** (ProblemData.py +60 lines, ProblemResult.py +52 lines)
- **New business logic** for minimum stays quality comparison

---

## Directory Structure Comparison

### Old Structure (booking-opt-prod)
```
booking-opt-prod/
├── Optimizer/
│   ├── Optimizer/                    <- Core optimizer (what we copied)
│   │   ├── Data/
│   │   ├── FixedPlanRestrictions/
│   │   ├── Models/
│   │   ├── SolverData/
│   │   ├── SolverRunner.py           (141 lines)
│   │   ├── InitialPlanSolverRunner.py (2560 bytes)
│   │   ├── RestrictionSolverRunner.py (3059 bytes)
│   │   └── main.py                   (GCP Pub/Sub)
│   └── OptimizerTests/
├── BackEnd/
└── TestJSON/
```

### New Structure (booking-opt-latest)
```
booking-opt-latest/
├── BookingOpt/                       <- Renamed from "Optimizer/Optimizer"
│   ├── Data/
│   ├── FixedPlanRestrictions/
│   ├── Models/
│   ├── SolverData/
│   ├── SolverRunner.py               (186 lines) **CHANGED**
│   ├── InitialPlanSolverRunner.py    (6543 bytes) **CHANGED**
│   ├── RestrictionSolverRunner.py    (2963 bytes) **CHANGED**
│   ├── FeasibilitySolverRunner.py    (10747 bytes) **NEW**
│   ├── InitialSolGenerator.py        (1258 bytes) **NEW**
│   └── main.py                       (FastAPI)
└── BookingOptTests/
```

### Our Current Structure (app/worker/optimizer)
```
app/worker/optimizer/                 <- Copied from old Optimizer/Optimizer
├── Data/
├── FixedPlanRestrictions/
├── Models/
├── SolverData/
├── SolverRunner.py                   (141 lines, with our relative import fixes)
├── InitialPlanSolverRunner.py
├── RestrictionSolverRunner.py
└── main.py                           (Not used - we call from worker.py)
```

---

## Key Changes in Core Files

### 1. SolverRunner.py (Main Entry Point)

**Size Change**: 141 lines → 186 lines (+45 lines, +32% increase)

**Critical Changes**:

1. **New Imports** (Lines 17-18):
   ```python
   import InitialSolGenerator as rsg                           # NEW
   from FixedPlanRestrictions.RestrictionImpact import RestrictionImpact  # NEW
   ```

2. **Feasibility Check** (Lines 38-42):
   ```python
   if initialRunner.SolverData.CurrentReservationsWithoutAssignedRoom < 1:
       succeeded, initAssignment = initialRunner.Run()
       fullyBookedDays = initialRunner.SolverData.FullyBookedDays
       minStart = initialRunner.SolverData.MinStart
   ```
   - Only runs optimization if all current reservations have assigned rooms

3. **Initial Plan Generation** (Line 58) - **KEY MINIMUM STAYS CHANGE**:
   ```python
   initialPlan, initialPlanGaps = rsg.Run(initialRunner.SolverData)
   ```
   - Calls new `InitialSolGenerator` module
   - Calculates gaps in the current plan (before optimization)
   - This is the baseline for comparing minimum stays quality

4. **Optimization Time Threshold** (Line 67):
   ```python
   # OLD: if result.InitialOptimizationTime < 5.0:
   # NEW: if result.InitialOptimizationTime < 0.1 and not problemData.RestrictionsForInitialPlan:
   ```
   - Much stricter threshold (5 seconds → 0.1 seconds)
   - Skips restriction solver if only calculating restrictions for initial plan

5. **Restriction Impact Tracking** (Lines 80-84):
   ```python
   avdCa, avdCd, avdMax = RestrictionImpact().GetAvoidedStays(finalRestrictions, initialRunner.SolverData)
   result.StaysAvoidedByCa = avdCa
   result.StaysAvoidedByCd = avdCd
   result.StaysAvoidedByMax = avdMax
   ```
   - Tracks how many potential stays were blocked by each restriction type

6. **RestrictionsOnly Mode** (Lines 97-99):
   ```python
   if problemData.RestrictionsOnly and initAssignment[s] == None:
       result.Message += "Cannot calculate restrictions when missing initial assignments."
       succeeded = False
   ```

7. **Group ID Tracking** (Line 108):
   ```python
   # OLD: Assignment(..., stay[1] - stay[0], adjGrp)
   # NEW: Assignment(..., stay[1] - stay[0], adjGrp, grpId = initialRunner.SolverData.IdDict[s])
   ```
   - Adds reservation ID to assignments

8. **Quality Comparison** (Lines 153-166) - **CRITICAL MINIMUM STAYS LOGIC**:
   ```python
   if initialPlan is not None:
       result.InitialPlan = initialPlan
       result.InitialMinStays = initialPlanGaps
       result.QualityComparison = {d : {"Initial":0, "Optimized":0} for d in range(1,problemData.MinStay + 1)}

       for d in result.InitialMinStays:
           if date.toordinal(date.fromisoformat(d)) in fullyBookedDays:
               continue
           if int(result.MinStays[d]) not in result.QualityComparison:
               result.QualityComparison[int(result.MinStays[d])] = {"Initial":0, "Optimized":0}
           if int(result.InitialMinStays[d]) not in result.QualityComparison:
               result.QualityComparison[int(result.InitialMinStays[d])] = {"Initial":0, "Optimized":0}
           result.QualityComparison[int(result.MinStays[d])]["Optimized"] += 1
           result.QualityComparison[int(result.InitialMinStays[d])]["Initial"] += 1
   ```
   - **This is the core business logic change**
   - Compares gaps before and after optimization
   - Creates histogram showing improvement in minimum stay distribution
   - Example: Shows how many days went from 1-night gaps to 3-night gaps

---

### 2. FeasibilitySolverRunner.py (NEW FILE)

**Purpose**: Handle optimization scenarios with new reservations (feasibility checking)

**Size**: 10,747 bytes (largest new file)

**Entry Point**:
```python
class FeasibilityRunner:
    def Run(self, problemJson, returnDict = True):
        # Checks if current plan is feasible
        # If infeasible, tries alternative assignments
        # Returns feasibility status + optimized restrictions
```

**Usage** (from main.py):
```python
if len(scn["NewReservations"]) > 0 and not restrOnly:
    runner = FeasibilityRunner()
    success, result = runner.Run(scn)
else:
    success, result = Runner.Run(scn)
```

**Impact on Our Integration**:
- Our current `worker.py` always calls `SolverRunner.Run()`
- We need to add logic to detect `NewReservations` and route to `FeasibilityRunner`

---

### 3. InitialSolGenerator.py (NEW FILE)

**Purpose**: Calculate minimum stay gaps in the initial (current) plan

**Size**: 1,258 bytes

**Function**:
```python
def Run(solverData):
    # Returns: (initialPlan, initialPlanGaps)
    # initialPlanGaps: dict of {date: gap_size_in_nights}
```

**Key Logic**:
- Analyzes current room assignments
- Identifies gaps between reservations
- Calculates minimum stay requirement for each gap
- This becomes the "before" baseline for quality comparison

---

### 4. RestrictionImpact.py (NEW FILE in FixedPlanRestrictions/)

**Purpose**: Analyze which restriction types blocked the most potential stays

**Method**:
```python
class RestrictionImpact:
    def GetAvoidedStays(finalRestrictions, solverData):
        # Returns: (staysAvoidedByCa, staysAvoidedByCd, staysAvoidedByMax)
```

**Restriction Types**:
- **Ca**: Closed Arrivals (can't arrive on this date)
- **Cd**: Closed Departures (can't depart on this date)
- **Max**: Maximum stay restrictions

---

### 5. Data Model Changes

#### ProblemData.py
**Size Change**: 116 → 176 lines (+60 lines, +52% increase)

**New Fields**:
- `NewReservations` - for feasibility checking
- `RestrictionsForInitialPlan` - flag for restriction-only mode
- `RestrictionsOnly` - another mode flag
- Additional validation logic

#### ProblemResult.py
**Size Change**: 131 → 183 lines (+52 lines, +40% increase)

**New Fields**:
- `InitialPlan` - baseline assignments before optimization
- `InitialMinStays` - gap distribution before optimization
- `QualityComparison` - histogram comparing before/after gap quality
- `StaysAvoidedByCa`, `StaysAvoidedByCd`, `StaysAvoidedByMax` - restriction impact stats
- `CurrentScheduleInfeasible` - feasibility flag
- `Message` - extended error/status messages

#### Assignment.py
**Size Change**: 16 → 18 lines (minor)

**New Parameter**:
- `grpId` - reservation ID for tracking

---

## Interface Compatibility Analysis

### Current Interface (What We Use)

```python
# app/worker/worker.py calls:
from optimizer import SolverRunner
success, result = SolverRunner.Run(optimization_params)
```

### New Interface Requirements

```python
# Need to add routing logic:
if "NewReservations" in optimization_params and len(optimization_params["NewReservations"]) > 0:
    from optimizer.FeasibilitySolverRunner import FeasibilityRunner
    runner = FeasibilityRunner()
    success, result = runner.Run(optimization_params)
else:
    from optimizer import SolverRunner
    success, result = SolverRunner.Run(optimization_params)
```

**Compatibility Assessment**: ✅ **Backward Compatible**
- Old interface (`SolverRunner.Run()`) still exists and works
- New features are additive (new runner, new output fields)
- Existing API requests will continue to work
- New API requests can include `NewReservations` to trigger new logic

---

## Merge Strategy

### Phase 1: Preparation ✅ (Current)
- [x] Analyze differences between old and new codebases
- [x] Document all changes
- [x] Identify breaking vs. non-breaking changes

### Phase 2: File Replacement
**Action**: Copy updated optimizer files to `app/worker/optimizer/`

**Files to Replace** (keeping our relative import fixes):
1. `SolverRunner.py` - copy from new, reapply our import fixes
2. `InitialPlanSolverRunner.py` - copy from new
3. `RestrictionSolverRunner.py` - copy from new
4. **All Data/ files** - copy from new (ProblemData, ProblemResult, Assignment, etc.)
5. **All FixedPlanRestrictions/ files** - copy from new (includes RestrictionImpact.py)
6. **All Models/ files** - copy from new
7. **All SolverData/ files** - copy from new

**New Files to Add**:
1. `FeasibilitySolverRunner.py` - NEW
2. `InitialSolGenerator.py` - NEW

**Files to Skip**:
- `main.py` - we don't use this (we call from worker.py)

### Phase 3: Worker Integration
**File**: `app/worker/worker.py`

**Current Code**:
```python
def run_optimization_task(hotel_id: str, optimization_params: dict[str, Any], user_id: str = None) -> dict[str, Any]:
    try:
        from optimizer import SolverRunner
        success, result = SolverRunner.Run(optimization_params, returnDict=True)
        # ...
```

**Updated Code**:
```python
def run_optimization_task(hotel_id: str, optimization_params: dict[str, Any], user_id: str = None) -> dict[str, Any]:
    try:
        # Route to appropriate solver based on input
        if "NewReservations" in optimization_params and len(optimization_params.get("NewReservations", [])) > 0:
            from optimizer.FeasibilitySolverRunner import FeasibilityRunner
            runner = FeasibilityRunner()
            success, result = runner.Run(optimization_params, returnDict=True)
        else:
            from optimizer import SolverRunner
            success, result = SolverRunner.Run(optimization_params, returnDict=True)
        # ... rest stays the same
```

### Phase 4: Testing
1. **Unit Tests** - should pass (no interface changes)
2. **Integration Tests** - run existing test cases
3. **New Test Cases** - test `NewReservations` scenarios
4. **Regression Testing** - verify old test data still works

### Phase 5: Validation
1. Compare results from old vs new optimizer on same input
2. Verify new output fields are populated correctly
3. Test quality comparison logic

---

## Risk Assessment

### Low Risk ✅
- SolverRunner.Run() signature unchanged (backward compatible)
- Additive changes (new files, new fields, new logic paths)
- Our import fixes are minimal and can be reapplied

### Medium Risk ⚠️
- Data model expansions (ProblemData, ProblemResult)
  - **Mitigation**: Old inputs should still work (new fields are optional)
- Changed optimization time threshold (5s → 0.1s)
  - **Impact**: May skip restriction solver more often
  - **Mitigation**: Test with actual workloads
- New minimum stay quality logic
  - **Impact**: Additional computation
  - **Mitigation**: Monitor performance

### High Risk ❌
- None identified - this is a well-designed backward-compatible update

---

## Our Required Changes Summary

### Files We Need to Modify
1. `app/worker/optimizer/` - replace entire directory with new BookingOpt/ contents
2. `app/worker/worker.py` - add routing logic for FeasibilityRunner
3. Test files - add test cases for NewReservations scenarios

### Files We Need to Preserve
1. Our relative import fixes in `SolverRunner.py` (changed absolute imports to relative)
2. Linting exclusions in `pyproject.toml` (optimizer still uses tabs)
3. Docker build configuration (unchanged)

### Dependencies
**Check if new dependencies needed**:
```bash
# Compare requirements
diff booking-opt-prod/Optimizer/requirements.txt booking-opt-latest/requirements.txt
```
(Need to check if this file exists and if new packages required)

---

## Testing Strategy

### Test Cases to Create

1. **Baseline Regression** - existing test data should produce same results
2. **New Reservations** - test FeasibilityRunner path
3. **Quality Comparison** - verify InitialMinStays vs MinStays comparison
4. **Restriction Impact** - verify StaysAvoidedBy* fields populated
5. **Performance** - ensure new logic doesn't slow down optimization

### Integration Test Updates

**Add to** `app/tests/test_integration.py`:
```python
def test_feasibility_with_new_reservations():
    """Test FeasibilityRunner path with NewReservations"""
    test_data = load_test_data("SampleInput_with_new_reservations.json")
    # Submit job, verify uses FeasibilityRunner
    # Check result includes feasibility status
    pass

def test_quality_comparison():
    """Test that QualityComparison field is populated"""
    test_data = load_test_data("SampleInput_3.json")
    # Submit job
    # Verify result["QualityComparison"] exists
    # Verify InitialMinStays vs MinStays comparison
    pass
```

---

## Timeline Estimate

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| File Replacement | Copy new optimizer files | 30 min |
| Import Fixes | Reapply relative imports | 15 min |
| Worker Integration | Update worker.py routing | 15 min |
| Docker Rebuild | Rebuild worker image | 10 min |
| Smoke Testing | Run existing integration tests | 15 min |
| New Test Cases | Write NewReservations tests | 1 hour |
| Validation | Compare old vs new results | 1 hour |
| Documentation | Update docs | 30 min |
| **Total** | | **~4 hours** |

---

## Questions for User

1. **Test Data**: Do you have test JSON files with `NewReservations` to test the FeasibilityRunner path?

2. **Backwards Compatibility**: Do we need to support both old and new optimizer versions during transition?

3. **Performance**: Is the stricter optimization time threshold (0.1s vs 5s) acceptable for your workloads?

4. **Validation**: Do you want to run parallel old/new optimizer comparison before fully switching?

---

## Next Steps

1. ✅ Analysis complete (this document)
2. ⏳ User review and questions answered
3. ⏳ Begin Phase 2: File replacement
4. ⏳ Update worker.py routing logic
5. ⏳ Rebuild Docker images
6. ⏳ Run integration tests
7. ⏳ Document changes in RESTART-INSTRUCTIONS.md

---

**Analysis Complete**: 2026-02-01
**Ready for User Review and Approval to Proceed**
