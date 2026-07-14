#!/usr/bin/env python3
"""Validate Wise Owl critic and Prime Owl JSON packets."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


CRITIC_ROLES = {"logic_owl", "guardian_owl", "proof_owl"}
CRITIC_VERDICTS = {"pass", "concerns", "blocked"}
PRIME_VERDICTS = {"pass", "fix_required", "caution"}
SEVERITIES = {"blocking", "non_blocking", "suggestion"}
CATEGORIES = {"correctness", "security", "testability", "maintainability", "scope", "ci"}
CONFIDENCES = {"high", "medium", "low"}
REJECTION_REASONS = {
    "duplicate",
    "no_evidence",
    "speculative",
    "style_only",
    "out_of_scope",
    "low_value",
    "contradicted_by_evidence",
}
MODE_ROLES = {
    "lite": {"logic_owl"},
    "standard": {"logic_owl", "proof_owl"},
    "security": {"guardian_owl"},
    "full": CRITIC_ROLES,
}

SOURCE_ID_ROLES = CRITIC_ROLES
CRITIC_TOP_KEYS = {"role", "verdict", "findings", "notes"}
CRITIC_FINDING_KEYS = {"id", "severity", "category", "issue", "evidence", "impact", "suggested_fix", "confidence"}
PRIME_TOP_KEYS = {"verdict", "accepted_findings", "rejected_findings", "builder_instructions"}
PRIME_ACCEPTED_KEYS = {"source_ids", "severity", "category", "issue", "evidence", "impact", "required_builder_action"}
PRIME_REJECTED_KEYS = {"source_ids", "reason", "explanation"}


def is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def list_items(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def require_fields(errors: list[str], obj: Any, fields: tuple[str, ...], path: str) -> None:
    if not isinstance(obj, dict):
        errors.append(f"{path}: expected object")
        return
    for field in fields:
        if field not in obj:
            errors.append(f"{path}.{field}: missing required field")


def reject_unknown_keys(errors: list[str], obj: Any, allowed: set[str], path: str) -> None:
    if not isinstance(obj, dict):
        return
    for field in sorted(set(obj) - allowed):
        errors.append(f"{path}.{field}: unexpected field")


def require_enum(errors: list[str], value: Any, allowed: set[str], path: str) -> None:
    if not isinstance(value, str) or value not in allowed:
        choices = ", ".join(sorted(allowed))
        errors.append(f"{path}: expected one of {choices}; got {value!r}")


def require_source_ids(errors: list[str], value: Any, path: str) -> None:
    if not isinstance(value, list) or not value or not all(is_non_empty_string(item) for item in value):
        errors.append(f"{path}: expected a non-empty list of strings")
        return
    seen: set[str] = set()
    for item in value:
        if item in seen:
            errors.append(f"{path}: duplicate source_id {item!r}")
        seen.add(item)
        role, separator, finding_id = item.partition(":")
        if separator != ":" or role not in SOURCE_ID_ROLES or not finding_id.strip():
            errors.append(f"{path}: invalid source_id {item!r}; expected <logic_owl|guardian_owl|proof_owl>:<finding-id>")


def require_non_empty_strings(errors: list[str], obj: dict[str, Any], fields: tuple[str, ...], path: str) -> None:
    for field in fields:
        if field in obj and not is_non_empty_string(obj.get(field)):
            errors.append(f"{path}.{field}: must be a non-empty string")


def require_non_empty_string_list(errors: list[str], value: Any, path: str) -> None:
    if not isinstance(value, list) or not value or not all(is_non_empty_string(item) for item in value):
        errors.append(f"{path}: expected a non-empty list of non-empty strings")


def validate_notes(errors: list[str], packet: dict[str, Any]) -> None:
    notes = packet.get("notes")
    if not isinstance(notes, list):
        errors.append("notes: expected list")
        return
    for index, note in enumerate(notes):
        if not is_non_empty_string(note):
            errors.append(f"notes[{index}]: expected non-empty string")
    if packet.get("verdict") == "pass" and not notes:
        errors.append("notes: pass packets must include at least one non-empty note")


def require_list(errors: list[str], packet: dict[str, Any], field: str) -> list[Any]:
    value = packet.get(field)
    if not isinstance(value, list):
        errors.append(f"{field}: expected list")
        return []
    return value


def critic_source_ids(packet: dict[str, Any]) -> tuple[set[str], list[str]]:
    errors: list[str] = []
    role = packet.get("role") if isinstance(packet.get("role"), str) else ""
    ids: set[str] = set()
    seen: set[str] = set()
    for index, finding in enumerate(list_items(packet.get("findings"))):
        if not isinstance(finding, dict):
            continue
        finding_id = finding.get("id")
        if not is_non_empty_string(finding_id):
            continue
        if finding_id in seen:
            errors.append(f"findings[{index}].id: duplicate critic finding id {finding_id!r}")
            continue
        seen.add(finding_id)
        ids.add(f"{role}:{finding_id}")
    return ids, errors


def validate_critic(packet: Any) -> list[str]:
    errors: list[str] = []
    require_fields(errors, packet, ("role", "verdict", "findings", "notes"), "$")
    if not isinstance(packet, dict):
        return errors

    reject_unknown_keys(errors, packet, CRITIC_TOP_KEYS, "$")
    require_enum(errors, packet.get("role"), CRITIC_ROLES, "role")
    require_enum(errors, packet.get("verdict"), CRITIC_VERDICTS, "verdict")
    validate_notes(errors, packet)

    for index, finding in enumerate(require_list(errors, packet, "findings")):
        path = f"findings[{index}]"
        require_fields(
            errors,
            finding,
            ("id", "severity", "category", "issue", "evidence", "impact", "suggested_fix", "confidence"),
            path,
        )
        if not isinstance(finding, dict):
            continue
        reject_unknown_keys(errors, finding, CRITIC_FINDING_KEYS, path)
        require_enum(errors, finding.get("severity"), SEVERITIES, f"{path}.severity")
        require_enum(errors, finding.get("category"), CATEGORIES, f"{path}.category")
        require_enum(errors, finding.get("confidence"), CONFIDENCES, f"{path}.confidence")
        require_non_empty_strings(errors, finding, ("id", "issue", "evidence", "impact", "suggested_fix"), path)
    _, duplicate_errors = critic_source_ids(packet)
    errors.extend(duplicate_errors)
    validate_critic_verdict_semantics(errors, packet)
    return errors


def validate_critic_verdict_semantics(errors: list[str], packet: dict[str, Any]) -> None:
    findings = [finding for finding in list_items(packet.get("findings")) if isinstance(finding, dict)]
    has_blocking = any(finding.get("severity") == "blocking" for finding in findings)
    verdict = packet.get("verdict")
    expected = "pass" if not findings else "blocked" if has_blocking else "concerns"
    if verdict != expected:
        errors.append(f"verdict: expected {expected!r} for finding severities; got {verdict!r}")


def validate_source_accounting(
    errors: list[str],
    packet: dict[str, Any],
    critic_packets: list[dict[str, Any]] | None,
    required_roles: set[str] | None = None,
    mode: str | None = None,
) -> None:
    seen: set[str] = set()
    accounted: set[str] = set()
    for section in ("accepted_findings", "rejected_findings"):
        for index, finding in enumerate(list_items(packet.get(section))):
            if not isinstance(finding, dict):
                continue
            for source_id in list_items(finding.get("source_ids")):
                if not is_non_empty_string(source_id):
                    continue
                path = f"{section}[{index}].source_ids"
                if source_id in seen:
                    errors.append(f"{path}: duplicate source_id {source_id!r}")
                seen.add(source_id)
                accounted.add(source_id)

    if critic_packets is None:
        return

    expected: set[str] = set()
    roles: set[str] = set()
    for critic_index, critic in enumerate(list_items(critic_packets)):
        critic_errors = validate_critic(critic)
        errors.extend(f"critics[{critic_index}].{error}" for error in critic_errors)
        if not isinstance(critic, dict):
            continue
        role = critic.get("role")
        if isinstance(role, str) and role in roles:
            errors.append(f"critics[{critic_index}].role: duplicate critic role {role!r}")
        elif isinstance(role, str) and role in CRITIC_ROLES:
            roles.add(role)
        ids, _ = critic_source_ids(critic)
        expected.update(ids)

    if required_roles is not None:
        missing_roles = sorted(required_roles - roles)
        extra_roles = sorted(roles - required_roles)
        if missing_roles:
            errors.append(f"mode {mode}: missing critic roles {', '.join(missing_roles)}")
        if extra_roles:
            errors.append(f"mode {mode}: unexpected critic roles {', '.join(extra_roles)}")

    missing = sorted(expected - accounted)
    extra = sorted(accounted - expected)
    if missing:
        errors.append(f"source_ids: missing critic findings {', '.join(missing)}")
    if extra:
        errors.append(f"source_ids: unknown critic findings {', '.join(extra)}")


def validate_verdict_semantics(errors: list[str], packet: dict[str, Any]) -> None:
    accepted = [finding for finding in list_items(packet.get("accepted_findings")) if isinstance(finding, dict)]
    has_blocking = any(finding.get("severity") == "blocking" for finding in accepted)
    verdict = packet.get("verdict")
    expected = "pass" if not accepted else "fix_required" if has_blocking else "caution"
    if verdict != expected:
        errors.append(f"verdict: expected {expected!r} for accepted finding severities; got {verdict!r}")


def validate_prime(
    packet: Any,
    critic_packets: list[dict[str, Any]] | None = None,
    required_roles: set[str] | None = None,
    mode: str | None = None,
) -> list[str]:
    errors: list[str] = []
    require_fields(errors, packet, ("verdict", "accepted_findings", "rejected_findings", "builder_instructions"), "$")
    if not isinstance(packet, dict):
        return errors

    reject_unknown_keys(errors, packet, PRIME_TOP_KEYS, "$")
    require_enum(errors, packet.get("verdict"), PRIME_VERDICTS, "verdict")
    require_non_empty_string_list(errors, packet.get("builder_instructions"), "builder_instructions")

    for index, finding in enumerate(require_list(errors, packet, "accepted_findings")):
        path = f"accepted_findings[{index}]"
        require_fields(
            errors,
            finding,
            ("source_ids", "severity", "category", "issue", "evidence", "impact", "required_builder_action"),
            path,
        )
        if not isinstance(finding, dict):
            continue
        reject_unknown_keys(errors, finding, PRIME_ACCEPTED_KEYS, path)
        require_source_ids(errors, finding.get("source_ids"), f"{path}.source_ids")
        require_enum(errors, finding.get("severity"), SEVERITIES, f"{path}.severity")
        require_enum(errors, finding.get("category"), CATEGORIES, f"{path}.category")
        require_non_empty_strings(errors, finding, ("issue", "evidence", "impact", "required_builder_action"), path)

    for index, finding in enumerate(require_list(errors, packet, "rejected_findings")):
        path = f"rejected_findings[{index}]"
        require_fields(errors, finding, ("source_ids", "reason", "explanation"), path)
        if not isinstance(finding, dict):
            continue
        reject_unknown_keys(errors, finding, PRIME_REJECTED_KEYS, path)
        require_source_ids(errors, finding.get("source_ids"), f"{path}.source_ids")
        require_enum(errors, finding.get("reason"), REJECTION_REASONS, f"{path}.reason")
        require_non_empty_strings(errors, finding, ("explanation",), path)
    validate_verdict_semantics(errors, packet)
    validate_source_accounting(errors, packet, critic_packets, required_roles, mode)
    return errors


def load_json(path: Path) -> tuple[Any | None, list[str]]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle), []
    except OSError as exc:
        return None, [f"{path}: {exc}"]
    except (ValueError, RecursionError) as exc:
        return None, [f"{path}: invalid JSON: {exc}"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a Wise Owl JSON packet.")
    parser.add_argument("--type", choices=("critic", "prime"), required=True)
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--critics", nargs="+", type=Path, default=[])
    parser.add_argument("--require-critics", action="store_true")
    parser.add_argument("--mode", choices=tuple(MODE_ROLES))
    args = parser.parse_args(argv)

    packet, errors = load_json(args.file)
    if not errors:
        if args.critics and args.type != "prime":
            errors = ["--critics can only be used with --type prime"]
        elif args.mode and args.type != "prime":
            errors = ["--mode can only be used with --type prime"]
        elif args.require_critics and args.type != "prime":
            errors = ["--require-critics can only be used with --type prime"]
        elif args.require_critics and not args.critics:
            errors = ["--require-critics requires at least one --critics packet"]
        elif args.type == "critic":
            errors = validate_critic(packet)
        else:
            critic_packets = []
            for critic_path in args.critics:
                critic_packet, critic_errors = load_json(critic_path)
                errors.extend(critic_errors)
                if not critic_errors:
                    critic_packets.append(critic_packet)
            if not errors:
                accounting_packets = critic_packets if args.critics or args.mode else None
                errors = validate_prime(packet, accounting_packets, MODE_ROLES.get(args.mode), args.mode)

    if errors:
        print("Wise Owl packet is invalid:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    if args.type == "prime" and not args.critics and not args.mode:
        print("Wise Owl packet is valid. Source accounting was not checked because --critics was not supplied.")
    else:
        print("Wise Owl packet is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
