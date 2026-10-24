"""
Religious Trait Knowledge Library for the Standalone Religion Engine (Milestone R0).

Core Philosophy:
- Stores reusable theological, ethical, and sociological TRAITS, NOT hardcoded religions.
- Every trait is inspired by historical and modern religious traditions across all world regions:
  * South Asia: Hinduism, Buddhism, Jainism, Sikhism, Ayyavazhi, Vedic Religion, Ajivika, Charvaka
  * Middle East & West Asia: Judaism, Christianity, Islam, Baháʼí, Zoroastrianism, Yazidism, Druze, Mandaeism, Manichaeism, Mesopotamian Religion, Canaanite Religion, Mithraism
  * East Asia: Taoism, Confucianism, Shinto, Tenrikyo, Falun Gong, Chinese Folk Religion, Korean Muism, Jeung San Do
  * Southeast Asia: Cao Dai, Hòa Hảo, Vietnamese Folk Religion, Balinese Hinduism
  * Africa: Ancient Egyptian Religion, Yoruba Religion, Akan Religion, Vodun, Dinka Religion, Serer Religion, Berber Traditional Religion, Kemetism
  * Europe: Greek Religion, Roman Religion, Norse Religion, Celtic Polytheism, Rodnovery, Druidry
  * Americas: Aztec Religion, Maya Religion, Inca Religion, Native American Church, Mapuche Religion
  * Oceania: Māori Religion, Dreaming Traditions, Hawaiian Religion, Samoan Traditional Religion
  * Modern Movements: Rastafari, Scientology, Wicca, Thelema, Spiritism, Unitarian Universalism
"""

from __future__ import annotations
from typing import Mapping, Sequence
from minemesis.religion.religion_models import ReligionTrait, TraitCategory


_ALL_TRAITS: list[ReligionTrait] = [
    # -------------------------------------------------------------------------
    # 1. COSMOLOGY
    # -------------------------------------------------------------------------
    ReligionTrait(
        id="monotheism",
        name="Singular Supreme Deity",
        category=TraitCategory.COSMOLOGY,
        description="Belief in an indivisible, transcendent creator god who governs all existence and natural law.",
        inspired_by=("Judaism", "Christianity", "Islam", "Baháʼí", "Zoroastrianism", "Ayyavazhi", "Sikhism", "Kemetism"),
        modifiers={"zeal_factor": 0.2, "doctrinal_rigidity": 0.25},
        incompatibilities=("polytheism", "animism_cosmology", "non_theistic_void"),
    ),
    ReligionTrait(
        id="polytheism",
        name="Pantheon of Distinct Deities",
        category=TraitCategory.COSMOLOGY,
        description="Veneration of multiple specialized divinities presiding over forces of nature, arts, war, and hearth.",
        inspired_by=("Greek Religion", "Roman Religion", "Norse Religion", "Celtic Polytheism", "Mesopotamian Religion", "Canaanite Religion", "Yoruba Religion", "Aztec Religion", "Balinese Hinduism", "Rodnovery"),
        modifiers={"cultural_syncretism": 0.3, "temple_dedication_bonus": 0.2},
        incompatibilities=("monotheism", "non_theistic_void", "dualism_cosmic_struggle"),
    ),
    ReligionTrait(
        id="ancestor_worship",
        name="Living Ancestral Presence",
        category=TraitCategory.COSMOLOGY,
        description="The departed spirits of ancestors actively guide, watch over, and reward or punish their descendants.",
        inspired_by=("Chinese Folk Religion", "Shinto", "Yoruba Religion", "Roman Religion", "Korean Muism", "Serer Religion", "Mapuche Religion", "Akan Religion"),
        modifiers={"family_loyalty_modifier": 0.35, "grudge_persistence_modifier": 0.3, "lineage_honor": 0.25},
        incompatibilities=(),
    ),
    ReligionTrait(
        id="animism_cosmology",
        name="Immanent Spirit Realm",
        category=TraitCategory.COSMOLOGY,
        description="All natural phenomena, rivers, trees, animals, and stones possess conscious spiritual essences (Kami, Wakan, Spirits).",
        inspired_by=("Shinto", "Vodun", "Māori Religion", "Dreaming Traditions", "Vietnamese Folk Religion", "Rodnovery", "Druidry", "Berber Traditional Religion"),
        modifiers={"nature_reverence": 0.3, "consumption_modifier": -0.05, "harmony_bias": 0.2},
        incompatibilities=("monotheism",),
    ),
    ReligionTrait(
        id="reincarnation",
        name="Cycle of Rebirth & Transmigration",
        category=TraitCategory.COSMOLOGY,
        description="Souls undergo continuous cycles of rebirth (Samsara), governed by the moral balance of actions across lifetimes.",
        inspired_by=("Hinduism", "Buddhism", "Jainism", "Druze", "Sikhism", "Cao Dai", "Spiritism", "Thelema"),
        modifiers={"patience_modifier": 0.25, "reconciliation_modifier": 0.2, "death_fear_reduction": 0.25},
        incompatibilities=("apocalyptic_judgment", "non_theistic_void"),
    ),
    ReligionTrait(
        id="cycle_of_ages",
        name="Eternal Cosmic Cycles",
        category=TraitCategory.COSMOLOGY,
        description="Time unfolds through repeating monumental world ages of creation, golden virtue, degeneration, and cathartic cosmic renewal.",
        inspired_by=("Hinduism", "Vedic Religion", "Aztec Religion", "Maya Religion", "Norse Religion", "Greek Religion", "Mithraism", "Jeung San Do"),
        modifiers={"crisis_resilience": 0.3, "fatalism_modifier": 0.15},
        incompatibilities=(),
    ),
    ReligionTrait(
        id="dualism_cosmic_struggle",
        name="Cosmic War of Light and Darkness",
        category=TraitCategory.COSMOLOGY,
        description="Existence is an absolute metaphysical battlefield between pure cosmic truth/light and deceptive darkness.",
        inspired_by=("Zoroastrianism", "Manichaeism", "Yazidism", "Mandaeism", "Mithraism", "Tenrikyo"),
        modifiers={"moral_zeal": 0.3, "compromise_penalty": -0.2, "revenge_modifier": 0.15},
        incompatibilities=("polytheism", "pantheism_harmony"),
    ),
    ReligionTrait(
        id="apocalyptic_judgment",
        name="Final Day of Divine Reckoning",
        category=TraitCategory.COSMOLOGY,
        description="History moves toward a decisive final hour where all mortal souls are judged by divine decree for eternity.",
        inspired_by=("Christianity", "Islam", "Judaism", "Ancient Egyptian Religion", "Zoroastrianism", "Falun Gong"),
        modifiers={"moral_adherence": 0.25, "apocalyptic_urgency": 0.3},
        incompatibilities=("reincarnation", "cycle_of_ages"),
    ),
    ReligionTrait(
        id="dreaming_cosmology",
        name="Eternal Dreaming Trackways",
        category=TraitCategory.COSMOLOGY,
        description="Creation is continuous; ancestral spirit beings forged songs, laws, and topography that mortals continually reenact.",
        inspired_by=("Dreaming Traditions", "Māori Religion", "Hawaiian Religion", "Samoan Traditional Religion"),
        modifiers={"sacred_land_bond": 0.4, "wanderlust_restriction": -0.15},
        incompatibilities=("monotheism",),
    ),
    ReligionTrait(
        id="non_theistic_void",
        name="Causal Impermanence & Void",
        category=TraitCategory.COSMOLOGY,
        description="Rejection of creator gods in favor of natural causality, interdependent origination, and ultimate metaphysical liberation.",
        inspired_by=("Buddhism", "Jainism", "Ajivika", "Charvaka", "Unitarian Universalism"),
        modifiers={"reconciliation_modifier": 0.2, "superstition_penalty": -0.3, "learning_bonus": 0.25},
        incompatibilities=("monotheism", "polytheism"),
    ),
    ReligionTrait(
        id="pantheism_harmony",
        name="Immanent Tao & Universal Balance",
        category=TraitCategory.COSMOLOGY,
        description="The cosmos is an organic, self-balancing whole governed by quiet cosmic currents that mortals should align with.",
        inspired_by=("Taoism", "Confucianism", "Wicca", "Spiritism", "Balinese Hinduism"),
        modifiers={"diplomacy_modifier": 0.25, "reconciliation_modifier": 0.2, "raid_modifier": -0.2},
        incompatibilities=("dualism_cosmic_struggle",),
    ),

    # -------------------------------------------------------------------------
    # 2. VIRTUES
    # -------------------------------------------------------------------------
    ReligionTrait(
        id="forgiveness_doctrine",
        name="Doctrine of Mercy & Forgiveness",
        category=TraitCategory.VIRTUES,
        description="Forgiving grievances and showing mercy to transgressors is the highest spiritual attainment.",
        inspired_by=("Christianity", "Buddhism", "Jainism", "Baháʼí", "Unitarian Universalism", "Tenrikyo"),
        modifiers={"reconciliation_modifier": 0.35, "revenge_modifier": -0.4, "grudge_persistence_modifier": -0.35},
        incompatibilities=("warrior_honor", "holy_war_zeal"),
    ),
    ReligionTrait(
        id="charity_obligation",
        name="Mandatory Almsgiving & Mutual Aid",
        category=TraitCategory.VIRTUES,
        description="Sharing wealth and feeding the starving is an absolute spiritual obligation binding all faithful.",
        inspired_by=("Islam", "Sikhism", "Christianity", "Judaism", "Cao Dai", "Hòa Hảo", "Tenrikyo"),
        modifiers={"aid_modifier": 0.4, "trade_cooperation_modifier": 0.25, "famine_sharing_bonus": 0.35},
        incompatibilities=(),
    ),
    ReligionTrait(
        id="ascetic_discipline",
        name="Ascetic Renunciation & Rigor",
        category=TraitCategory.VIRTUES,
        description="Purification through fasting, physical restraint, detachment from material luxury, and stoic labor.",
        inspired_by=("Jainism", "Ajivika", "Buddhism", "Christian Monasticism", "Hinduism", "Manichaeism", "Mandaeism"),
        modifiers={"consumption_modifier": -0.18, "discipline_bonus": 0.3, "wealth_lust_reduction": -0.25},
        incompatibilities=(),
    ),
    ReligionTrait(
        id="family_loyalty_piety",
        name="Filial Piety & Lineage Honor",
        category=TraitCategory.VIRTUES,
        description="Unwavering devotion to parents, kin, and marital obligations as the foundation of social harmony.",
        inspired_by=("Confucianism", "Roman Religion", "Chinese Folk Religion", "Shinto", "Serer Religion", "Korean Muism"),
        modifiers={"family_loyalty_modifier": 0.4, "marriage_loyalty_modifier": 0.3, "grudge_persistence_modifier": 0.2},
        incompatibilities=(),
    ),
    ReligionTrait(
        id="warrior_honor",
        name="Martial Valor & Heroic Feats",
        category=TraitCategory.VIRTUES,
        description="Glory in battle, courage in the face of peril, and dying with arms in hand ensure eternal remembrance.",
        inspired_by=("Norse Religion", "Roman Religion", "Aztec Religion", "Sikhism", "Greek Religion", "Māori Religion"),
        modifiers={"courage_modifier": 0.4, "raid_modifier": 0.3, "revenge_modifier": 0.25, "reconciliation_modifier": -0.2},
        incompatibilities=("strict_pacifism", "forgiveness_doctrine"),
    ),
    ReligionTrait(
        id="humility_and_meekness",
        name="Selfless Humility & Simplicity",
        category=TraitCategory.VIRTUES,
        description="Relinquishing pride and ambition; the humble and meek hold spiritual superiority over worldly rulers.",
        inspired_by=("Christianity", "Taoism", "Dinka Religion", "Tenrikyo", "Rastafari"),
        modifiers={"reconciliation_modifier": 0.2, "chief_ambition_penalty": -0.25, "diplomacy_modifier": 0.15},
        incompatibilities=("warrior_honor",),
    ),
    ReligionTrait(
        id="truth_and_learning",
        name="Sacred Scholarship & Inquiry",
        category=TraitCategory.VIRTUES,
        description="Study of holy scripture, debating philosophy, and seeking objective truth are sacred callings.",
        inspired_by=("Judaism", "Confucianism", "Charvaka", "Falun Gong", "Unitarian Universalism", "Scientology", "Baháʼí"),
        modifiers={"learning_modifier": 0.35, "gossip_distortion_reduction": -0.3, "revelation_speed": 0.25},
        incompatibilities=(),
    ),
    ReligionTrait(
        id="hospitality_sanctity",
        name="Sacred Covenant of Hospitality",
        category=TraitCategory.VIRTUES,
        description="Wayfarers, guests, and emissaries are protected by divine decree; harming a guest is an unforgivable sacrilege.",
        inspired_by=("Greek Religion", "Berber Traditional Religion", "Celtic Polytheism", "Samoan Traditional Religion", "Bedouin traditions"),
        modifiers={"diplomacy_modifier": 0.3, "trade_cooperation_modifier": 0.2, "migrant_acceptance": 0.25},
        incompatibilities=(),
    ),

    # -------------------------------------------------------------------------
    # 3. TABOOS
    # -------------------------------------------------------------------------
    ReligionTrait(
        id="taboo_murder",
        name="Sacred Sanctity of Life (Ahimsa)",
        category=TraitCategory.TABOOS,
        description="Taking a human life incurs terrible spiritual pollution or karmic retribution.",
        inspired_by=("Jainism", "Buddhism", "Christianity", "Judaism", "Islam", "Hòa Hảo"),
        modifiers={"murder_revulsion": 0.4, "revenge_modifier": -0.3, "violence_reduction": -0.25},
        incompatibilities=("warrior_honor", "holy_war_zeal"),
    ),
    ReligionTrait(
        id="taboo_food_restrictions",
        name="Dietary Purity Laws",
        category=TraitCategory.TABOOS,
        description="Strict dietary guidelines regarding forbidden animals, fasting cycles, or consecrated preparation (Halal, Kosher, Ital, Ahimsa vegetarianism).",
        inspired_by=("Judaism", "Islam", "Hinduism", "Jainism", "Rastafari", "Sikhism", "Mandaeism"),
        modifiers={"consumption_modifier": -0.05, "cultural_boundary": 0.2},
        incompatibilities=(),
    ),
    ReligionTrait(
        id="taboo_ancestor_dishonor",
        name="Prohibition of Ancestral Disrespect",
        category=TraitCategory.TABOOS,
        description="Neglecting ancestral rites, altering family names, or desecrating parentage incurs immediate clan shaming.",
        inspired_by=("Chinese Folk Religion", "Shinto", "Yoruba Religion", "Roman Religion", "Korean Muism", "Serer Religion"),
        modifiers={"grudge_persistence_modifier": 0.35, "family_loyalty_modifier": 0.25},
        incompatibilities=(),
    ),
    ReligionTrait(
        id="taboo_cowardice",
        name="Abomination of Cowardice",
        category=TraitCategory.TABOOS,
        description="Fleeing from danger, yielding without fight, or breaking rank brings unpardonable dishonor to one's entire kin.",
        inspired_by=("Norse Religion", "Aztec Religion", "Māori Religion", "Roman Religion", "Sikhism"),
        modifiers={"courage_modifier": 0.35, "raid_modifier": 0.2, "reconciliation_modifier": -0.2},
        incompatibilities=("strict_pacifism",),
    ),
    ReligionTrait(
        id="taboo_desecration_of_dead",
        name="Inviolability of Burial Rites",
        category=TraitCategory.TABOOS,
        description="Disturbing graves, withholding funeral rites, or denying fallen foes burial invites terrible curses.",
        inspired_by=("Ancient Egyptian Religion", "Greek Religion", "Native American Church", "Vodun", "Roman Religion", "Kemetism"),
        modifiers={"burial_care": 0.35, "feud_escalation_on_defilement": 0.4},
        incompatibilities=(),
    ),
    ReligionTrait(
        id="taboo_oath_breaking",
        name="Sacred Doom of Oath-Breakers",
        category=TraitCategory.TABOOS,
        description="Oaths sworn before the divine are irrevocable; oath-breakers are cast out from both society and the afterlife.",
        inspired_by=("Norse Religion", "Greek Religion", "Zoroastrianism", "Mithraism", "Roman Religion"),
        modifiers={"treaty_durability": 0.4, "trade_cooperation_modifier": 0.25},
        incompatibilities=(),
    ),

    # -------------------------------------------------------------------------
    # 4. SOCIAL STRUCTURES
    # -------------------------------------------------------------------------
    ReligionTrait(
        id="hierarchical_priesthood",
        name="Consecrated Priesthood Hierarchy",
        category=TraitCategory.SOCIAL_STRUCTURES,
        description="A formal, ordained caste of high priests and clergy who alone hold legitimate authority to administer sacraments and consecrate rites.",
        inspired_by=("Roman Religion", "Christianity", "Ancient Egyptian Religion", "Mesopotamian Religion", "Aztec Religion", "Balinese Hinduism", "Kemetism"),
        modifiers={"order_stability": 0.3, "reformation_resistance": 0.3, "clergy_influence": 0.35},
        incompatibilities=("lay_egalitarianism", "shamanic_mediators"),
    ),
    ReligionTrait(
        id="monastic_orders",
        name="Contemplative Monastic Communities",
        category=TraitCategory.SOCIAL_STRUCTURES,
        description="Monks and nuns living in cloistered communities dedicated to prayer, manuscript transcription, meditation, and quiet manual labor.",
        inspired_by=("Buddhism", "Jainism", "Christianity", "Taoism"),
        modifiers={"consumption_modifier": -0.1, "learning_modifier": 0.25, "diplomacy_modifier": 0.15},
        incompatibilities=(),
    ),
    ReligionTrait(
        id="shamanic_mediators",
        name="Spirit Shamans & Healers",
        category=TraitCategory.SOCIAL_STRUCTURES,
        description="Charismatic spiritual practitioners who enter altered trance states to negotiate with ancestors, cure sickness, and divine portents.",
        inspired_by=("Korean Muism", "Vodun", "Mapuche Religion", "Rodnovery", "Druidry", "Dinka Religion", "Native American Church"),
        modifiers={"healing_bonus": 0.3, "famine_guidance": 0.2, "divination_prestige": 0.25},
        incompatibilities=("hierarchical_priesthood",),
    ),
    ReligionTrait(
        id="prophetic_lineage",
        name="Charismatic Prophets & Messengers",
        category=TraitCategory.SOCIAL_STRUCTURES,
        description="Divine truth is periodically renewed through inspired prophets who deliver revelation directly from on high.",
        inspired_by=("Judaism", "Christianity", "Islam", "Baháʼí", "Cao Dai", "Jeung San Do", "Tenrikyo", "Rastafari"),
        modifiers={"schism_propensity": 0.25, "zeal_factor": 0.3, "conversion_speed": 0.25},
        incompatibilities=(),
    ),
    ReligionTrait(
        id="council_of_elders",
        name="Venerable Council of Elders",
        category=TraitCategory.SOCIAL_STRUCTURES,
        description="Moral and spiritual authority resides with the senior-most clan elders who interpret traditional lore and consensus.",
        inspired_by=("Māori Religion", "Serer Religion", "Akan Religion", "Dinka Religion", "Native American Church", "Confucianism"),
        modifiers={"succession_crisis_reduction": -0.3, "tradition_durability": 0.35},
        incompatibilities=(),
    ),
    ReligionTrait(
        id="lay_egalitarianism",
        name="Universal Priesthood of All Believers",
        category=TraitCategory.SOCIAL_STRUCTURES,
        description="Rejection of clerical hierarchies; every adherent possesses equal direct spiritual authority and communion.",
        inspired_by=("Sikhism", "Unitarian Universalism", "Early Islam", "Wicca", "Spiritism"),
        modifiers={"social_equality": 0.35, "reformation_speed": 0.25, "clergy_cost_reduction": 0.3},
        incompatibilities=("hierarchical_priesthood",),
    ),

    # -------------------------------------------------------------------------
    # 5. WARFARE VIEWS
    # -------------------------------------------------------------------------
    ReligionTrait(
        id="strict_pacifism",
        name="Absolute Non-Violence & Pacifism",
        category=TraitCategory.WARFARE_VIEWS,
        description="All warfare, raiding, and retaliatory violence are strictly forbidden under any circumstances.",
        inspired_by=("Jainism", "Buddhism", "Baháʼí", "Unitarian Universalism", "Tenrikyo"),
        modifiers={"raid_modifier": -0.8, "revenge_modifier": -0.6, "diplomacy_modifier": 0.4, "reconciliation_modifier": 0.35},
        incompatibilities=("holy_war_zeal", "warrior_tradition", "warrior_honor"),
    ),
    ReligionTrait(
        id="defensive_sanctity",
        name="Righteous Defense & Just War",
        category=TraitCategory.WARFARE_VIEWS,
        description="Violence is permitted solely to protect innocent lives, preserve holy ground, and defend kin against unprovoked assault.",
        inspired_by=("Sikhism", "Christianity", "Islam", "Judaism", "Balinese Hinduism"),
        modifiers={"defense_bonus": 0.35, "unprovoked_raid_penalty": -0.4, "retaliation_discipline": 0.2},
        incompatibilities=("strict_pacifism", "holy_war_zeal"),
    ),
    ReligionTrait(
        id="holy_war_zeal",
        name="Sacred Crusade & Holy War",
        category=TraitCategory.WARFARE_VIEWS,
        description="Military conquest against unbelievers and desecrators is an act of supreme devotion rewarded with divine glory.",
        inspired_by=("Christianity", "Islam", "Aztec Religion", "Canaanite Religion", "Mesopotamian Religion"),
        modifiers={"raid_modifier": 0.45, "courage_modifier": 0.3, "reconciliation_modifier": -0.3, "conversion_on_conquest": 0.35},
        incompatibilities=("strict_pacifism", "defensive_sanctity", "forgiveness_doctrine", "taboo_murder"),
    ),
    ReligionTrait(
        id="warrior_tradition",
        name="Sacred Warrior Cult",
        category=TraitCategory.WARFARE_VIEWS,
        description="Arms, martial prowess, and combat trials are the true measure of character, favored by the deities of war.",
        inspired_by=("Norse Religion", "Roman Religion", "Celtic Polytheism", "Māori Religion", "Aztec Religion", "Mithraism"),
        modifiers={"raid_modifier": 0.4, "courage_modifier": 0.35, "revenge_modifier": 0.25},
        incompatibilities=("strict_pacifism",),
    ),
    ReligionTrait(
        id="martyrdom_glory",
        name="Blessed Sanctity of Martyrdom",
        category=TraitCategory.WARFARE_VIEWS,
        description="Those who perish bearing witness to their faith or defending their brethren achieve instant sainthood and eternal paradise.",
        inspired_by=("Early Christianity", "Shia Islam", "Sikhism", "Aztec Religion", "Bábí/Baháʼí history"),
        modifiers={"courage_modifier": 0.4, "death_fear_reduction": 0.4, "saint_rate_on_death": 0.5},
        incompatibilities=(),
    ),

    # -------------------------------------------------------------------------
    # 6. FAMILY BELIEFS
    # -------------------------------------------------------------------------
    ReligionTrait(
        id="bloodline_sanctity",
        name="Sacred Bloodline Preservation",
        category=TraitCategory.FAMILY_BELIEFS,
        description="Lineage purity and inherited divine charisma require careful marital selection and reverence for patriarchal/matriarchal blood.",
        inspired_by=("Confucianism", "Shinto", "Judaism", "Ancient Egyptian Religion", "Druze"),
        modifiers={"dynastic_stability": 0.35, "marriage_loyalty_modifier": 0.3, "foreign_marriage_reluctance": -0.2},
        incompatibilities=(),
    ),
    ReligionTrait(
        id="monogamy_sacrament",
        name="Sacrament of Indissoluble Monogamy",
        category=TraitCategory.FAMILY_BELIEFS,
        description="Marriage is a sacred lifelong covenant between two individuals, sanctified by the divine and unbreakable.",
        inspired_by=("Christianity", "Roman Religion", "Unitarian Universalism", "Baháʼí"),
        modifiers={"marriage_loyalty_modifier": 0.4, "adultery_scandal_multiplier": 0.5},
        incompatibilities=("polygamy_tradition",),
    ),
    ReligionTrait(
        id="polygamy_tradition",
        name="Sanctified Plural Marriage",
        category=TraitCategory.FAMILY_BELIEFS,
        description="Taking multiple spouses is an honorable practice to expand the clan, care for war widows, and multiply offspring.",
        inspired_by=("Yoruba Religion", "Ancient Judaism", "Islam", "Mormon history", "Dinka Religion"),
        modifiers={"fertility_modifier": 0.25, "clan_expansion": 0.3},
        incompatibilities=("monogamy_sacrament",),
    ),
    ReligionTrait(
        id="ancestral_veneration",
        name="Kinship Communion with the Departed",
        category=TraitCategory.FAMILY_BELIEFS,
        description="Every home maintains an altar to venerate departed kin, seeking their blessings in all family affairs.",
        inspired_by=("Chinese Folk Religion", "Shinto", "Yoruba Religion", "Akan Religion", "Korean Muism", "Roman Religion"),
        modifiers={"family_loyalty_modifier": 0.35, "grudge_persistence_modifier": 0.25},
        incompatibilities=(),
    ),
    ReligionTrait(
        id="communal_childcare",
        name="Communal Kinship & Shared Childcare",
        category=TraitCategory.FAMILY_BELIEFS,
        description="Children are raised by the entire collective settlement rather than isolated nuclear households alone.",
        inspired_by=("Hawaiian Religion", "Samoan Traditional Religion", "Akan Religion", "Native American Church", "Kibbutz traditions"),
        modifiers={"communal_bond": 0.3, "orphan_resilience": 0.4},
        incompatibilities=(),
    ),

    # -------------------------------------------------------------------------
    # 7. SACRED GEOGRAPHY
    # -------------------------------------------------------------------------
    ReligionTrait(
        id="sacred_rivers",
        name="Veneration of Holy Waters & Rivers",
        category=TraitCategory.SACRED_GEOGRAPHY,
        description="Rivers are divine life-givers whose currents wash away spiritual impurity and sustain the cosmic cycle.",
        inspired_by=("Hinduism", "Ancient Egyptian Religion", "Mesopotamian Religion", "Yoruba Religion", "Mandaeism"),
        modifiers={"river_settlement_affinity": 0.35, "purification_bonus": 0.25},
        incompatibilities=(),
    ),
    ReligionTrait(
        id="sacred_mountains",
        name="Holy Peaks & Mountain Sanctuaries",
        category=TraitCategory.SACRED_GEOGRAPHY,
        description="Mountain summits are the thrones of gods, bridging mortal earth to celestial heavens.",
        inspired_by=("Shinto", "Greek Religion", "Inca Religion", "Taoism", "Mapuche Religion"),
        modifiers={"mountain_settlement_affinity": 0.35, "meditation_bonus": 0.25},
        incompatibilities=(),
    ),
    ReligionTrait(
        id="sacred_groves",
        name="Hallowed Forests & Tree Shrines",
        category=TraitCategory.SACRED_GEOGRAPHY,
        description="Ancient trees and deep woodlands are sanctuaries of the gods where felling wood without ritual permission is sacrilege.",
        inspired_by=("Celtic Polytheism", "Druidry", "Shinto", "Rodnovery", "Berber Traditional Religion"),
        modifiers={"forest_settlement_affinity": 0.35, "wood_preservation": 0.2},
        incompatibilities=(),
    ),
    ReligionTrait(
        id="pilgrimage_sites",
        name="Tradition of Holy Pilgrimages",
        category=TraitCategory.SACRED_GEOGRAPHY,
        description="Adherents undertake long physical journeys to sacred shrines, unifying distant communities and spreading faith.",
        inspired_by=("Islam", "Christianity", "Hinduism", "Buddhism", "Shinto", "Balinese Hinduism"),
        modifiers={"pilgrimage_propensity": 0.35, "cultural_diffusion": 0.3},
        incompatibilities=(),
    ),
    ReligionTrait(
        id="monumental_temples",
        name="Monumental Architecture & Megaliths",
        category=TraitCategory.SACRED_GEOGRAPHY,
        description="Faith is embodied in grand stone temples, monuments, and stone circles built by collective community labor.",
        inspired_by=("Ancient Egyptian Religion", "Mesopotamian Religion", "Greek Religion", "Aztec Religion", "Maya Religion", "Inca Religion"),
        modifiers={"civic_pride": 0.3, "wealth_into_faith": 0.25},
        incompatibilities=(),
    ),

    # -------------------------------------------------------------------------
    # 8. AFTERLIFE CONCEPTS
    # -------------------------------------------------------------------------
    ReligionTrait(
        id="paradise_and_underworld",
        name="Heavenly Paradise & Infernal Torment",
        category=TraitCategory.AFTERLIFE_CONCEPTS,
        description="Virtuous souls inherit garden paradises of joy, while unrepentant wicked souls plunge into subterranean torment.",
        inspired_by=("Christianity", "Islam", "Zoroastrianism", "Ancient Egyptian Religion", "Norse Religion", "Greek Religion"),
        modifiers={"moral_adherence": 0.3, "sin_guilt_multiplier": 0.25},
        incompatibilities=("oblivion_cessation", "karmic_transmigration"),
    ),
    ReligionTrait(
        id="karmic_transmigration",
        name="Karmic Reincarnation Ladder",
        category=TraitCategory.AFTERLIFE_CONCEPTS,
        description="The soul is repeatedly reborn as higher or lower beings according to the precise moral weight of deeds.",
        inspired_by=("Hinduism", "Buddhism", "Jainism", "Sikhism", "Spiritism", "Thelema"),
        modifiers={"reconciliation_modifier": 0.2, "moral_restraint": 0.25},
        incompatibilities=("paradise_and_underworld", "oblivion_cessation"),
    ),
    ReligionTrait(
        id="ancestral_spirit_communion",
        name="Abode of the Ancestral Shades",
        category=TraitCategory.AFTERLIFE_CONCEPTS,
        description="Souls cross into an unseen parallel spirit realm just beyond mortal sight, dining with ancestors and watching mortals.",
        inspired_by=("Yoruba Religion", "Shinto", "Native American Church", "Dreaming Traditions", "Vodun", "Serer Religion"),
        modifiers={"death_peace_bonus": 0.25, "family_loyalty_modifier": 0.25},
        incompatibilities=("oblivion_cessation",),
    ),
    ReligionTrait(
        id="oblivion_cessation",
        name="Mortal Extinction & Liberation",
        category=TraitCategory.AFTERLIFE_CONCEPTS,
        description="Death is the natural dissolution of material elements; there is no post-mortem judgment or consciousness.",
        inspired_by=("Charvaka", "Ajivika", "Early Hebrew Sheol", "Unitarian Universalism"),
        modifiers={"earthly_focus": 0.3, "superstition_penalty": -0.3},
        incompatibilities=("paradise_and_underworld", "karmic_transmigration", "ancestral_spirit_communion"),
    ),

    # -------------------------------------------------------------------------
    # 9. RITUALS
    # -------------------------------------------------------------------------
    ReligionTrait(
        id="ritual_fasting",
        name="Sacred Fasting Cycles",
        category=TraitCategory.RITUALS,
        description="Periodic abstention from nourishment during holy seasons cleanses the spirit and cultivates communal empathy.",
        inspired_by=("Islam", "Christianity", "Judaism", "Jainism", "Balinese Hinduism", "Baháʼí"),
        modifiers={"consumption_modifier": -0.12, "empathy_bonus": 0.2},
        incompatibilities=(),
    ),
    ReligionTrait(
        id="meditative_contemplation",
        name="Silent Meditation & Breathwork",
        category=TraitCategory.RITUALS,
        description="Inner stillness, seated contemplation, and breath control quiet passion and unveil the divine within.",
        inspired_by=("Buddhism", "Hinduism", "Taoism", "Thelema", "Scientology", "Falun Gong"),
        modifiers={"stress_resilience": 0.3, "reconciliation_modifier": 0.2, "consumption_modifier": -0.05},
        incompatibilities=(),
    ),
    ReligionTrait(
        id="purification_ablutions",
        name="Sacred Washing & Water Consecration",
        category=TraitCategory.RITUALS,
        description="Ritual immersion or washing in clean water cleanses spiritual blemish before entering holy ground.",
        inspired_by=("Islam", "Shinto", "Judaism", "Christianity", "Hinduism", "Mandaeism"),
        modifiers={"health_resilience": 0.15, "ritual_piety": 0.25},
        incompatibilities=(),
    ),
    ReligionTrait(
        id="sacred_ecstatic_dance",
        name="Ecstatic Sacred Dance & Music",
        category=TraitCategory.RITUALS,
        description="Communal rhythmic drumming, chanting, and trance-dance channel ancestral presence and divine ecstasy.",
        inspired_by=("Vodun", "Sufi Islam", "Hawaiian Religion", "Native American Church", "Balinese Hinduism", "Wicca"),
        modifiers={"communal_solidarity": 0.35, "conversion_magnetism": 0.25},
        incompatibilities=("ascetic_discipline",),
    ),
    ReligionTrait(
        id="vision_quest_divination",
        name="Vision Quests & Omen Reading",
        category=TraitCategory.RITUALS,
        description="Youth and leaders fast in solitude or cast sacred lots (Ifá, I Ching, Runes, Oracles) to discover divine guidance.",
        inspired_by=("Native American Church", "Korean Muism", "Yoruba Religion", "Greek Religion", "Norse Religion", "Druze"),
        modifiers={"insight_bonus": 0.3, "crisis_navigation": 0.25},
        incompatibilities=(),
    ),
]

_TRAITS_BY_ID: dict[str, ReligionTrait] = {t.id: t for t in _ALL_TRAITS}
ALL_RELIGION_TRAITS: dict[str, ReligionTrait] = _TRAITS_BY_ID
_TRAITS_BY_CATEGORY: dict[TraitCategory, list[ReligionTrait]] = {}
for _t in _ALL_TRAITS:
    _TRAITS_BY_CATEGORY.setdefault(_t.category, []).append(_t)


def get_trait(trait_id: str) -> ReligionTrait | None:
    """Lookup a trait by unique identifier."""
    return _TRAITS_BY_ID.get(trait_id)


def get_all_traits() -> list[ReligionTrait]:
    """Returns the complete library of all extracted religious traits."""
    return list(_ALL_TRAITS)


def get_traits_by_category(category: TraitCategory) -> list[ReligionTrait]:
    """Returns all traits belonging to a specific category."""
    return list(_TRAITS_BY_CATEGORY.get(category, []))


def are_traits_compatible(trait_a: ReligionTrait, trait_b: ReligionTrait) -> bool:
    """Checks mutual compatibility between two traits."""
    if trait_b.id in trait_a.incompatibilities:
        return False
    if trait_a.id in trait_b.incompatibilities:
        return False
    return True


def is_trait_set_coherent(traits: Sequence[ReligionTrait]) -> bool:
    """Returns True if all traits in the set are mutually compatible."""
    for i in range(len(traits)):
        for j in range(i + 1, len(traits)):
            if not are_traits_compatible(traits[i], traits[j]):
                return False
    return True
