"""Pure deterministic parser for ingestion candidates (15.8). No I/O, no LLM calls.

The Extractor/Resolver agents (15.8 §1.6) never compute money, dates, or cancellation-policy
shapes themselves — they only emit verbatim ``*_text`` fields with a ``source_quote``. This
module is the ONLY place that turns those text fields into typed values: minor-unit amounts,
ISO dates / season windows, and the 15.1 cancellation-policy "shape A". Whenever a text field
is genuinely ambiguous, the functions here report that explicitly (``ambiguous=True`` +
``reason``) instead of guessing — callers turn that into an ``unresolved[]`` entry or a
blocking ``Clarification`` question. Zero fabricated tiers, zero guessed years, zero LLM math.
"""
from __future__ import annotations

import calendar
import re
from dataclasses import dataclass, field

from core.rules.pricing_rules import currency_divisor

# ---------------------------------------------------------------------------
# Amount parsing
# ---------------------------------------------------------------------------

SUPPORTED_INGEST_CURRENCIES: frozenset[str] = frozenset({"VND", "USD", "EUR"})

_CURRENCY_ALIASES: dict[str, str] = {
    "vnd": "VND",
    "vnđ": "VND",
    "đ": "VND",
    "d": "VND",
    "₫": "VND",
    "usd": "USD",
    "us$": "USD",
    "$": "USD",
    "eur": "EUR",
    "€": "EUR",
}

_AMBIGUOUS_AMOUNT_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\+\+\s*$"), "amount has a '++' suffix (service/tax charge not confirmed)"),
    (re.compile(r"\d\s*(tr|trieu|triệu)\b", re.I), "amount uses an abbreviated unit (e.g. 'tr'/'triệu') — exact digits unconfirmed"),
    (re.compile(r"\btừ\b|\bfrom\b", re.I), "amount is phrased as a starting/'from' price, not a fixed amount"),
    (re.compile(r"li[eê]n\s*h[eệ]|\bcontact\b|\bcall\s*us\b", re.I), "amount says 'contact us' — no numeric price given"),
    (re.compile(r"\bTBA\b|\bTBD\b", re.I), "amount is marked TBA/TBD"),
)

_NUMERIC_RE = re.compile(r"[0-9][0-9.,\s]*")

# A char class matching a Unicode *letter* only (not digit, not underscore) — used to build
# alias boundaries below. `\w` includes digits, so we exclude those explicitly.
_LETTER = r"[^\W\d_]"


def _build_alias_matchers() -> list[tuple[re.Pattern[str], str]]:
    """Longest alias first, so multi-char aliases (``usd``) are tried before a single-char
    one (``d``) can steal a match out of the middle of them. Purely-alphabetic aliases get a
    letter-boundary guard so ``d`` never matches inside ``usd``/``dollars``; symbol aliases
    (``$``, ``€``, ``₫``, ``us$``) are matched as plain substrings since they never appear
    embedded inside an unrelated word."""
    matchers: list[tuple[re.Pattern[str], str]] = []
    for alias, code in sorted(_CURRENCY_ALIASES.items(), key=lambda kv: len(kv[0]), reverse=True):
        if alias.isalpha():
            pattern = re.compile(rf"(?<!{_LETTER}){re.escape(alias)}(?!{_LETTER})")
        else:
            pattern = re.compile(re.escape(alias))
        matchers.append((pattern, code))
    return matchers


_ALIAS_MATCHERS = _build_alias_matchers()


@dataclass(frozen=True)
class ParsedAmount:
    minor_units: int | None
    currency: str | None
    ambiguous: bool
    reason: str | None = None
    # A percentage (e.g. a "giảm 5%" group discount or a "+10%" seasonal uplift) is not a
    # money amount at all — it has no currency and no minor-unit representation. Earlier this
    # was smuggled through minor_units/currency (minor_units=round(pct*100), currency="%"),
    # which violates every other branch's contract that `currency` is a real ISO code in
    # SUPPORTED_INGEST_CURRENCIES; a percent-worded price *line* (not a supplement) would then
    # silently persist as a real price of a few hundred minor units under a bogus "%" currency
    # instead of being rejected. Percent amounts now carry their own typed fields and leave
    # minor_units/currency both None, so any caller that still only understands money (like a
    # rate price line) correctly treats them as unresolved instead of committing garbage.
    is_percent: bool = False
    percent_value: float | None = None


def _detect_currency(amount_text: str, currency_text: str | None) -> str | None:
    for source in (currency_text, amount_text):
        if not source:
            continue
        normalized = source.strip().lower()
        if normalized in _CURRENCY_ALIASES:
            return _CURRENCY_ALIASES[normalized]
        for pattern, code in _ALIAS_MATCHERS:
            if pattern.search(normalized):
                return code
    return None


def _find_amount_token(amount_text: str) -> tuple[str | None, bool]:
    """Return (numeric_token, ambiguous). When ``amount_text`` contains more than one numeric
    group (e.g. a leading pax count — "2 pax: 500.000 VND"), pick the group with strictly more
    digit characters (the price, not the count); a tie (e.g. a "50.000 - 80.000" range) is
    reported ambiguous rather than silently taking whichever group happened to come first.
    """
    groups = [m.group(0).strip() for m in _NUMERIC_RE.finditer(amount_text)]
    groups = [g for g in groups if g]
    if not groups:
        return None, False
    if len(groups) == 1:
        return groups[0], False
    digit_counts = [sum(ch.isdigit() for ch in g) for g in groups]
    max_count = max(digit_counts)
    winners = [g for g, c in zip(groups, digit_counts) if c == max_count]
    if len(winners) == 1:
        return winners[0], False
    return None, True


def _split_numeric_groups(numeric: str) -> tuple[float | None, bool]:
    """Return (value, ambiguous) for a digits+separators token, deciding decimal vs thousands."""
    numeric = numeric.strip()
    has_dot = "." in numeric
    has_comma = "," in numeric

    if has_dot and has_comma:
        # Whichever separator appears LAST is the decimal separator.
        decimal_sep = "." if numeric.rfind(".") > numeric.rfind(",") else ","
        thousands_sep = "," if decimal_sep == "." else "."
        cleaned = numeric.replace(thousands_sep, "").replace(decimal_sep, ".")
    elif has_dot:
        groups = numeric.split(".")
        if len(groups) > 2:
            # Multiple dots => all thousands separators (e.g. "1.250.000").
            cleaned = numeric.replace(".", "")
        elif len(groups[-1]) == 3:
            # Single dot, exactly 3 trailing digits => thousands separator (e.g. "1.250").
            cleaned = numeric.replace(".", "")
        else:
            # Single dot, 1-2 trailing digits => decimal point (e.g. "125.5").
            cleaned = numeric
    elif has_comma:
        groups = numeric.split(",")
        if len(groups) > 2:
            cleaned = numeric.replace(",", "")
        elif len(groups[-1]) == 3:
            cleaned = numeric.replace(",", "")
        else:
            cleaned = numeric.replace(",", ".")
    else:
        cleaned = numeric

    cleaned = cleaned.replace(" ", "")
    try:
        return float(cleaned), False
    except ValueError:
        return None, True


def parse_amount_text(amount_text: str | None, currency_text: str | None = None) -> ParsedAmount:
    """Convert an ``amount_text``/``currency_text`` pair (verbatim from the Extractor) into
    a minor-unit integer. Never guesses: flags ambiguity instead of inventing a number.
    """
    if not amount_text or not amount_text.strip():
        return ParsedAmount(minor_units=None, currency=None, ambiguous=True, reason="empty amount text")

    stripped = amount_text.strip()
    if re.search(r"\b(?:miễn\s*phí|free(?:\s+of\s+charge)?|foc)\b", stripped, re.I):
        currency = _detect_currency(amount_text, currency_text) or (currency_text.strip() if currency_text else None) or "VND"
        return ParsedAmount(minor_units=0, currency=currency, ambiguous=False)

    percent_match = re.search(r"([-+]?\d+(?:[.,]\d+)?)\s*%", stripped)
    if percent_match:
        pct_val = float(percent_match.group(1).replace(",", "."))
        return ParsedAmount(minor_units=None, currency=None, ambiguous=False, is_percent=True, percent_value=pct_val)

    for pattern, reason in _AMBIGUOUS_AMOUNT_PATTERNS:
        if pattern.search(amount_text):
            return ParsedAmount(minor_units=None, currency=None, ambiguous=True, reason=reason)

    currency = _detect_currency(amount_text, currency_text)
    if currency is None:
        return ParsedAmount(minor_units=None, currency=None, ambiguous=True, reason="currency not identified")
    if currency not in SUPPORTED_INGEST_CURRENCIES:
        return ParsedAmount(minor_units=None, currency=currency, ambiguous=True, reason=f"unsupported currency '{currency}'")

    token, token_ambiguous = _find_amount_token(amount_text)
    if token_ambiguous:
        return ParsedAmount(minor_units=None, currency=currency, ambiguous=True, reason="multiple numeric groups found — cannot determine which one is the amount")
    if token is None:
        return ParsedAmount(minor_units=None, currency=currency, ambiguous=True, reason="no numeric amount found")

    value, ambiguous = _split_numeric_groups(token)
    if ambiguous or value is None or value <= 0:
        return ParsedAmount(minor_units=None, currency=currency, ambiguous=True, reason="could not resolve numeric amount")

    minor_units = round(value * currency_divisor(currency))
    return ParsedAmount(minor_units=minor_units, currency=currency, ambiguous=False)


# ---------------------------------------------------------------------------
# Date / validity window parsing
# ---------------------------------------------------------------------------

_MONTH_NAMES: dict[str, int] = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}

_DMY_RE = re.compile(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})$")
_YMD_RE = re.compile(r"^(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})$")
_DM_RE = re.compile(r"^(\d{1,2})[/\-.](\d{1,2})$")
_TEXT_DM_Y_RE = re.compile(r"^(\d{1,2})\s+([A-Za-z]+)\.?,?\s*(\d{4})$")
_TEXT_MONTH_D_Y_RE = re.compile(r"^([A-Za-z]+)\.?\s+(\d{1,2}),?\s*(\d{4})$")

_RANGE_SPLIT_RE = re.compile(r"\s*(?:–|—|-|~|đến|to|thru|through)\s*", re.I)


@dataclass(frozen=True)
class ParsedDateComponent:
    month: int | None
    day: int | None
    year: int | None
    valid: bool


def _normalize_year(year: int) -> int:
    return 2000 + year if year < 100 else year


def _parse_date_component(token: str) -> ParsedDateComponent:
    token = token.strip()
    if not token:
        return ParsedDateComponent(None, None, None, valid=False)

    if match := _YMD_RE.match(token):
        year, month, day = (int(g) for g in match.groups())
        return ParsedDateComponent(month, day, year, valid=_is_valid_calendar(month, day, year))

    if match := _DMY_RE.match(token):
        day, month, year = match.groups()
        day, month = int(day), int(month)
        year = _normalize_year(int(year))
        return ParsedDateComponent(month, day, year, valid=_is_valid_calendar(month, day, year))

    if match := _TEXT_DM_Y_RE.match(token):
        day_s, month_name, year_s = match.groups()
        month = _MONTH_NAMES.get(month_name.lower())
        if month is None:
            return ParsedDateComponent(None, None, None, valid=False)
        return ParsedDateComponent(month, int(day_s), int(year_s), valid=_is_valid_calendar(month, int(day_s), int(year_s)))

    if match := _TEXT_MONTH_D_Y_RE.match(token):
        month_name, day_s, year_s = match.groups()
        month = _MONTH_NAMES.get(month_name.lower())
        if month is None:
            return ParsedDateComponent(None, None, None, valid=False)
        return ParsedDateComponent(month, int(day_s), int(year_s), valid=_is_valid_calendar(month, int(day_s), int(year_s)))

    if match := _DM_RE.match(token):
        day, month = (int(g) for g in match.groups())
        return ParsedDateComponent(month, day, None, valid=_is_valid_calendar(month, day, None))

    return ParsedDateComponent(None, None, None, valid=False)


def _is_valid_calendar(month: int | None, day: int | None, year: int | None = None) -> bool:
    """Real calendar validation (not just ``1 <= day <= 31``) — a token like "31/02/2025"
    must never be reported ``valid`` (it would otherwise crash ``date.fromisoformat`` far
    downstream, in resolution/commit). When ``year`` is unknown (a recurring season window,
    e.g. "01/10-30/04"), validate against a leap year so 29 Feb stays permitted.
    """
    if month is None or day is None:
        return False
    if not (1 <= month <= 12) or day < 1:
        return False
    reference_year = year if year is not None else 2000  # 2000 is a leap year
    return day <= calendar.monthrange(reference_year, month)[1]


def _iso(component: ParsedDateComponent) -> str | None:
    if not component.valid or component.year is None:
        return None
    return f"{component.year:04d}-{component.month:02d}-{component.day:02d}"


def _month_day(component: ParsedDateComponent) -> str | None:
    if not component.valid:
        return None
    return f"{component.month:02d}-{component.day:02d}"


@dataclass(frozen=True)
class ParsedValidity:
    kind: str  # "date_range" | "single_date" | "season_window"
    date_from: str | None = None
    date_to: str | None = None
    season_from_md: str | None = None
    season_to_md: str | None = None
    ambiguous: bool = False
    reason: str | None = None


def parse_validity_text(validity_text: str | None) -> ParsedValidity:
    """Convert a ``validity_text`` (verbatim) into a date range, single date, or a recurring
    season window (month/day only, no year required — common for annual tariff seasons).
    A single date missing its year is ambiguous and must become a clarification question.
    """
    if not validity_text or not validity_text.strip():
        return ParsedValidity(kind="single_date", ambiguous=True, reason="empty validity text")

    text = validity_text.strip()
    whole = _parse_date_component(text)
    if whole.valid:
        if whole.year is None:
            return ParsedValidity(kind="single_date", ambiguous=True, reason="date is missing its year")
        return ParsedValidity(kind="single_date", date_from=_iso(whole), ambiguous=False)

    tokens = [t for t in _RANGE_SPLIT_RE.split(text) if t]

    if len(tokens) >= 2:
        start, end = _parse_date_component(tokens[0]), _parse_date_component(tokens[-1])
        if not start.valid or not end.valid:
            return ParsedValidity(kind="date_range", ambiguous=True, reason="could not parse both sides of the date range")
        if start.year is not None and end.year is not None:
            return ParsedValidity(kind="date_range", date_from=_iso(start), date_to=_iso(end), ambiguous=False)
        if start.year is None and end.year is None:
            # Recurring annual season window, e.g. "01/10-30/04" (Oct-Apr, crosses year boundary).
            return ParsedValidity(
                kind="season_window",
                season_from_md=_month_day(start),
                season_to_md=_month_day(end),
                ambiguous=False,
            )
        return ParsedValidity(kind="date_range", ambiguous=True, reason="one side of the range has a year, the other does not")

    single = _parse_date_component(tokens[0]) if tokens else ParsedDateComponent(None, None, None, valid=False)
    if not single.valid:
        return ParsedValidity(kind="single_date", ambiguous=True, reason="unrecognized date format")
    if single.year is None:
        return ParsedValidity(kind="single_date", ambiguous=True, reason="date is missing its year")
    return ParsedValidity(kind="single_date", date_from=_iso(single), ambiguous=False)


# ---------------------------------------------------------------------------
# Cancellation policy text -> 15.1 shape A
# ---------------------------------------------------------------------------

_CLAUSE_SPLIT_RE = re.compile(r"[;.\n|]")
_DAYS_RE = re.compile(r"(\d+)\s*(?:-\s*(\d+)\s*)?\s*(?:ng[aà]y|days?)\b", re.I)
_PERCENT_RE = re.compile(r"(\d{1,3})\s*%")
_FREE_RE = re.compile(r"mi[eễ]n\s*ph[ií]|\bfree\b", re.I)
_NO_SHOW_RE = re.compile(r"no[\s-]?show|kh[oô]ng\s*(?:đ|d)[eế]n", re.I)
_UNDER_THRESHOLD_RE = re.compile(r"\bdư[ớo]i\b|\bunder\b|\bless\s+than\b|\bwithin\b", re.I)


@dataclass(frozen=True)
class ParsedCancellationTier:
    days_before_service_min: int
    penalty_percent: int


@dataclass(frozen=True)
class ParsedCancellationPolicy:
    tiers: list[ParsedCancellationTier] = field(default_factory=list)
    no_show_penalty_percent: int = 100
    ambiguous: bool = False
    reason: str | None = None


def _clause_percent(clause: str) -> int | None:
    if match := _PERCENT_RE.search(clause):
        return int(match.group(1))
    if _FREE_RE.search(clause):
        return 0
    return None


def parse_cancellation_policy_text(policy_text: str | None) -> ParsedCancellationPolicy:
    """Convert free-text cancellation policy into 15.1 shape A: ``{tiers[], no_show_percent}``.
    Never fabricates a tier — a clause that doesn't yield both a day threshold and a percent
    is simply skipped; if that leaves zero tiers, the whole policy is reported ambiguous.
    """
    if not policy_text or not policy_text.strip():
        return ParsedCancellationPolicy(ambiguous=True, reason="empty cancellation policy text")

    tiers: list[ParsedCancellationTier] = []
    no_show_percent: int | None = None
    seen_days: set[int] = set()

    for raw_clause in _CLAUSE_SPLIT_RE.split(policy_text):
        clause = raw_clause.strip()
        if not clause:
            continue
        if _NO_SHOW_RE.search(clause):
            percent = _clause_percent(clause)
            if percent is not None:
                no_show_percent = percent
            continue

        percent = _clause_percent(clause)
        days_match = _DAYS_RE.search(clause)
        if percent is None or days_match is None:
            continue
        if _UNDER_THRESHOLD_RE.search(clause):
            days_before_service_min = 0
        else:
            low, _high = days_match.groups()
            days_before_service_min = int(low)
        if days_before_service_min in seen_days:
            return ParsedCancellationPolicy(ambiguous=True, reason="duplicate day threshold across clauses")
        seen_days.add(days_before_service_min)
        tiers.append(ParsedCancellationTier(days_before_service_min=days_before_service_min, penalty_percent=percent))

    if not tiers:
        return ParsedCancellationPolicy(ambiguous=True, reason="no parseable cancellation tiers found")

    ordered = sorted(tiers, key=lambda t: t.days_before_service_min, reverse=True)
    previous_percent: int | None = None
    for tier in ordered:
        if previous_percent is not None and tier.penalty_percent < previous_percent:
            return ParsedCancellationPolicy(ambiguous=True, reason="penalty percent must increase as days-before-service decreases")
        previous_percent = tier.penalty_percent

    return ParsedCancellationPolicy(
        tiers=tiers,
        no_show_penalty_percent=no_show_percent if no_show_percent is not None else 100,
        ambiguous=False,
    )


# ---------------------------------------------------------------------------
# Pax tier text (e.g. "nhóm 10-15 khách")
# ---------------------------------------------------------------------------

_TIER_PAX_RE = re.compile(r"(\d+)\s*(?:-|–|to|đến)\s*(\d+)")
_TIER_PAX_SINGLE_RE = re.compile(r"(\d+)\s*(?:khách|pax|guests?|people|người|chỗ|seats?)\b", re.I)


@dataclass(frozen=True)
class ParsedPaxTier:
    tier_min: int | None
    tier_max: int | None
    ambiguous: bool
    reason: str | None = None


def parse_tier_pax_text(tier_pax_text: str | None) -> ParsedPaxTier:
    """Convert ``tier_pax_text`` (e.g. "nhóm 10-15 khách") into (tier_min, tier_max)."""
    if not tier_pax_text or not tier_pax_text.strip():
        return ParsedPaxTier(None, None, ambiguous=True, reason="empty pax tier text")

    if re.search(r"\b(?:tuổi|years?|yo|age|tháng|months?)\b", tier_pax_text, re.I):
        return ParsedPaxTier(None, None, ambiguous=False)

    if match := _TIER_PAX_RE.search(tier_pax_text):
        low, high = int(match.group(1)), int(match.group(2))
        if low > high:
            low, high = high, low
        return ParsedPaxTier(tier_min=low, tier_max=high, ambiguous=False)

    if match := _TIER_PAX_SINGLE_RE.search(tier_pax_text):
        value = int(match.group(1))
        return ParsedPaxTier(tier_min=value, tier_max=value, ambiguous=False)

    return ParsedPaxTier(None, None, ambiguous=True, reason="could not parse a pax range")
