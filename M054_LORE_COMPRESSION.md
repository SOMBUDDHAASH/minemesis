# M0.5.4 ADDENDUM: Lore Compression Through Relational References & Symbolic IR

> **Architectural Design Document & Storage Projection**  
> **Status:** Proposal / Design Specification (Do Not Implement Immediately)  
> **Date:** October 25, 2026  
> **Domain:** Memory Management, Epistemic Normalization, Procedural Literature & Legends Mode  

---

## 1. Executive Summary & Motivation

In Milestone 0.5.4, we resolved the **Epistemic Explosion Bottleneck** by capping individual subjective belief formation ($\le 10$ witnesses per event) and routing background community perception into generalized `CollectiveKnowledge` vectors. This reduced 100-year active beliefs by **98.75%** (from $2,850,000$ down to $\sim 35,000$) and cut peak RAM across 500 simulated years to **$269.7\text{ MB}$**.

However, auditing the long-horizon memory profile (1,000 to 4,000 years) reveals the next major retention ceiling: **The Expanded Text Trap**.

The problem is **not encryption** (which is designed for cryptographic confidentiality and often inflates data size), but rather:
$$\text{Relational Normalization} + \text{Deduplication} + \text{Symbolic Intermediate Representation (Narrative IR)} + \text{Lazy Rendering}$$

Currently, whenever an event is logged, a book is penned, or a chronicle is updated, the engine serializes fully rendered English prose and redundant string identifiers into memory. For example:
- In a 100-year run with 10 settlements, **1,817 books** are written, storing **$6.43\text{ MB}$ of raw text strings** across pages, translating to **$\sim 22\text{ MB}$ of Python heap overhead**.
- The name `"Nessa Santosman"` is stored as an independent UTF-8 string **667 times** in event payloads alone.
- Every `Event` allocates a dictionary containing `"description"`, `"actor_name"`, `"target_name"`, and `"spouse1_name"`, duplicating strings already referenced by ID.

At 4,000 years, this naive storage strategy produces over **$260\text{ MB}$ of raw page strings** ($> 1\text{ GB}$ heap) in a small world, and over **$3.3\text{ GB}$** in a standard 30-settlement world.

By shifting Minemesis from **Expanded Text Storage** to **Narrative IR / Lore Bytecode**, we store only immutable mathematical facts (entity IDs, event IDs, template IDs, vocabulary tokens) during simulation, generating human-readable prose **strictly on demand** when viewed in the Story Viewer, read in an in-game library, or exported to Minecraft JSON.

---

## 2. The Expanded Text Trap: Empirical Measurements

An empirical audit of an active 100-year, 10-settlement simulation (`Seed 42`) produced the following storage profile:

| Subsystem Component | Count / Frequency | Raw String Volume | Python Heap Footprint | Duplication Factor |
| :--- | :--- | :--- | :--- | :--- |
| **Book Pages (`pages: list[str]`)** | 1,817 books (8,420 pages) | $6,430.6\text{ KB}$ ($6.43\text{ MB}$) | $\sim 22.4\text{ MB}$ | High (standard formulas repeated) |
| **Event Payloads (`description`)** | 12,909 events | $436.0\text{ KB}$ | $\sim 1.8\text{ MB}$ | High (famine, marriage, birth prose) |
| **Payload Name Redundancy** | 18,440 name occurrences | $243.9\text{ KB}$ | $\sim 1.1\text{ MB}$ | Extreme (top names repeated 300–670x) |
| **Event Participants Dict** | 12,909 events | $310.0\text{ KB}$ | $\sim 1.4\text{ MB}$ | Role strings repeated (`"actor"`, `"target"`) |
| **Total Uncompressed Lore State** | — | **$7.42\text{ MB}$** | **$\sim 26.7\text{ MB}$** | **Baseline 100-Year Memory** |

### Top Duplicated Strings in Memory (100 Years)
1. `"Nessa Santosman"`: **667 occurrences**
2. `"Children of the Golden Stars"`: **568 occurrences**
3. `"Living Harmony Sanctuary"`: **426 occurrences**
4. `"Golden Stars Sanctuary"`: **380 occurrences**
5. `"Waystone of Ancestors"`: **372 occurrences**

In an un-normalized system, every mention allocates a string pointer and hash table entry. In a normalized relational system, every occurrence is a 4-byte integer `int32`.

---

## 3. The 7 Core Principles of Lore Compression

### Principle 1: Store Relational References (IDs), Not Strings
- **Current:**
  ```python
  payload = {
      "description": "Borin Ironwood accused Aran Stone of theft in Oakhaven",
      "actor_name": "Borin Ironwood",
      "target_name": "Aran Stone",
      "settlement_name": "Oakhaven"
  }
  ```
- **Normalized:**
  ```python
  event = Event(
      type=EventType.ACCUSATION,
      actor_id=182,
      target_id=77,
      location_id=0,
      payload_code=AccusationPayload(crime_id=CrimeType.THEFT)
  )
  ```
  Names are resolved from centralized entity tables (`CharacterTable`, `SettlementTable`) only at render time.

### Principle 2: Store Facts, Not Generated Sentences
The objective single source of truth is the **Event Log**. An event does not need a pre-rendered English description in RAM. The description:
$$\text{"Borin Ironwood passed away of old age at 64 years"}$$
is a pure, deterministic function of:
$$\text{Event}(type=\text{DEATH}, target=182, causes=[], payload=\{natural: \text{True}\})$$
Storing the text string is storing the result of a deterministic function instead of its inputs.

### Principle 3: Template-Based Lore Storage (Lore Bytecode)
Instead of storing:
> *"The renowned farmer Borin Ironwood taught grain storage methods that transformed the valley of Oakhaven."*

The system stores a lightweight symbolic tuple:
```python
LoreSentenceIR(
    template_id=41,        # ID pointing to "{actor} taught {skill} that transformed {location}."
    actor_id=182,
    location_id=0,
    slot_id=SkillType.GRAIN_STORAGE
)
```
- **Byte size of raw string:** $\sim 98\text{ bytes}$ (+ $56\text{ bytes}$ Python string header = $154\text{ bytes}$).
- **Byte size of `LoreSentenceIR`:** $4 \times \text{int32} = 16\text{ bytes}$ (an **$89.6\%$ reduction**).

### Principle 4: Books as Structured Documents (Narrative IR)
A book is not a list of pages containing paragraphs of text. A book is an **Intentional Compilation of Historical Facts** authored by a character:
```python
@dataclass(frozen=True)
class BookIR:
    id: int
    author_id: int
    genre_id: int
    creation_tick: int
    settlement_id: int
    perspective_bias: int            # Enum/flag for point-of-view distortion
    chapters: tuple[ChapterIR, ...]
```
Where each `ChapterIR` holds:
- `template_group_id`: integer identifying chapter layout (e.g., `FAMILY_PATRIARCH_PROLOGUE`, `BATTLE_ANNALS`).
- `source_event_ids`: tuple of event IDs cited by the author.
- `slot_overrides`: integer tokens representing author literacy and subjective spin.

### Principle 5: Centralized Entity Tables
All mutable and immutable entity names reside in dedicated tables indexed by dense integers:
1. `CharacterTable`: `id -> (first_name_id, last_name_id, sex, birth_tick, death_tick)`
2. `FamilyTable`: `id -> (name_id, founding_tick, founding_settlement_id)`
3. `SettlementTable`: `id -> (name_id, x, y, site_type)`
4. `ReligionTable`: `id -> (name_id, theology_type, founding_tick)`
5. `LexiconTable`: Global deduplicated string intern pool for all proper names and titles.

### Principle 6: Collective Knowledge References
Characters and books never replicate community consensus text. If a village believes House Blackwood is dishonorable, a book chapter cites `SettlementOpinion(set_0, fam_blackwood)`, rather than baking 50 paragraphs of local gossip into manuscript pages.

### Principle 7: Lazy Rendering
Prose is synthesized **on demand** and never retained permanently in simulation heap:
- **Story Viewer:** Renders only the active chapter/event being inspected.
- **Book Inspection / Library Reading:** Expands `BookIR` to paginated text on click.
- **Minecraft Written Book Export:** Serializes directly to JSON file/stream and frees buffer.
- **History Chronicle Export:** Streams markdown paragraphs to disk without holding full chronicle in RAM.

---

## 4. Architectural Data Models: Narrative IR Specification

```
+-----------------------------------------------------------------------+
|                         CENTRALIZED FACT TABLES                       |
|  CharacterTable  |  SettlementTable  |  ReligionTable  |  EventLog    |
+-----------------------------------------------------------------------+
                                    ^
                                    | references by integer ID
+-----------------------------------+-----------------------------------+
|                     NARRATIVE IR (LORE BYTECODE)                     |
|                                                                       |
|  BookIR:                                                              |
|    - id: int32                                                        |
|    - author_id: int32                                                 |
|    - genre_id: uint8                                                  |
|    - creation_tick: int32                                             |
|    - chapters: tuple[ChapterIR, ...]                                  |
|                                                                       |
|  ChapterIR:                                                           |
|    - template_id: uint16                                              |
|    - event_refs: tuple[int32, ...]                                    |
|    - entity_refs: tuple[int32, ...]                                   |
|    - token_slots: tuple[uint16, ...]                                  |
+-----------------------------------+-----------------------------------+
                                    |
                                    | on-demand expansion (Lazy)
                                    v
+-----------------------------------------------------------------------+
|                           LAZY RENDER ENGINE                          |
|  - In-game Library Reader: Expands ChapterIR -> Formatted Pages       |
|  - Minecraft Book Exporter: Streams JSON without heap retention       |
|  - Legends Mode: Renders event timeline summaries from EventLog facts  |
+-----------------------------------------------------------------------+
```

### Proposed Data Structures

```python
from dataclasses import dataclass
from typing import Tuple, Optional

@dataclass(frozen=True, slots=True)
class SentenceIR:
    template_id: int            # Index into GRAMMAR_TEMPLATES table
    subject_id: int             # Character or Settlement ID
    object_id: int              # Target Character, Settlement, or Event ID
    qualifier_id: int           # Vocabulary modifier index (e.g., literacy tier adjective)

@dataclass(frozen=True, slots=True)
class ChapterIR:
    chapter_type_id: int        # e.g., 1=LineageRoster, 2=FeudAccount, 3=Miracle
    title_template_id: int
    sentences: Tuple[SentenceIR, ...]
    cited_event_ids: Tuple[int, ...]

@dataclass(frozen=True, slots=True)
class BookIR:
    id: int
    author_id: int
    genre_id: int
    settlement_id: int
    creation_tick: int
    perspective_bias_id: int
    chapters: Tuple[ChapterIR, ...]
```

### On-Demand Rendering Engine

```python
class NarrativeRenderer:
    """
    Stateless deterministic text synthesizer.
    Reconstructs human-readable English from Narrative IR on demand.
    """
    def __init__(self, simulation: Simulation):
        self.sim = simulation
        self.vocab = VOCABULARY_REGISTRY
        self.templates = GRAMMAR_TEMPLATE_REGISTRY

    def render_sentence(self, s_ir: SentenceIR, seed: int) -> str:
        template = self.templates[s_ir.template_id]
        subj = self.sim.get_character_name(s_ir.subject_id)
        obj = self.sim.get_entity_name(s_ir.object_id)
        qualifier = self.vocab[s_ir.qualifier_id]
        return template.format(subject=subj, object=obj, modifier=qualifier)

    def render_book_pages(self, book_ir: BookIR, max_chars_per_page: int = 256) -> list[str]:
        full_text_blocks = []
        for ch in book_ir.chapters:
            sentences = [self.render_sentence(s, book_ir.creation_tick) for s in ch.sentences]
            full_text_blocks.append(" ".join(sentences))
        combined = "\n\n".join(full_text_blocks)
        return paginate_text(combined, max_chars_per_page=max_chars_per_page)
```

---

## 5. Storage Estimates & Quantitative Projections

### A. Per-Object Memory Weight Comparison

| Object Type | Current (Expanded Text) | Normalized (Narrative IR) | Absolute Reduction | Relative Savings |
| :--- | :--- | :--- | :--- | :--- |
| **Single Event** | $\sim 8,737\text{ B}$ (heap deep size) | $\sim 1,179\text{ B}$ | $-7,558\text{ B}$ | **$86.5\%$** |
| **Single Book (4–8 pages)** | $\sim 7,143\text{ B}$ (with string pages) | $\sim 1,616\text{ B}$ (symbolic IR) | $-5,527\text{ B}$ | **$77.4\%$** |
| **Character Name Reference** | $\sim 64\text{ B}$ (string + pointer) | $4\text{ B}$ (`int32` ID) | $-60\text{ B}$ | **$93.7\%$** |
| **Page Text Block** | $\sim 256\text{ B}$ (UTF-8 text) | $0\text{ B}$ (synthesized lazily) | $-256\text{ B}$ | **$100.0\%$** |

---

### B. Horizon Projections: 100 to 4,000 Simulated Years

Projections based on empirical M0.5.4 equilibrium demographic models ($N_{\text{living}} \approx 4,500$, annual event rate $\approx 240\text{/yr}$, annual book production $\approx 18\text{/yr}$ across 30 settlements):

#### 1. 100 Years (Benchmark Horizon)
- **Cumulative Events:** $\sim 24,000$
- **Cumulative Books:** $\sim 1,800$
- **Current Heap Allocation:** $\sim 35\text{ MB}$ (lore + event strings)
- **Narrative IR Heap Allocation:** $\sim 4.2\text{ MB}$
- **Net Memory Saved:** **$\sim 30.8\text{ MB}$ ($88.0\%$ reduction in lore storage)**

#### 2. 500 Years (Stability Horizon)
- **Cumulative Events:** $\sim 120,000$
- **Cumulative Books:** $\sim 9,000$
- **Current Heap Allocation:** $\sim 175\text{ MB}$ (lore + event strings)
- **Narrative IR Heap Allocation:** $\sim 21\text{ MB}$
- **Net Memory Saved:** **$\sim 154\text{ MB}$ ($88.0\%$ reduction in lore storage)**

#### 3. 1,000 Years (Millennium Horizon)
- **Cumulative Events:** $\sim 240,000$
- **Cumulative Books:** $\sim 18,000$
- **Current Heap Allocation:** $\sim 350\text{ MB}$
- **Narrative IR Heap Allocation:** $\sim 42\text{ MB}$
- **Net Memory Saved:** **$\sim 308\text{ MB}$**

#### 4. 4,000 Years (Civilization Horizon)
- **Cumulative Events:** $\sim 960,000$
- **Cumulative Books:** $\sim 72,000$
- **Current Heap Allocation:** **$1,400\text{ MB}\text{ -- }3,300\text{ MB}$ ($1.4\text{--}3.3\text{ GB}$)**
- **Narrative IR Heap Allocation:** **$168\text{ MB}$**
- **Net Memory Saved:** **$> 1.2\text{ GB}\text{ -- }3.1\text{ GB}$ ($88.0\%\text{--}92.5\%$ reduction)**

```
Lore & Event Storage Growth Over Time (MB)
  4000 MB +                                                     Current Expanded Text
          |                                                             /
  3000 MB +                                                            /
          |                                                           /
  2000 MB +                                                          /
          |                                                         /
  1000 MB +                                                        /
          |                                                       /
     0 MB +---+-------------------+-------------------+----------+-----------
             100y                500y               1000y      4000y
             (IR: 4.2 MB)     (IR: 21 MB)        (IR: 42 MB)  (IR: 168 MB)  <- Narrative IR
```

---

## 6. Compatibility & Synergy with M0.5.4 Architecture

| Existing Architecture Component | Interaction with Lore Compression | Compatibility Assessment |
| :--- | :--- | :--- |
| **`EventLog` & `Event`** | Removes `payload["description"]` and redundant `*_name` keys. Employs compact integer sub-payloads. | **100% Compatible:** Invariant validation and `CAUSE_GRAMMAR` operate strictly on event types, roles, and causes—never on description text. |
| **`CollectiveKnowledge`** | Lore references cite settlement and family opinion vectors directly rather than serializing village rumors. | **Full Synergy:** Reduces redundancy between literature and epistemic consensus. |
| **`RelationshipCache`** | Unaffected. Cache operates on `(source_id, target_id)` tuples. | **No impact.** |
| **Tiered Retention Policy** | Tier 2 dead characters already have `beliefs` and `memories` archived. Books written by or about them become compact `BookIR` tokens rather than uncompacted text pages. | **Critical Enabler:** Allows historical figures from 2,000 years ago to be remembered in books without consuming heap text. |
| **Determinism & Seeds** | Because procedural slot grammars use `KeyedRNG` keyed to `(seed, book_id, tick)`, rendering text on demand is **100% deterministic and byte-identical** every time. | **Mathematically Guaranteed:** Same seed + same BookIR = byte-identical English prose. |

---

## 7. Phased Implementation Roadmap (Future Sprint)

> [!IMPORTANT]
> As instructed, this architecture addendum is a **design specification**. Implementation will begin only upon formal user sign-off.

### Phase 1: Event Payload Normalization
- Strip pre-rendered `payload["description"]`, `payload["*_name"]` across all event emitters in `life_cycle.py`, `conflict.py`, and `religion_engine.py`.
- Implement `render_event_description(event, characters, settlements)` helper for logging, testing, and UI display.

### Phase 2: Central Entity Lexicon & ID Table
- Establish `minemesis/core/entity_table.py` with integer interning for first names, last names, settlement names, and holy site titles.

### Phase 3: Book Data Model Refactoring (`BookIR`)
- Refactor `minemesis/lore/lore_models.py`: replace `Book.pages: list[str]` with `BookIR.chapters: tuple[ChapterIR, ...]`.
- Update `minemesis/lore/lore_generators.py` to synthesize `ChapterIR` tokens instead of running `paginate_text()` into strings.

### Phase 4: Lazy Narrative Renderer
- Create `minemesis/lore/lore_renderer.py` implementing `render_book_text()` and `render_book_minecraft_json()`.
- Update Story Viewer and CLI exporters to invoke lazy rendering on demand.

---

## 8. Conclusion

Lore Compression through Relational References and Narrative IR transforms Minemesis from an engine that struggles under the weight of its own generated text into an **infinite procedural library**. 

By storing **facts and generative recipes** rather than **expanded prose**:
1. Memory overhead is decoupled from prose length.
2. A 4,000-year world with tens of thousands of books and a million events fits in **under $300\text{ MB}$ of total system RAM**.
3. Every villager retains the unbounded creative capacity to write books, compose memoirs, and record history without threatening simulation stability.

---
*End of Design Document.*
