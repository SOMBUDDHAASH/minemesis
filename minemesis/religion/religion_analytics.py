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
    CulturalProfile,
    LoreStage,
    Religion,
    ReligiousMyth,
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
    # Milestone R2.10 Additions:
    most_syncretic_religion: Optional[dict[str, Any]] = None
    most_diverse_culture: Optional[dict[str, Any]] = None
    most_isolated_culture: Optional[dict[str, Any]] = None
    largest_pilgrimage_network: Optional[dict[str, Any]] = None
    most_influential_myth: Optional[dict[str, Any]] = None
    most_culturally_mixed_settlement: Optional[dict[str, Any]] = None


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
    cultural_profiles: Optional[Mapping[str, CulturalProfile]] = None,
    myths: Optional[Sequence[ReligiousMyth]] = None,
) -> ReligiousAnalyticsReport:
    """Compiles the full analytics report for Milestones R1.10 and R2.10."""
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
            "ReligiousSyncretism", "DoctrinalBorrowing", "FolkTraditionAbsorbed",
            "LocalCustomCelebrated", "HolySiteElevated", "MythExchanged",
        }
        chronicle_entries = []
        for evt in event_log.all_events():
            if evt.type.value in religious_event_types:
                year = (evt.tick // 12) + 1
                month = (evt.tick % 12) + 1
                chronicle_entries.append(
                    f"Year {year:02d}, Month {month:02d} (Tick {evt.tick:04d}): [{evt.type.value}] at {evt.location} - {evt.payload.get('site_name') or evt.payload.get('sect_name') or evt.payload.get('custom_name') or evt.payload.get('title') or evt.payload.get('reason') or evt.type.value}"
                )
        report.history_chronicle = chronicle_entries

    # 11. Most Syncretic Religion (R2.10)
    syncretic_rels = [
        r for r in all_rels
        if len(r.syncretic_parents) > 0 or len(r.borrowed_traits) > 0 or len(r.absorbed_folk_traditions) > 0
    ]
    if syncretic_rels:
        most_sync = max(
            syncretic_rels,
            key=lambda r: (len(r.syncretic_parents) + len(r.borrowed_traits) + len(r.absorbed_folk_traditions), len(r.adherents))
        )
        report.most_syncretic_religion = {
            "id": most_sync.id,
            "name": most_sync.name,
            "syncretic_parents": len(most_sync.syncretic_parents),
            "borrowed_traits": len(most_sync.borrowed_traits),
            "absorbed_folk_traditions": len(most_sync.absorbed_folk_traditions),
            "adherents": len(most_sync.adherents),
        }
    elif all_rels:
        r0 = all_rels[0]
        report.most_syncretic_religion = {
            "id": r0.id,
            "name": r0.name,
            "syncretic_parents": 0,
            "borrowed_traits": 0,
            "absorbed_folk_traditions": 0,
            "adherents": len(r0.adherents),
        }

    # 12. Cultural Profile Analytics (R2.10)
    if cultural_profiles:
        div_scores = {
            s_id: len(cp.folk_traditions) + len(cp.local_customs) + len(cp.social_values)
            for s_id, cp in cultural_profiles.items()
        }
        if div_scores:
            best_div_s = max(div_scores, key=div_scores.get)
            report.most_diverse_culture = {
                "settlement_id": best_div_s,
                "traditions_and_customs": len(cultural_profiles[best_div_s].folk_traditions) + len(cultural_profiles[best_div_s].local_customs),
                "social_values": dict(cultural_profiles[best_div_s].social_values),
            }

        sorted_by_traditions = sorted(cultural_profiles.keys(), key=lambda s: len(cultural_profiles[s].folk_traditions))
        if sorted_by_traditions:
            iso_s = sorted_by_traditions[0]
            mix_s = sorted_by_traditions[-1]
            report.most_isolated_culture = {
                "settlement_id": iso_s,
                "folk_traditions": len(cultural_profiles[iso_s].folk_traditions),
            }
            report.most_culturally_mixed_settlement = {
                "settlement_id": mix_s,
                "folk_traditions": len(cultural_profiles[mix_s].folk_traditions),
            }

    # 13. Largest Pilgrimage Network (R2.10)
    if all_rels:
        best_network_rel = max(
            all_rels,
            key=lambda r: (len(r.holy_sites), sum(s.pilgrims_visited for s in r.holy_sites))
        )
        report.largest_pilgrimage_network = {
            "religion_id": best_network_rel.id,
            "religion_name": best_network_rel.name,
            "holy_sites_count": len(best_network_rel.holy_sites),
            "total_pilgrims_visited": sum(s.pilgrims_visited for s in best_network_rel.holy_sites),
            "sites": [s.name for s in best_network_rel.holy_sites],
        }

    # 14. Most Influential Myth (R2.10)
    all_myths_list: list[ReligiousMyth] = list(myths) if myths else []
    if not all_myths_list:
        for r in all_rels:
            all_myths_list.extend(r.myths)

    if all_myths_list:
        stage_rank = {
            LoreStage.CULTURE: 5,
            LoreStage.TRADITION: 4,
            LoreStage.MYTH: 3,
            LoreStage.LEGEND: 2,
            LoreStage.STORY: 1,
        }
        best_myth = max(all_myths_list, key=lambda m: (stage_rank.get(m.stage, 1), m.retellings))
        report.most_influential_myth = {
            "id": best_myth.myth_id,
            "title": f"The Tale of {best_myth.hero_name}",
            "stage": best_myth.stage.value,
            "transmissions": best_myth.retellings,
            "settlements_known": sorted(list(best_myth.known_by_settlements)),
        }

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
        f"- **Most Syncretic Faith:** {report.most_syncretic_religion['name'] if report.most_syncretic_religion else 'None'} ({report.most_syncretic_religion.get('borrowed_traits', 0) if report.most_syncretic_religion else 0} borrowed traits, {report.most_syncretic_religion.get('absorbed_folk_traditions', 0) if report.most_syncretic_religion else 0} absorbed folk traditions)",
        f"- **Most Diverse Culture:** {report.most_diverse_culture['settlement_id'] if report.most_diverse_culture else 'None'}",
        f"- **Most Isolated Culture:** {report.most_isolated_culture['settlement_id'] if report.most_isolated_culture else 'None'}",
        f"- **Largest Pilgrimage Network:** {report.largest_pilgrimage_network['religion_name'] if report.largest_pilgrimage_network else 'None'} ({report.largest_pilgrimage_network['holy_sites_count'] if report.largest_pilgrimage_network else 0} holy sites, {report.largest_pilgrimage_network['total_pilgrims_visited'] if report.largest_pilgrimage_network else 0} pilgrims)",
        f"- **Most Influential Myth:** {report.most_influential_myth['title'] if report.most_influential_myth else 'None'} (Stage: {report.most_influential_myth['stage'] if report.most_influential_myth else 'None'}, {report.most_influential_myth['transmissions'] if report.most_influential_myth else 0} transmissions)",
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
