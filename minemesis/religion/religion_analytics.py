"""
Religious Analytics and Historical Chronicle System (Milestone R1.10).

Computes comprehensive historical and demographic metrics for religions across the world:
- Largest Religion (by living adherents)
- Fastest Growing Religion (by recent conversions)
- Most Schismatic Religion (by child sects and reformations)
- Oldest Religion (by founding tick)
- Most Successful Heresy (schismatic offshoot with highest adherents)
- Most Canonized Saints
- Most Pilgrimages
- Religious Diversity Index (Simpson's Index: 1 - sum(p_i^2)) for each settlement
- Genealogical Family Trees for all faith lineages
- Year-by-Year Religious History Chronicle
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence
from minemesis.religion.religion_models import (
    CharacterFaith,
    Religion,
)


@dataclass
class ReligiousAnalyticsReport:
    largest_religion: Optional[dict[str, Any]] = None
    fastest_growing_religion: Optional[dict[str, Any]] = None
    most_schismatic_religion: Optional[dict[str, Any]] = None
    oldest_religion: Optional[dict[str, Any]] = None
    most_successful_heresy: Optional[dict[str, Any]] = None
    most_canonized_saints: Optional[dict[str, Any]] = None
    most_pilgrimages: Optional[dict[str, Any]] = None
    settlement_diversity_indices: dict[str, float] = field(default_factory=dict)
    family_trees: dict[str, str] = field(default_factory=dict)
    history_chronicle: list[str] = field(default_factory=list)


def format_religion_family_tree(
    religion_id: str,
    religions: Mapping[str, Religion],
    prefix: str = "",
    is_last: bool = True,
) -> str:
    """Recursively formats a religion's genealogical descent tree."""
    rel = religions.get(religion_id)
    if not rel:
        return ""

    branch = "`-- " if is_last else "|-- "
    status = " [Extinct]" if rel.is_extinct else f" [{len(rel.adherents)} adherents]"
    generation_label = f" (Gen {rel.generation})"
    lines = [f"{prefix}{branch}{rel.name}{generation_label}{status}"]

    new_prefix = prefix + ("    " if is_last else "|   ")
    children = sorted(rel.child_religion_ids)
    for i, child_id in enumerate(children):
        is_child_last = (i == len(children) - 1)
        lines.append(format_religion_family_tree(child_id, religions, new_prefix, is_child_last))

    return "\n".join(lines)


def calculate_settlement_diversity_index(
    settlement_id: str,
    settlement_characters: Sequence[Any],
    faiths: Mapping[str, CharacterFaith],
) -> float:
    """
    Computes Simpson's Diversity Index: D = 1 - sum(p_i^2).
    0.0 = completely homogeneous (monoculture).
    1.0 = maximally diverse.
    """
    living = [c for c in settlement_characters if c.alive and c.settlement_id == settlement_id]
    total = len(living)
    if total <= 1:
        return 0.0

    counts: dict[str, int] = {}
    for c in living:
        f = faiths.get(c.id)
        if f:
            counts[f.religion_id] = counts.get(f.religion_id, 0) + 1

    sum_p_sq = sum((count / total) ** 2 for count in counts.values())
    return round(1.0 - sum_p_sq, 3)


def generate_religious_analytics(
    religions: Mapping[str, Religion],
    faiths: Mapping[str, CharacterFaith],
    settlements: Mapping[str, Any],
    living_characters: Sequence[Any],
    event_log: Any = None,
    current_tick: int = 0,
) -> ReligiousAnalyticsReport:
    """Compiles the full analytics report for Milestone R1.10."""
    report = ReligiousAnalyticsReport()

    active_rels = [r for r in religions.values() if not r.is_extinct]
    all_rels = list(religions.values())

    # 1. Largest Religion
    if religions:
        rel_adherent_counts = {
            r.id: sum(1 for f in faiths.values() if f.religion_id == r.id)
            for r in all_rels
        }
        largest_id = max(rel_adherent_counts, key=rel_adherent_counts.get)
        l_rel = religions[largest_id]
        report.largest_religion = {
            "id": l_rel.id,
            "name": l_rel.name,
            "adherents": rel_adherent_counts[largest_id],
            "dominant_settlements": sorted(list(l_rel.dominant_settlements)),
        }

    # 2. Fastest Growing Religion (conversions in past 120 ticks)
    recent_tick_threshold = max(0, current_tick - 120)
    conversions_by_rel: dict[str, int] = {}
    for f in faiths.values():
        if f.conversion_tick >= recent_tick_threshold:
            conversions_by_rel[f.religion_id] = conversions_by_rel.get(f.religion_id, 0) + 1

    if conversions_by_rel:
        fastest_id = max(conversions_by_rel, key=conversions_by_rel.get)
        f_rel = religions.get(fastest_id)
        if f_rel:
            report.fastest_growing_religion = {
                "id": f_rel.id,
                "name": f_rel.name,
                "recent_converts": conversions_by_rel[fastest_id],
            }
    elif report.largest_religion:
        report.fastest_growing_religion = dict(report.largest_religion)

    # 3. Most Schismatic Religion
    if religions:
        most_schismatic = max(all_rels, key=lambda r: len(r.child_religion_ids) + len(r.schisms))
        report.most_schismatic_religion = {
            "id": most_schismatic.id,
            "name": most_schismatic.name,
            "child_sects": len(most_schismatic.child_religion_ids),
            "schism_count": len(most_schismatic.schisms),
        }

    # 4. Oldest Religion
    if religions:
        oldest = min(all_rels, key=lambda r: r.founded_tick)
        report.oldest_religion = {
            "id": oldest.id,
            "name": oldest.name,
            "founded_year": oldest.founded_year,
            "founded_tick": oldest.founded_tick,
            "generation": oldest.generation,
        }

    # 5. Most Successful Heresy (child religion with highest adherents)
    heresies = [r for r in all_rels if r.parent_religion_id is not None]
    if heresies:
        best_heresy = max(heresies, key=lambda r: len(r.adherents))
        parent = religions.get(best_heresy.parent_religion_id)
        report.most_successful_heresy = {
            "id": best_heresy.id,
            "name": best_heresy.name,
            "parent_name": parent.name if parent else best_heresy.parent_religion_id,
            "adherents": len(best_heresy.adherents),
            "dominant_settlements": sorted(list(best_heresy.dominant_settlements)),
        }

    # 6. Most Canonized Saints
    if religions:
        most_saints_rel = max(all_rels, key=lambda r: len(r.saints))
        report.most_canonized_saints = {
            "id": most_saints_rel.id,
            "name": most_saints_rel.name,
            "saints_count": len(most_saints_rel.saints),
            "saints_list": [s.title for s in most_saints_rel.saints[:5]],
        }

    # 7. Most Pilgrimages
    total_pilgrimages_by_rel: dict[str, int] = {}
    for f in faiths.values():
        total_pilgrimages_by_rel[f.religion_id] = total_pilgrimages_by_rel.get(f.religion_id, 0) + f.pilgrimages_completed

    if total_pilgrimages_by_rel:
        best_pilgrim_id = max(total_pilgrimages_by_rel, key=total_pilgrimages_by_rel.get)
        p_rel = religions.get(best_pilgrim_id)
        if p_rel:
            report.most_pilgrimages = {
                "id": p_rel.id,
                "name": p_rel.name,
                "total_pilgrimages": total_pilgrimages_by_rel[best_pilgrim_id],
            }

    # 8. Settlement Diversity Indices
    for s_id in sorted(settlements.keys()):
        report.settlement_diversity_indices[s_id] = calculate_settlement_diversity_index(
            settlement_id=s_id,
            settlement_characters=living_characters,
            faiths=faiths,
        )

    # 9. Religion Family Trees
    root_religions = [r for r in all_rels if r.parent_religion_id is None]
    for root in sorted(root_religions, key=lambda r: r.id):
        report.family_trees[root.name] = format_religion_family_tree(root.id, religions)

    # 10. History Chronicle from EventLog
    if event_log:
        religious_event_types = {
            "Conversion", "ReligiousReform", "ReligiousSchism", "SaintCanonized",
            "Pilgrimage", "HolySiteDiscovered", "HeresyDeclared", "SectReunification",
            "ReligiousRefugeeMigration", "GreatFigureEmergence", "MythRecorded",
        }
        chronicle_entries = []
        for evt in event_log.all_events():
            if evt.type.value in religious_event_types:
                year = (evt.tick // 12) + 1
                month = (evt.tick % 12) + 1
                chronicle_entries.append(
                    f"Year {year:02d}, Month {month:02d} (Tick {evt.tick:04d}): [{evt.type.value}] at {evt.location} - {evt.payload.get('site_name') or evt.payload.get('sect_name') or evt.payload.get('title') or evt.payload.get('reason') or evt.type.value}"
                )
        report.history_chronicle = chronicle_entries

    return report


def format_religious_analytics_summary(report: ReligiousAnalyticsReport) -> str:
    """Formats the analytics report into a publication-grade markdown summary."""
    lines = [
        "## Religious History & Analytics Report",
        "",
        "### Key Global Metrics",
        f"- **Largest Religion:** {report.largest_religion['name'] if report.largest_religion else 'None'} ({report.largest_religion['adherents'] if report.largest_religion else 0} adherents)",
        f"- **Fastest Growing Religion:** {report.fastest_growing_religion['name'] if report.fastest_growing_religion else 'None'}",
        f"- **Most Schismatic Faith:** {report.most_schismatic_religion['name'] if report.most_schismatic_religion else 'None'} ({report.most_schismatic_religion['child_sects'] if report.most_schismatic_religion else 0} offshoots)",
        f"- **Oldest Faith:** {report.oldest_religion['name'] if report.oldest_religion else 'None'} (Founded Year {report.oldest_religion['founded_year'] if report.oldest_religion else 1})",
        f"- **Most Successful Heresy:** {report.most_successful_heresy['name'] if report.most_successful_heresy else 'None'} (Descended from {report.most_successful_heresy['parent_name'] if report.most_successful_heresy else 'N/A'}, {report.most_successful_heresy['adherents'] if report.most_successful_heresy else 0} adherents)",
        f"- **Most Canonized Saints:** {report.most_canonized_saints['name'] if report.most_canonized_saints else 'None'} ({report.most_canonized_saints['saints_count'] if report.most_canonized_saints else 0} saints)",
        f"- **Most Pilgrimages Completed:** {report.most_pilgrimages['name'] if report.most_pilgrimages else 'None'} ({report.most_pilgrimages['total_pilgrimages'] if report.most_pilgrimages else 0} pilgrimages)",
        "",
        "### Settlement Religious Diversity Index (Simpson's Index: 0.0=Monoculture, 1.0=Max Diversity)",
    ]
    for s_id, score in sorted(report.settlement_diversity_indices.items()):
        lines.append(f"- **{s_id}:** {score:.3f}")

    lines.append("")
    lines.append("### Religion Family Trees (Genealogy)")
    for root_name, tree_str in report.family_trees.items():
        lines.append(f"```text\n{tree_str}\n```")

    if report.history_chronicle:
        lines.append("")
        lines.append(f"### Historical Religious Chronicle ({len(report.history_chronicle)} events recorded)")
        for entry in report.history_chronicle[:15]:
            lines.append(f"- {entry}")
        if len(report.history_chronicle) > 15:
            lines.append(f"- *... and {len(report.history_chronicle) - 15} additional religious milestones.*")

    return "\n".join(lines)
