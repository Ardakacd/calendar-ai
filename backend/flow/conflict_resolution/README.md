# Conflict Resolution Agent - Complete Analysis

## Overview

The Conflict Resolution Agent is responsible for detecting schedule conflicts and suggesting alternative meeting times. It acts as a specialized assistant to the Scheduling Agent, providing intelligent conflict analysis and resolution recommendations.

## Tools Required

### 1. `check_conflict`
**Purpose**: Check if a time slot conflicts with existing events

**Input**:
- `startDate`: datetime - Start time to check
- `endDate`: datetime - End time to check  
- `exclude_event_id`: Optional[str] - Event to exclude (for updates)

**Output**:
- `has_conflict`: bool - Whether conflicts exist
- `conflicting_events`: List[Event] - All conflicting events
- `conflict_count`: int - Number of conflicts
- `conflict_types`: List[str] - Types: "overlap", "exact_match", "adjacent"

**Key Features**:
- Returns ALL conflicts (not just first)
- Identifies conflict types
- Supports update operations (exclude_event_id)

**When to Use**: Before creating/updating events to verify availability

---

### 2. `find_free_slots`
**Purpose**: Find available time slots in a date range

**Input**:
- `startDate`: datetime - Start of search range
- `endDate`: datetime - End of search range
- `duration_minutes`: int - Required duration
- `preferred_times`: Optional[List[str]] - Preferred times (e.g., ["09:00", "14:00"])
- `buffer_minutes`: Optional[int] - Buffer between meetings (default: 15)

**Output**:
- `free_slots`: List[dict] - Available slots with:
  - `startDate`: datetime
  - `endDate`: datetime
  - `duration_minutes`: int
  - `quality_score`: float (0-1)

**Key Features**:
- Considers buffer time between meetings
- Respects working hours (9 AM - 5 PM)
- Ranks slots by quality score
- Can filter by preferred times

**When to Use**: When you need multiple options or searching a wide range

---

### 3. `suggest_alternative_times`
**Purpose**: Suggest best alternative times for a conflicting event

**Input**:
- `requested_startDate`: datetime - Original requested time
- `requested_endDate`: datetime - Original requested end time
- `duration_minutes`: int - Required duration
- `search_window_days`: Optional[int] - Days forward to search (default: 7)
- `max_suggestions`: Optional[int] - Max suggestions (default: 3)

**Output**:
- `suggestions`: List[dict] - Alternative times with:
  - `startDate`: datetime
  - `endDate`: datetime
  - `reason`: str - Why this time is good
  - `confidence`: float (0-1) - Quality score
- `original_time`: datetime - Original requested time
- `count`: int - Number of suggestions

**Key Features**:
- Searches forward from requested time
- Provides ranked suggestions
- Includes human-readable reasons
- Confidence scores for ranking

**When to Use**: **PRIMARY TOOL** - Use when conflicts are detected

---

## System Prompt Design

### Core Responsibilities
1. **Conflict Detection**: Identify when requested times conflict
2. **Analysis**: Understand conflict nature and severity
3. **Resolution**: Suggest practical alternatives
4. **Communication**: Provide clear, actionable feedback

### Key Principles
- **Proactive**: Always suggest solutions, not just detect problems
- **Intelligent**: Consider user preferences (working hours, buffer time)
- **Flexible**: Provide multiple options ranked by quality
- **Clear**: Communicate in user-friendly language

### User Preferences Considered
- **Working Hours**: 9 AM - 5 PM (default)
- **Buffer Time**: 15 minutes between meetings (default)
- **Preferred Times**: If user specifies preferred times
- **Lunch Hours**: Avoid 12 PM - 1 PM when possible
- **Time of Day**: Morning (9-12) and afternoon (14-16) preferred

### Quality Scoring Factors
- Time of day (morning/afternoon preferred)
- Proximity to requested time
- Within working hours
- Matches preferred times
- Avoids lunch hours

## Workflow

```
1. Scheduling Agent → Request conflict check
   Input: { startDate, endDate, duration, exclude_event_id }

2. Conflict Resolution Agent → Check conflicts
   Tool: check_conflict
   
3. If conflicts found:
   a. Analyze conflicts (count, types, severity)
   b. Suggest alternatives
      Tool: suggest_alternative_times
   c. Return structured response

4. If no conflicts:
   Return success immediately

5. Scheduling Agent receives:
   - Conflict status
   - Conflicting events
   - Alternative suggestions
   - Recommendation message
```

## Integration Points

### With Scheduling Agent
- **Called**: Before create/update operations
- **Receives**: Proposed event details
- **Returns**: Conflict status + suggestions
- **Decision**: Scheduling Agent decides next step

### With Database
- Uses `EventAdapter` for conflict checking
- Accesses user's calendar events
- Efficient queries (minimize database calls)

## Example Scenarios

### Scenario 1: No Conflict
```
Request: Create meeting at 2 PM tomorrow
Check: No conflicts
Response: ✅ Available, proceed
```

### Scenario 2: Single Conflict
```
Request: Create meeting at 2 PM tomorrow
Check: Conflicts with "Team Standup" (2-3 PM)
Suggestions:
  1. 3:15 PM (right after, confidence: 0.9)
  2. 10:00 AM (morning slot, confidence: 0.8)
Response: ⚠️ Conflict detected, here are alternatives
```

### Scenario 3: Multiple Conflicts
```
Request: Create meeting at 2 PM tomorrow
Check: Conflicts with 2 events
Suggestions:
  1. 4:00 PM (later in day, confidence: 0.85)
  2. Next day 2 PM (same time, confidence: 0.9)
Response: ⚠️ Multiple conflicts, best alternatives provided
```

## Implementation Status

✅ **Tools Created**:
- `check_conflict` - Enhanced conflict detection
- `find_free_slots` - Free slot finder
- `suggest_alternative_times` - Primary suggestion tool

✅ **System Prompt**: Complete with workflow and examples

⏳ **Next Steps**:
1. Create Conflict Resolution Agent node in LangGraph
2. Integrate with Scheduling Agent
3. Add user preference storage (working hours, preferred times)
4. Test with various conflict scenarios

## Files Created

1. `flow/tools/conflict_resolution_tools.py` - All three tools
2. `flow/conflict_resolution/system_prompt.py` - Agent prompt
3. `flow/conflict_resolution/analysis.md` - Design analysis
4. `flow/conflict_resolution/README.md` - This document

## Usage Example

```python
from flow.tools.conflict_resolution_tools import (
    check_conflict_tool_factory,
    suggest_alternative_times_tool_factory
)

# Create tools bound to user
user_id = 123
check_tool = check_conflict_tool_factory(user_id)
suggest_tool = suggest_alternative_times_tool_factory(user_id)

# Check conflict
result = await check_tool.ainvoke({
    "startDate": "2025-03-20T14:00:00-05:00",
    "endDate": "2025-03-20T15:00:00-05:00"
})

# If conflict, suggest alternatives
if result["has_conflict"]:
    suggestions = await suggest_tool.ainvoke({
        "requested_startDate": "2025-03-20T14:00:00-05:00",
        "requested_endDate": "2025-03-20T15:00:00-05:00",
        "duration_minutes": 60
    })
```
