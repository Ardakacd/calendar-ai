# Communication Protocol Summary

## Quick Answer

**NO** - Planner/Scheduling Agent should **NOT** pass the whole event.

**Only pass minimal fields**:
- `startDate`: datetime
- `endDate`: datetime (or `duration_minutes` to calculate)
- `exclude_event_id`: Optional[str] (for updates only)

---

## Visual Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Scheduling Agent                          │
│  Has: Full event data (title, startDate, endDate, etc.)     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Extracts only time info
                     │
                     ▼
         ┌───────────────────────────┐
         │  conflict_check_request   │
         │  {                        │
         │    startDate: datetime,    │
         │    endDate: datetime,     │
         │    duration_minutes: 60   │
         │  }                       │
         └───────────┬───────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Conflict Resolution Agent                      │
│  Receives: Only time information                           │
│  Uses: check_conflict tool                                  │
│  Returns: Conflict status + suggestions                    │
└────────────────────┬───────────────────────────────────────┘
                     │
                     │ Returns result
                     │
                     ▼
         ┌───────────────────────────┐
         │  conflict_check_result     │
         │  {                        │
         │    has_conflict: true,    │
         │    conflicting_events: [],│
         │    suggestions: [...]     │
         │  }                       │
         └───────────┬───────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Scheduling Agent                          │
│  Reads: Conflict result                                    │
│  Decides: Proceed, use suggestion, or ask user            │
└─────────────────────────────────────────────────────────────┘
```

---

## Example: Create Event

### Step 1: Scheduling Agent extracts event
```python
# Scheduling Agent has full event data
event_data = {
    "title": "Team Meeting",
    "startDate": "2025-03-20T14:00:00-05:00",
    "duration": 60,
    "location": "Conference Room A"
}
```

### Step 2: Scheduling Agent prepares conflict check request
```python
# Only extract what Conflict Resolution Agent needs
state['conflict_check_request'] = {
    "startDate": datetime.fromisoformat("2025-03-20T14:00:00-05:00"),
    "endDate": datetime.fromisoformat("2025-03-20T15:00:00-05:00"),
    "duration_minutes": 60
    # Note: NO title, NO location, NO full event object
}
```

### Step 3: Conflict Resolution Agent processes
```python
# Conflict Resolution Agent reads minimal request
request = state['conflict_check_request']
result = await check_conflict_tool.ainvoke({
    "startDate": request["startDate"],
    "endDate": request["endDate"]
})
```

### Step 4: Conflict Resolution Agent returns result
```python
state['conflict_check_result'] = {
    "has_conflict": True,
    "conflicting_events": [...],
    "suggestions": [...]
}
```

---

## Example: Update Event

### Step 1: Scheduling Agent prepares update
```python
# Scheduling Agent has update data
update_data = {
    "event_id": "existing-event-uuid",
    "startDate": "2025-03-20T14:00:00-05:00",  # New time
    "duration": 60
}
```

### Step 2: Scheduling Agent requests conflict check
```python
state['conflict_check_request'] = {
    "startDate": datetime.fromisoformat("2025-03-20T14:00:00-05:00"),
    "endDate": datetime.fromisoformat("2025-03-20T15:00:00-05:00"),
    "exclude_event_id": "existing-event-uuid",  # Important for updates!
    "duration_minutes": 60
}
```

### Step 3: Conflict Resolution Agent checks
```python
# Excludes the event being updated from conflict check
result = await check_conflict_tool.ainvoke({
    "startDate": request["startDate"],
    "endDate": request["endDate"],
    "exclude_event_id": request["exclude_event_id"]  # Exclude self
})
```

---

## Updated FlowState Fields

Add these to `FlowState`:

```python
class FlowState(TypedDict):
    # ... existing fields ...
    
    # Conflict Resolution
    conflict_check_request: Optional[dict] = {
        "startDate": datetime,
        "endDate": datetime,
        "duration_minutes": int,
        "exclude_event_id": Optional[str]  # For updates
    }
    
    conflict_check_result: Optional[dict] = {
        "has_conflict": bool,
        "conflicting_events": List[Event],
        "suggestions": List[dict],
        "recommendation": str
    }
    
    conflict_resolution_messages: Annotated[list[BaseMessage], add_messages]
```

---

## Why This Design?

### ✅ Benefits

1. **Efficiency**: Less data transfer
2. **Security**: Only necessary info shared
3. **Clarity**: Clear contract between agents
4. **Maintainability**: Easy to test and debug
5. **Flexibility**: Can extend without breaking changes

### ❌ If We Passed Whole Event

- Unnecessary data transfer
- Tight coupling between agents
- Harder to test (need full event objects)
- More complex state management

---

## Key Takeaway

**Conflict Resolution Agent only needs TIME information**:
- When: `startDate`, `endDate`
- How long: `duration_minutes`
- What to exclude: `exclude_event_id` (for updates)

**Everything else** (title, location, etc.) is **NOT needed** for conflict checking.
