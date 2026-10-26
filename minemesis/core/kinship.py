"""
Kinship and Dynasty Degree Calculation for Milestone 1.
Computes Degree 1 and Degree 2 kinship relationships against PersonStore.
"""

from __future__ import annotations
from typing import Optional, Set

from minemesis.core.person_store import PersonStore
from minemesis.models.character import Character


def get_parents(store: PersonStore, char: Character) -> list[str]:
    parents = []
    if char.father_id:
        parents.append(char.father_id)
    if char.mother_id:
        parents.append(char.mother_id)
    return parents


def get_full_siblings(store: PersonStore, char: Character) -> list[str]:
    if not char.father_id or not char.mother_id:
        return []
    father = store.get_person(char.father_id)
    mother = store.get_person(char.mother_id)
    if not father or not mother:
        return []

    # Intersection of father's and mother's children
    f_kids = set(father.children_ids)
    m_kids = set(mother.children_ids)
    full_sibs = f_kids.intersection(m_kids)
    full_sibs.discard(char.id)
    return sorted(full_sibs)


def get_half_siblings(store: PersonStore, char: Character) -> list[str]:
    f_kids = set()
    m_kids = set()
    if char.father_id:
        father = store.get_person(char.father_id)
        if father:
            f_kids = set(father.children_ids)
    if char.mother_id:
        mother = store.get_person(char.mother_id)
        if mother:
            m_kids = set(mother.children_ids)

    # Symmetric difference (children of father OR mother, but not both)
    half_sibs = f_kids.symmetric_difference(m_kids)
    half_sibs.discard(char.id)
    return sorted(half_sibs)


def kin_degree(store: PersonStore, char_a_id: str, char_b_id: str) -> Optional[int]:
    """
    Returns 1 if degree 1, 2 if degree 2, else None if degree > 2 or unrelated.
    Degree 1: Parents, Children, Spouse, Full Siblings.
    Degree 2: Grandparents, Grandchildren, Aunts/Uncles, Nieces/Nephews, Half-Siblings.
    """
    if char_a_id == char_b_id:
        return 0

    char_a = store.get_person(char_a_id)
    char_b = store.get_person(char_b_id)
    if not char_a or not char_b:
        return None

    # --- Check Degree 1 ---
    # Spouse
    if char_a.spouse_id == char_b.id or char_b.spouse_id == char_a.id:
        return 1

    # Parent / Child
    a_parents = get_parents(store, char_a)
    if char_b.id in a_parents:
        return 1
    if char_a.id in char_b.children_ids:
        return 1

    b_parents = get_parents(store, char_b)
    if char_a.id in b_parents:
        return 1
    if char_b.id in char_a.children_ids:
        return 1

    # Full Siblings
    a_full_sibs = get_full_siblings(store, char_a)
    if char_b.id in a_full_sibs:
        return 1

    # --- Check Degree 2 ---
    # Half-Siblings
    a_half_sibs = get_half_siblings(store, char_a)
    if char_b.id in a_half_sibs:
        return 2

    # Grandparents / Grandchildren
    for p_id in a_parents:
        p = store.get_person(p_id)
        if p and char_b.id in get_parents(store, p):
            return 2  # char_b is grandparent of char_a

    for p_id in b_parents:
        p = store.get_person(p_id)
        if p and char_a.id in get_parents(store, p):
            return 2  # char_a is grandparent of char_b

    # Aunts / Uncles & Nieces / Nephews
    # char_b is sibling of char_a's parent
    for p_id in a_parents:
        p = store.get_person(p_id)
        if p and char_b.id in get_full_siblings(store, p):
            return 2

    # char_a is sibling of char_b's parent
    for p_id in b_parents:
        p = store.get_person(p_id)
        if p and char_a.id in get_full_siblings(store, p):
            return 2

    return None


def get_kin_relation(store: PersonStore, char_a_id: str, char_b_id: str) -> str:
    """Returns human-readable kinship label between char_a and char_b."""
    if char_a_id == char_b_id:
        return "Self"

    char_a = store.get_person(char_a_id)
    char_b = store.get_person(char_b_id)
    if not char_a or not char_b:
        return "Unrelated"

    if char_a.spouse_id == char_b.id:
        return "Spouse"

    a_parents = get_parents(store, char_a)
    if char_b.id in a_parents:
        return "Parent"
    if char_b.id in char_a.children_ids:
        return "Child"

    if char_b.id in get_full_siblings(store, char_a):
        return "Sibling"

    if char_b.id in get_half_siblings(store, char_a):
        return "Half-Sibling"

    for p_id in a_parents:
        p = store.get_person(p_id)
        if p and char_b.id in get_parents(store, p):
            return "Grandparent"
        if p and char_b.id in get_full_siblings(store, p):
            return "Uncle/Aunt"

    b_parents = get_parents(store, char_b)
    for p_id in b_parents:
        p = store.get_person(p_id)
        if p and char_a.id in get_parents(store, p):
            return "Grandchild"
        if p and char_a.id in get_full_siblings(store, p):
            return "Nephew/Niece"

    return "Unrelated"


def get_kin_network(store: PersonStore, char_id: str, max_degree: int = 2) -> dict[str, int]:
    """
    Returns a mapping of {related_char_id: degree} for all kin up to max_degree.
    """
    char = store.get_person(char_id)
    if not char:
        return {}

    kin: dict[str, int] = {}

    # Degree 1
    deg1: set[str] = set()
    if char.spouse_id:
        deg1.add(char.spouse_id)
    deg1.update(get_parents(store, char))
    deg1.update(char.children_ids)
    deg1.update(get_full_siblings(store, char))

    for k_id in deg1:
        if k_id != char_id and store.get_person(k_id) is not None:
            kin[k_id] = 1

    if max_degree >= 2:
        deg2: set[str] = set()
        deg2.update(get_half_siblings(store, char))

        # Grandparents
        for p_id in get_parents(store, char):
            p = store.get_person(p_id)
            if p:
                deg2.update(get_parents(store, p))
                deg2.update(get_full_siblings(store, p))  # Aunts/Uncles

        # Grandchildren & Nieces/Nephews
        for c_id in char.children_ids:
            c = store.get_person(c_id)
            if c:
                deg2.update(c.children_ids)

        for s_id in get_full_siblings(store, char):
            s = store.get_person(s_id)
            if s:
                deg2.update(s.children_ids)

        for k_id in deg2:
            if k_id != char_id and k_id not in kin and store.get_person(k_id) is not None:
                kin[k_id] = 2

    return kin
