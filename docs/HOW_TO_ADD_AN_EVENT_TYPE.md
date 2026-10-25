# How to Add a New Event Type in Minemesis

Minemesis follows a strict causal architecture. When introducing a new event type into the simulation, it must be properly typed, narratable, and indexed across the database and viewer.

---

## 4-Step Guide

### Step 1: Add the Enum in `minemesis/core/types.py`
Add your new event type to the `EventType` enum:

```python
class EventType(str, Enum):
    # Existing types...
    EARTHQUAKE = "Earthquake"
```

---

### Step 2: Define Valid Causal Precedents in `minemesis/core/causal_grammar.py`
Every event type in Minemesis must declare its valid cause predecessors in `CAUSE_GRAMMAR`:

```python
CAUSE_GRAMMAR[EventType.EARTHQUAKE] = frozenset()  # Natural root event with no prior causes
# Or if caused by prior events:
CAUSE_GRAMMAR[EventType.RELIEF_EFFORT] = frozenset({EventType.EARTHQUAKE, EventType.FAMINE})
```

---

### Step 3: Add Narration Handler in `viewer/services/narration.py`
Use the `@register_narrator` decorator to define an English prose generator for the event:

```python
from viewer.services.narration import register_narrator, _get_participant_name

@register_narrator("Earthquake")
def _narrate_earthquake(evt: dict[str, Any], participants: list[dict[str, Any]]) -> str:
    loc = evt.get("description", "the region")
    severity = evt.get("importance", 1.0)
    mag_desc = "violent" if severity >= 2.0 else "mild"
    return f"A {mag_desc} earthquake shook {loc}, rattling foundations."
```

*(Note: Even if you omit Step 3, the viewer's fallback system guarantees the viewer will NEVER crash on unknown or novel event types).*

---

### Step 4: Emit the Event in Simulation Code
Log the event to `event_log`:

```python
event_log.append(
    tick=tick,
    location=settlement.id,
    event_type=EventType.EARTHQUAKE,
    participants={"settlement": settlement.id},
    causes=[],
    intent=Intent.ACCIDENTAL,
    scale=Scale.AGGREGATE,
    payload={"severity": 2.5},
)
```

The `RunDBWriter` will automatically stream the event, resolve participants with baked-in display names, index it into SQLite, and make it searchable and causal-traversable in Viewer V2!
