import re
import unicodedata


def normalize_storage_token(value: str | None) -> str | None:
    if not value:
        return None

    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    compact = re.sub(r"[^A-Za-z0-9]+", "-", ascii_only).strip("-").upper()
    return compact or None


def slot_uses_positions(slot_purpose: str | None) -> bool:
    normalized = normalize_storage_token(slot_purpose)
    return normalized not in {"TRIAGEM", "PENDING"}


def build_location_code(
    storage_unit: str | None,
    storage_niche: str | None,
    storage_position: str | None,
) -> str | None:
    parts = [
        normalize_storage_token(storage_unit),
        normalize_storage_token(storage_niche),
        normalize_storage_token(storage_position),
    ]
    filtered_parts = [part for part in parts if part]
    if not filtered_parts:
        return None
    return "-".join(filtered_parts)


def normalize_slot_position(value: str | None) -> str | None:
    if not value:
        return None

    stripped = value.strip()
    if not stripped:
        return None
    if stripped.isdigit():
        return stripped.zfill(3)
    return normalize_storage_token(stripped)


def build_copy_location_code(
    storage_unit_code: str | None,
    slot_code: str | None,
    slot_position: str | None,
) -> str | None:
    return build_location_code(
        storage_unit_code,
        slot_code,
        normalize_slot_position(slot_position),
    )
