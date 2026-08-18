"""Pure domain rules for party composition, guest identity hierarchy, and greeting labels."""

from __future__ import annotations


def resolve_client_display_name(
    role: str | None,
    customer_name: str | None,
    client_name: str | None = None,
    company_name: str | None = None,
) -> str:
    """Resolve the canonical display name on the quotation brochure.

    Rules:
    1. If B2C Traveller: uses customer_name directly (fallback: 'Valued Client').
    2. If B2B Advisor:
       - If client_name is provided: uses client_name (e.g. 'Mr. Alexander Vance').
       - Else: uses customer_name (Advisor's name).
    """
    is_advisor = (role or "").strip().lower() == "advisor"
    c_name = (client_name or "").strip()
    cust_name = (customer_name or "").strip()

    if is_advisor and c_name:
        return c_name
    return cust_name or "Valued Client"


def generate_party_label(
    adults: int | None,
    children: int | None = 0,
    customer_name: str | None = None,
    lang: str = "en",
    kid_ages: list[int] | None = None,
) -> str:
    """Generate a clean, localized party label for brochure headers and recap summaries.

    Examples:
    - EN: '2 Adults, 1 Child' or '2 Adults, 1 Child (age 8)' or 'Mr. David Jenkins & Party (2 Adults)'
    - VI: '2 Người lớn, 1 Trẻ em'
    - AR: '2 بالغين, 1 طفل'
    """
    safe_adults = adults if adults is not None and adults > 0 else 2
    safe_kids = children if children is not None and children > 0 else 0

    if lang == "vi":
        adult_str = f"{safe_adults} Người lớn"
        if safe_kids > 0:
            if kid_ages:
                ages_str = ", ".join(str(a) for a in kid_ages)
                kid_str = f"{safe_kids} Trẻ em ({ages_str} tuổi)"
            else:
                kid_str = f"{safe_kids} Trẻ em"
        else:
            kid_str = ""
        party_counts = ", ".join(p for p in [adult_str, kid_str] if p)
    elif lang == "ar":
        adult_str = f"{safe_adults} بالغ{'ين' if safe_adults > 1 else ''}"
        if safe_kids > 0:
            kid_word = "أطفال" if safe_kids > 1 else "طفل"
            kid_str = f"{safe_kids} {kid_word}"
        else:
            kid_str = ""
        party_counts = ", ".join(p for p in [adult_str, kid_str] if p)
    else:
        adult_str = f"{safe_adults} Adult{'s' if safe_adults > 1 else ''}"
        if safe_kids > 0:
            if kid_ages:
                ages_str = ", ".join(str(a) for a in kid_ages)
                kid_str = f"1 child (age {ages_str})" if safe_kids == 1 else f"{safe_kids} children (ages {ages_str})"
            else:
                kid_str = f"{safe_kids} Child{'ren' if safe_kids > 1 else ''}"
        else:
            kid_str = ""
        party_counts = ", ".join(p for p in [adult_str, kid_str] if p)

    name = (customer_name or "").strip()
    if name and party_counts:
        return f"{name} & Party ({party_counts})"
    if name:
        return name
    return party_counts


def infer_greeting_name(customer_name: str | None, lang: str = "en") -> str | None:
    """Generate personalized opening greeting for the brochure overview letter."""
    name = (customer_name or "").strip()
    if not name:
        return None

    name_lower = name.lower()
    if lang == "vi":
        if name_lower.startswith("kính gửi") or name_lower.startswith("thân gửi"):
            return name
        return f"Kính gửi {name}"
    elif lang == "ar":
        if name_lower.startswith("عزيزي") or name_lower.startswith("السيد"):
            return name
        return f"عزيزي {name}"

    if name_lower.startswith("dear "):
        return name
    return f"Dear {name}"
