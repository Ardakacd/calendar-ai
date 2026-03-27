# Communication Protocol: Planner/Scheduling Agent ↔ Conflict Resolution Agent

## Question: Does Planner Agent pass the whole event?

**Answer: NO** - Only pass the **minimal required fields**, not the entire event object.

## Why Not Pass the Whole Event?

1. **Efficiency**: Less data transfer, faster processing
2. **Security**: Principle of least privilege - only share what's needed
3. **Clarity**: Clear contract - agent only needs time information
4. **Flexibility**: Easier to extend without breaking changes

## What Conflict Resolution Agent Actually Needs

Looking at the tools:
- `check_conflict`: Needs `startDate`, `endDate`, `exclude_event_id` (optional)
- `suggest_alternative_times`: Needs `requested_startDate`, `requested_endDate`, `duration_minutes`

**Required Fields**:
- `startDate`: datetime
- `endDate`: datetime (or `duration_minutes` to calculate)
- `exclude_event_id`: Optional[str] (for updates only)

**NOT Needed**:
- `title`
- `location`
- `user_id` (already in context)
- `event_id` (for creates, not needed; for updates, use `exclude_event_id`)

## Communication Patterns

### Pattern 1: Via State (Current LangGraph Approach)

```python
# In FlowState, add conflict resolution fields:
class FlowState(TypedDict):
    # ... existing fields ...
    
    # Conflict resolution request
    conflict_check_request: Optional[dict] = {
        "startDate": datetime,
        "endDate": datetime,
        "exclude_event_id": Optional[str]  # For updates
    }
    
    # Conflict resolution response
    conflict_check_result: Optional[dict] = {
        "has_conflict": bool,
        "conflicting_events": List[Event],
        "suggestions": List[dict]
    }
```

**Flow**:
```
Scheduling Agent → Sets conflict_check_request in state
Conflict Resolution Agent → Reads request, checks conflicts, sets conflict_check_result
Scheduling Agent → Reads result, decides next step
```

### Pattern 2: Direct Function Call (Simpler)

```python
# Conflict Resolution Agent as a function
async def check_conflicts_for_event(
    startDate: datetime,
    endDate: datetime,
    user_id: int,
    exclude_event_id: Optional[str] = None
) -> dict:
    # Use tools to check and suggest
    ...
```

**Flow**:
```
Scheduling Agent → Calls conflict resolution function directly
Conflict Resolution Agent → Returns result
Scheduling Agent → Uses result
```

### Pattern 3: Message-Based (LLM Agents)

```python
# Conflict Resolution Agent receives message
message = {
    "type": "check_conflict",
    "data": {
        "startDate": "2025-03-20T14:00:00-05:00",
        "endDate": "2025-03-20T15:00:00-05:00",
        "exclude_event_id": None  # For updates
    }
}
```

## Recommended Approach: Minimal Payload via State

### For Create Operations

**Scheduling Agent sends**:
```python
state['conflict_check_request'] = {
    "startDate": datetime.fromisoformat("2025-03-20T14:00:00-05:00"),
    "endDate": datetime.fromisoformat("2025-03-20T15:00:00-05:00"),
    "exclude_event_id": None,
    "duration_minutes": 60  # For suggestions
}
```

**Conflict Resolution Agent returns**:
```python
state['conflict_check_result'] = {
    "has_conflict": True,
    "conflicting_events": [
        {
            "event_id": "...",
            "title": "Team Meeting",
            "startDate": "2025-03-20T14:00:00-05:00",
            "endDate": "2025-03-20T15:00:00-05:00"
        }
    ],
    "suggestions": [
        {
            "startDate": "2025-03-20T15:15:00-05:00",
            "endDate": "2025-03-20T16:15:00-05:00",
            "reason": "Available right after",
            "confidence": 0.9
        }
    ]
}
```

### For Update Operations

**Scheduling Agent sends**:
```python
state['conflict_check_request'] = {
    "startDate": datetime.fromisoformat("2025-03-20T14:00:00-05:00"),
    "endDate": datetime.fromisoformat("2025-03-20T15:00:00-05:00"),
    "exclude_event_id": "event-uuid-being-updated",  # Important!
    "duration_minutes": 60
}
```

## Updated FlowState

```python
class FlowState(TypedDict):
    # ... existing fields ...
    
    # Conflict Resolution
    conflict_check_request: Optional[dict]  # Minimal payload
    conflict_check_result: Optional[dict]   # Response
    conflict_resolution_messages: Annotated[list[BaseMessage], add_messages]
```

## Example: Create Event Flow

```
1. Planner Agent → Routes to Scheduling Agent
   State: { route: "create", input_text: "Meeting at 2 PM" }

2. Scheduling Agent → Extracts event details
   State: { 
     create_event_data: [{
       "title": "Meeting",
       "startDate": "2025-03-20T14:00:00-05:00",
       "duration": 60
     }]
   }

3. Scheduling Agent → Requests conflict check
   State: {
     conflict_check_request: {
       "startDate": "2025-03-20T14:00:00-05:00",
       "endDate": "2025-03-20T15:00:00-05:00",
       "duration_minutes": 60
     }
   }

4. Conflict Resolution Agent → Checks conflicts
   Uses: check_conflict tool
   State: {
     conflict_check_result: {
       "has_conflict": True,
       "suggestions": [...]
     }
   }

5. Scheduling Agent → Reads result, decides
   If no conflict: Proceed with create
   If conflict: Use suggestion or ask user
```

## Benefits of Minimal Payload

1. **Performance**: Less data to serialize/deserialize
2. **Security**: Only necessary information shared
3. **Maintainability**: Clear contract, easy to test
4. **Flexibility**: Can add fields without breaking existing code

## Summary

**Answer**: Planner/Scheduling Agent should pass **only**:
- `startDate`: datetime
- `endDate`: datetime (or `duration_minutes`)
- `exclude_event_id`: Optional[str] (for updates)

**NOT** the whole event object. This is more efficient, secure, and maintainable.
