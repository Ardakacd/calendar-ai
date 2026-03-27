# Conflict Resolution Agent - Design Analysis

## Purpose
The Conflict Resolution Agent is responsible for:
1. Detecting schedule conflicts when creating/updating events
2. Analyzing conflicts and their impact
3. Suggesting alternative meeting times
4. Providing intelligent recommendations based on user preferences

## Current State Analysis

### Existing Functionality
- ✅ Basic conflict detection (`check_event_conflict` in adapter)
- ✅ Returns first conflicting event
- ❌ No alternative time suggestions
- ❌ No analysis of multiple conflicts
- ❌ No consideration of user preferences

### Limitations
- Only returns first conflict (not all conflicts)
- No free time slot detection
- No intelligent suggestions
- No buffer time consideration
- No working hours awareness

## Required Tools

### 1. `check_conflict`
**Purpose**: Check if a specific time slot conflicts with existing events

**Input**:
- `startDate`: datetime
- `endDate`: datetime
- `exclude_event_id`: Optional[str] (for updates)

**Output**:
- `has_conflict`: bool
- `conflicting_events`: List[Event] (all conflicts, not just first)
- `conflict_type`: str ("overlap", "exact_match", "adjacent")

**Why needed**: More detailed conflict information than current implementation

### 2. `find_free_slots`
**Purpose**: Find available time slots in a date range

**Input**:
- `startDate`: datetime (start of search range)
- `endDate`: datetime (end of search range)
- `duration_minutes`: int (required duration)
- `preferred_times`: Optional[List[str]] (e.g., ["09:00", "14:00"])
- `buffer_minutes`: Optional[int] (default: 15)

**Output**:
- `free_slots`: List[dict] with:
  - `startDate`: datetime
  - `endDate`: datetime
  - `quality_score`: float (0-1, based on preferences)

**Why needed**: To suggest alternative times proactively

### 3. `suggest_alternative_times`
**Purpose**: Suggest best alternative times for a conflicting event

**Input**:
- `requested_startDate`: datetime (original requested time)
- `requested_endDate`: datetime
- `duration_minutes`: int
- `search_window_days`: int (default: 7)
- `max_suggestions`: int (default: 3)

**Output**:
- `suggestions`: List[dict] with:
  - `startDate`: datetime
  - `endDate`: datetime
  - `reason`: str (why this time is good)
  - `confidence`: float (0-1)

**Why needed**: Main tool for conflict resolution - provides actionable alternatives

### 4. `analyze_conflicts`
**Purpose**: Analyze multiple conflicts and provide recommendations

**Input**:
- `conflicts`: List[Event] (all conflicting events)
- `requested_event`: dict (event trying to be created/updated)

**Output**:
- `analysis`: dict with:
  - `severity`: str ("low", "medium", "high")
  - `conflict_count`: int
  - `recommendations`: List[str]
  - `can_resolve`: bool

**Why needed**: Better understanding of conflict situations

## System Prompt Design

### Core Responsibilities
1. **Conflict Detection**: Identify when requested times conflict with existing events
2. **Analysis**: Understand the nature and severity of conflicts
3. **Resolution**: Suggest practical alternatives
4. **Communication**: Provide clear, actionable feedback to Scheduling Agent

### Key Principles
- **Proactive**: Don't just detect conflicts, suggest solutions
- **Intelligent**: Consider user preferences (working hours, buffer time)
- **Flexible**: Provide multiple options ranked by quality
- **Clear**: Communicate conflicts and solutions clearly

### User Preferences to Consider
- Working hours (default: 9 AM - 5 PM)
- Buffer time between meetings (default: 15 minutes)
- Preferred meeting times (if available)
- Avoid lunch hours (12 PM - 1 PM)
- Respect existing event priorities

### Communication Pattern
```
Scheduling Agent → Conflict Resolution Agent
  Input: { requested_time, duration, context }
  Output: { has_conflict, conflicts, suggestions, analysis }
```

## Integration Points

### With Scheduling Agent
- Called BEFORE create/update operations
- Receives: requested event details
- Returns: conflict status + suggestions
- Scheduling Agent decides: proceed, use suggestion, or ask user

### With Database
- Uses EventAdapter for conflict checking
- Needs access to user's calendar events
- Should be efficient (minimize queries)

## Implementation Considerations

### Performance
- Cache user's events for date range queries
- Batch conflict checks when possible
- Limit search window for suggestions

### User Experience
- Provide 2-3 best alternatives
- Rank by quality (preferred times, working hours)
- Explain why each suggestion is good

### Edge Cases
- No conflicts → return success immediately
- All times conflict → suggest next available day
- Multiple conflicts → prioritize most important
- Update operations → exclude current event from checks
