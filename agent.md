README.md
Finite World Story Adventure
Architecture Freeze v1.0
Project Vision

This project is not a Minecraft clone.

This project is not a voxel survival game with smarter villagers.

This project is:

A finite-world civilization simulator rendered through a voxel sandbox.

The terrain is the stage.

The real game is the people.

The player's actions should not merely change blocks.

The player's actions should change relationships, politics, families, settlements, history, and ultimately the future of the world.

Core Thesis
Minecraft
+
Persistent Relationships
+
Civilization Simulation
+
Event-Sourced World State
+
Emergent Storytelling
=
Finite World Story Adventure

Design Goal

The player should eventually be able to say:

"I accidentally killed a villager during a raid. His son spent years hunting me because he believed it was murder. Later he learned the truth and eventually became an ally."

No quest designer wrote this.

No hardcoded story created this.

The simulation created it.

Architecture Rule #1
The Event Log Is Objective Reality

The Event Log is the single source of truth.

Everything else is a derived interpretation.

Example:

Reality:
Player accidentally killed Rowan.


The Event Log stores:

Rowan died.

Killer: Player

Intent: Accidental


The Event Log NEVER stores:

Player is evil.

Player murdered Rowan.

Rowan deserved it.


Those are interpretations.

Interpretations belong elsewhere.

Architecture Rule #2
Characters Never React To Reality

Characters react to:

What they perceive

What they believe

What they remember

What they feel


NOT to objective reality.

Core pipeline:

Event
↓
Perception
↓
Belief
↓
Memory
↓
Relationship
↓
Decision
↓
New Event


This loop creates stories.

World Architecture

There are two phases.

Phase 1: World Generation

Runs once.

Seed Engine
↓
Terrain Generation
↓
Resource Generation
↓
Civilization Generation
↓
Population Generation
↓
Historical Simulation


Output:

A world with history.

Phase 2: Runtime Simulation

Runs continuously.

All runtime systems operate against:

THE EVENT LOG


Everything reads and writes meaningful events.

Runtime Systems
Event Log

Objective reality.

Immutable.

Append-only.

No mutation.

No rewriting history.

Perception System

Converts reality into observations.

Questions:

Who witnessed the event?

How far away were they?

Could they see it?

Could they hear it?

Did someone tell them later?


Perception generates beliefs.

Important Rule

Uncertainty is NOT distortion.

Bad:

Low visibility

↓

Player killed guard

↓

Observer believes:
Guard attacked player


Good:

Low visibility

↓

Observer believes:
Something happened near the guard

Confidence: Low


Distortion comes from:

Bias

Relationships

Rumors

Politics

Retellings


Not random guessing.

Belief System

Tracks what characters think happened.

Characters act on beliefs.

Not reality.

Example:

Reality:

Accident


Belief:

Murder


This can create feuds.

Belief Structure
Belief
{
    Believer
    EventRef

    Source
    Witnessed
    Told
    Inferred

    BelievedFields

    Confidence

    TickAcquired
}

Memory System

Memories are emotional reactions to beliefs.

Not to events.

This distinction is critical.

Wrong:

Event
↓
Memory


Correct:

Event
↓
Belief
↓
Memory

Memory Structure
Memory
{
    Observer
    BeliefRef

    Emotion
    Intensity

    DecayRate
}


Different people react differently.

Example:

Guard dies.


Son:

Hatred


Wife:

Grief


Rival:

Relief


Same event.

Different memories.

Relationship System

Relationships are cached views.

Relationships are NEVER source of truth.

Relationships are computed from memories.

Example:

Trust

Fear

Respect

Hatred

Loyalty


Should evolve automatically as memories change.

Knowledge Propagation System

Responsible for:

Rumors

Gossip

Witness stories

Information spread


Knowledge moves through the world.

Not instantly.

Example:

Village A knows.

Village B hears rumor.

Village C hears nothing.

Politics System

Controls:

Alliances

Neutrality

Suspicion

Hostility

War


Inputs:

History

Relationships

Trade

Leadership

Resource pressure

Economy System

Controls:

Food

Trade

Production

Resource movement


Only major economic events become Event Log entries.

Warfare System

Controls:

Raids

Retaliation

Defense

Conquest

Peace Offers


Wars should emerge.

Never be scripted.

Event Schema

Events are objective reality.

Event
{
    id

    tick

    location

    type

    participants

    causes[]

    intent

    scale

    payload
}

Causes

Events may have multiple causes.

Example:

Civil War


Possible causes:

Famine

Chief Death

Long-Term Feud

Trade Collapse

Intent

Possible values:

Intentional

Accidental

SelfDefense

MilitaryAction


Intent is objective.

Beliefs may disagree with it.

Scale
Individual

Aggregate


Examples:

John dies.


Individual.

17 villagers died in famine.


Aggregate.

What Counts As An Event?

Not everything should be logged.

Question:

Could a character remember, discuss, blame, celebrate, fear, or tell someone about this?

If NO:

Normal state.


If YES:

Event.


Not Events:

Food tick

Ore count update

Grass growth

AI pathfinding


Events:

Birth

Death

Marriage

Trade Treaty

Raid

Peace

Village Founded

Wall Completed

Famine Begins

Historical Simulation Rules

The world exists before the player.

History should be simulated before gameplay begins.

Example:

Year 0
World Created

Year 6
Oak Village Founded

Year 12
Trade Route Created

Year 19
Chief Dies

Year 25
Blood Feud Begins

Year 41
Peace Treaty Signed


The player enters a living world.

Not a newly created one.

Fidelity Layers

The world operates at two resolutions.

Coarse Simulation

Used during long-term history generation.

Tracks:

Settlements

Factions

Leaders

Wars

Trade

Major Families

Fine Simulation

Used near player activity.

Tracks:

Named Characters

Schedules

Relationships

Families

Events

Critical Rule

Both systems must use:

THE SAME EVENT SCHEMA


History must remain continuous.

Character Persistence Rules

Not every villager should be fully simulated forever.

Tier 1 - Generated Population

Ordinary population.

Generated deterministically.

Derived from world state.

Exists mostly to populate settlements.

Tier 2 - Persistent Characters

Created or promoted when involved in notable events.

Examples:

Saved by player

Killed by player

Starts feud

Becomes leader

Starts war

Affected by major event


Once promoted:

Never disposable.

Historical Constraints

Coarse history constrains future detail.

Example:

History says:

Year 41

17 villagers died.


Later fine simulation must satisfy:

17 actual people existed.

17 actual people died.


Generated detail cannot contradict history.

Construction Interpretation Layer

Individual block placement is not meaningful.

The world should aggregate construction.

Example:

Player places 500 stone blocks.


Not an event.

System evaluates:

Defense score

Wall completeness

Protected area

Strategic value


If threshold crossed:

Village Defense Improved


Event emitted.

Only meaningful changes generate events.

Determinism Requirements

The same seed must generate:

The same map

The same history

The same initial world state


every time.

Requirements:

Deterministic execution

Fixed update order

No unordered iteration

Keyed randomness


Example:

Hash(
    WorldSeed,
    System,
    Entity,
    Tick
)


Avoid shared RNG state.

Narrative Director

Purpose:

Control pacing.

NOT storytelling.

Allowed Actions:

Raid frequency modifiers

Migration pressure

Threat pressure

Bandit activity

Environmental pressure


Forbidden Actions:

Create wars directly

Kill characters

Create stories

Force outcomes


Critical Rule:

Every Director intervention must be logged.

Example:

Director Action

Reason:
Low world tension

Action:
Bandit activity +20%


The Director must be auditable.

Milestone 0
Headless Prototype

No graphics.

No voxel rendering.

No pathfinding.

No crafting.

No combat simulation beyond events.

Requirements:

World
1 seed

2D map

3 settlements

~30 named characters

Families included

Core Systems
Event Log

Perception

Beliefs

Memory

Relationships

Gossip

Event Types

Only implement:

Birth

Death

Marriage

Trade

Raid

Feud Begins

Peace


Everything else waits.

History Printer

Given any event:

Print causal chain.


Example:

Peace Treaty
↓
Trade Route
↓
Marriage
↓
Old Feud
↓
Chief Death

Acceptance Criteria
1

Re-running the same seed must produce:

Byte-identical output.

2

Most major events should have causes.

Feuds should be traceable at least:

3+ steps backward.

3

At least one wrongful grudge should emerge from a false belief.

4

At least one feud should end in forgiveness or peace.

5

Across many seeds:

No total extinction.

No single faction world domination.


unless caused by an extreme seed.

Final Definition

This project is:

A deterministic, event-sourced civilization simulator inside a finite voxel world.

The Event Log records reality.

Perception creates observations.

Beliefs create understanding.

Memories create emotion.

Relationships create incentives.

Civilizations create conflict.

Conflict creates history.

History creates stories.

The player changes history.