"""Correction Path Planner for KaagazMitra (B3).

Turns B2 readiness findings into a source-backed, ordered correction plan
using ONLY verified correction rules.

Safety (per AGENTS.md and the B3 spec):
- Only rules with ``verification_status == "verified"`` are applied. Pending or
  missing rules never produce confirmed correction instructions.
- Dependencies are included only when they are verified AND available in the
  rulebook. Missing dependencies are never invented as instructions.
- No affidavit, procedure, alternative document or step is ever suggested
  unless it comes from a verified official rule.
- Dependency cycles are detected and surfaced (order_unknown + the exact
  user-facing message); they are never silently "resolved".
- When no verified rule matches, the plan is empty — never fictional.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Set, Tuple

from .matching import FIELD_ALIASES
from .schemas import (
    CorrectionRule,
    CorrectionStep,
    FindingClassification,
    ReadinessResult,
    VerificationStatus,
)

# Repository-root rulebook (populated by official-rule research later).
# It does NOT exist yet by design: no fictional production rules are invented.
# Tests override this module global to point at synthetic fixtures.
CORRECTION_RULEBOOK_PATH = (
    Path(__file__).resolve().parent.parent.parent / "rulebooks" / "corrections.json"
)

# Exact user-facing message shown when dependency cycles make order indeterminate.
CYCLE_MESSAGE = "These steps depend on each other. Ask the issuing office which to do first."

# Fallback when a verified rulebook does not name the authority explicitly.
_UNKNOWN_AUTHORITY = (
    "Authority not specified in the verified rulebook — confirm with the issuing office."
)

# Findings that can drive a correction plan.
_ACTIONABLE = {
    FindingClassification.LIKELY_BLOCKER,
    FindingClassification.NEEDS_SUPPORTING_DOC,
}


def load_correction_rules() -> List[CorrectionRule]:
    """Load and validate the correction rulebook.

    Returns an empty list when the rulebook does not exist yet (never invents
    rules). Tests override ``CORRECTION_RULEBOOK_PATH`` with synthetic fixtures.
    """
    if not CORRECTION_RULEBOOK_PATH.exists():
        return []
    data = json.loads(CORRECTION_RULEBOOK_PATH.read_text(encoding="utf-8"))
    items = data["rules"] if isinstance(data, dict) else data
    return [CorrectionRule.model_validate(item) for item in items]


def _fixes_field(fixes: str, field: str) -> bool:
    """True when a rule's ``fixes`` targets this finding field.

    Normalised through the B1 comparison aliases so e.g. ``full_name`` in a
    rulebook matches the canonical ``name`` comparison field.
    """
    if fixes == field:
        return True
    aliases = FIELD_ALIASES.get(field)
    return bool(aliases) and fixes in aliases


def _select_rules(
    readiness: ReadinessResult, verified: Dict[str, CorrectionRule]
) -> List[CorrectionRule]:
    """Pick verified rules whose ``fixes`` matches an actionable finding."""
    in_rulebook_order = list(verified.values())
    selected: List[CorrectionRule] = []
    seen: Set[str] = set()
    for finding in readiness.findings:
        if finding.classification not in _ACTIONABLE:
            continue
        for rule in in_rulebook_order:
            if rule.rule_id in seen:
                continue
            if _fixes_field(rule.fixes, finding.mismatch_field):
                selected.append(rule)
                seen.add(rule.rule_id)
    return selected


def _dependency_closure(
    selected: List[CorrectionRule], verified: Dict[str, CorrectionRule]
) -> List[CorrectionRule]:
    """Add verified, available dependencies (transitively).

    Dependencies that are missing from the rulebook or not verified are
    skipped — never invented as steps.
    """
    planned = list(selected)
    seen = {r.rule_id for r in planned}
    index = 0
    while index < len(planned):
        for dep_id in planned[index].depends_on:
            dep = verified.get(dep_id)
            if dep is not None and dep.rule_id not in seen:
                planned.append(dep)
                seen.add(dep.rule_id)
        index += 1
    return planned


def _topological_split(
    rules: List[CorrectionRule],
) -> Tuple[List[CorrectionRule], Set[str]]:
    """Kahn topological sort. Returns (ordered, ids_stuck_in_cycles).

    ``ordered`` is deterministic (stable selection order). Every rule id that
    cannot be emitted — i.e. is part of, or blocked by, a dependency cycle —
    is returned in the second set.
    """
    ids = {r.rule_id for r in rules}
    deps = {r.rule_id: [d for d in r.depends_on if d in ids] for r in rules}
    dependents: Dict[str, List[str]] = {rid: [] for rid in deps}
    indegree: Dict[str, int] = {rid: 0 for rid in deps}
    for rid, required in deps.items():
        for dep in required:
            indegree[rid] += 1
            dependents[dep].append(rid)

    queue = [r.rule_id for r in rules if indegree[r.rule_id] == 0]
    ordered_ids: List[str] = []
    while queue:
        rid = queue.pop(0)
        ordered_ids.append(rid)
        for next_id in dependents[rid]:
            indegree[next_id] -= 1
            if indegree[next_id] == 0:
                queue.append(next_id)

    by_id = {r.rule_id: r for r in rules}
    emitted = set(ordered_ids)
    ordered = [by_id[rid] for rid in ordered_ids]
    cycle_ids = {r.rule_id for r in rules if r.rule_id not in emitted}
    return ordered, cycle_ids


def _plain_action(rule: CorrectionRule) -> str:
    """The verified rulebook's own instruction, or a neutral, non-inventing fallback."""
    if rule.action:
        return rule.action
    field_label = rule.fixes.replace("_", " ")
    return (
        f"Ask the issuing office how to correct the {field_label} using the "
        f"officially accepted proof (verified rule {rule.rule_id})."
    )


def plan_corrections(
    readiness: ReadinessResult, correction_rules: List[CorrectionRule]
) -> List[CorrectionStep]:
    """Generate an ordered, source-backed correction plan.

    Verified rules only; prerequisites ordered before dependents via
    topological sort; cycle-affected steps carry ``order_unknown=True``.
    An empty list means "no verified correction applies" — never fiction.
    """
    verified = {
        r.rule_id: r
        for r in correction_rules
        if r.verification_status == VerificationStatus.VERIFIED
    }
    selected = _select_rules(readiness, verified)
    if not selected:
        return []

    planned = _dependency_closure(selected, verified)
    ordered, cycle_ids = _topological_split(planned)
    final = ordered + [r for r in planned if r.rule_id in cycle_ids]
    planned_ids = {r.rule_id for r in planned}

    steps: List[CorrectionStep] = []
    for index, rule in enumerate(final, start=1):
        in_cycle = rule.rule_id in cycle_ids
        steps.append(
            CorrectionStep(
                order=index,
                rule_id=rule.rule_id,
                action=_plain_action(rule),
                authority=rule.authority or _UNKNOWN_AUTHORITY,
                proof_needed=rule.proof_needed,
                depends_on=[d for d in rule.depends_on if d in planned_ids],
                order_unknown=in_cycle,
                is_deadlock=in_cycle,
            )
        )
    return steps


def _dot_escape(text: str) -> str:
    """Escape a value for use inside a Graphviz double-quoted string."""
    return (
        text.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\r", " ")
        .replace("\n", " ")
    )


def render_correction_dot(steps: List[CorrectionStep]) -> str:
    """Render the plan as safe Graphviz DOT text.

    Rule text is escaped; an empty plan renders the historical empty digraph.
    """
    lines = ["digraph correction_path {"]
    for step in steps:
        label = _dot_escape(f"{step.rule_id}: {step.action}")
        style = ", style=dashed" if step.order_unknown else ""
        lines.append(f'  "{_dot_escape(step.rule_id)}" [label="{label}"{style}];')
    for step in steps:
        for dep in step.depends_on:
            lines.append(f'  "{_dot_escape(dep)}" -> "{_dot_escape(step.rule_id)}";')
    lines.append("}")
    return "\n".join(lines) + "\n"


def collect_sources(
    correction_path: List[CorrectionStep], correction_rules: List[CorrectionRule]
) -> List[str]:
    """Ordered, de-duplicated official source URLs for the steps in the plan."""
    by_id = {r.rule_id: r for r in correction_rules}
    sources: List[str] = []
    for step in correction_path:
        rule = by_id.get(step.rule_id)
        if rule is None:
            continue
        for url in rule.source_urls:
            if url not in sources:
                sources.append(url)
    return sources

