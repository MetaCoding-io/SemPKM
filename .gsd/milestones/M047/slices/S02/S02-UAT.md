# S02: PPV Ontology Expansion — PillarScore, GuidingPrinciples & Enriched Reviews — UAT

**Milestone:** M047
**Written:** 2026-04-04T23:45:37.654Z

## UAT: PPV Ontology Expansion

### Preconditions
- PPV model v2.0.0 installed (from S01)
- Backend running with triplestore accessible
- Access to workspace browser and admin portal

### Test 1: PillarScore SHACL Form Creation
1. Navigate to workspace, click "New Object"
2. Select type "Pillar Score" from type picker
3. **Expected:** SHACL form renders with 3 property groups: Basic (title, score, wentWell, needsAttention), Relationships (weeklyReview, pillar), Metadata (created)
4. Enter title "Week 1 - Health"
5. Set score to 8
6. **Expected:** Score field accepts integer 1-10 only. Values outside range show validation error.
7. Set score to 0 → **Expected:** SHACL validation error (sh:minInclusive 1)
8. Set score to 11 → **Expected:** SHACL validation error (sh:maxInclusive 10)
9. Set score back to 8, fill wentWell "Good sleep schedule", needsAttention "Need more exercise"
10. Link to existing Pillar and WeeklyReview objects via relationship fields
11. Save → **Expected:** Object created successfully, appears in explorer under Pillar Score type

### Test 2: GuidingPrinciples SHACL Form Creation
1. Click "New Object", select type "Guiding Principles"
2. **Expected:** SHACL form renders with 3 property groups: Basic (title, values, purpose, meaning, manifestation), Statement (foundationalStatement, guidingWord), Metadata (created)
3. Enter title "My Core Values", fill values "integrity, growth", purpose "serve others", meaning "continuous improvement"
4. Fill foundationalStatement "I choose growth over comfort", guidingWord "resilience"
5. Save → **Expected:** Object created, appears in explorer under Guiding Principles type

### Test 3: Enriched Weekly Review Fields
1. Open an existing WeeklyReview object (or create new)
2. **Expected:** Form shows new "Reflection" property group with fields: wins, challenges, supportingPriorities
3. Fill wins "Completed project X", challenges "Time management", supportingPriorities "Focus on deep work"
4. Save → **Expected:** All reflection fields persist and display on re-open

### Test 4: Enriched Monthly Review Fields
1. Open a MonthlyReview object
2. **Expected:** Reflection group shows: biggestWins, biggestChallenges, focusAreas, habitsToAdjust (after existing gratitude and learnedThisMonth fields)
3. Fill all 4 fields, save, re-open → **Expected:** Values persist

### Test 5: Enriched Quarterly Review Fields
1. Open a QuarterlyReview object
2. **Expected:** New Reflection group with 6 fields: accomplishments, disappointments, whatWorked, whatDidntWork, howToImprove, annualVisionNotes
3. Fill all 6 fields, save, re-open → **Expected:** Values persist

### Test 6: Enriched Yearly Review Fields
1. Open a YearlyReview object
2. **Expected:** New Reflection group with 2 fields: intentionWord, yearTheme
3. Fill both, save, re-open → **Expected:** Values persist

### Test 7: PillarScore Table ViewSpec
1. Navigate to Views in explorer
2. Open "Pillar Scores" view
3. **Expected:** Table renders with columns: title, score, pillarTitle, weekTitle, wentWell, needsAttention
4. **Expected:** Rows sorted by pillarTitle

### Test 8: Action Kanban ViewSpec
1. Open "Action Kanban" view
2. **Expected:** Kanban board renders with columns auto-detected from ActionItem's status sh:in enum values
3. **Expected:** Cards show title, draggable between columns

### Test 9: Project Kanban ViewSpec
1. Open "Project Kanban" view
2. **Expected:** Kanban board renders with columns from Project status enum
3. **Expected:** Cards show title, status, priority, progress

### Test 10: Actions by Context ViewSpec
1. Open "Actions by Context" view
2. **Expected:** Table renders with columns: title, status, priority, doDate, context, energy
3. **Expected:** Rows sorted by context

### Test 11: Manifest Icons
1. Open explorer, expand object type tree
2. **Expected:** PillarScore shows bar-chart-2 icon in amber (#f59e0b)
3. **Expected:** GuidingPrinciples shows heart-handshake icon in purple (#8b5cf6)

### Test 12: Offline Validation Suite
1. Run: `cd backend && .venv/bin/python -m pytest tests/test_ppv_ontology.py -v`
2. **Expected:** 99 tests pass, covering ontology classes, properties, shapes, constraints, PropertyGroups, ViewSpecs, rules, manifest, combined parse, and cross-references

### Edge Cases
- Creating PillarScore without required fields (title, score, pillar, weeklyReview) should show SHACL validation errors
- Score field should reject non-integer values
- GuidingPrinciples with only title (all optional fields empty) should save successfully
- Multiple PillarScores can reference the same Pillar but different WeeklyReviews
