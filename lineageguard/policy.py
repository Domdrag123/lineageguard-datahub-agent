from __future__ import annotations

import hashlib
import json

from .catalog import Catalog
from .models import Change, Finding, ImpactReport


BREAKING_OPERATIONS = {"drop_field", "rename_field", "narrow_type", "make_required"}
CRITICAL_TAGS = {"PII", "Critical", "Revenue", "Regulated"}


def analyze(catalog: Catalog, change: Change) -> ImpactReport:
    source = catalog.assets[change.asset_urn]
    paths = catalog.downstream_paths(change.asset_urn, change.field)
    impacted_urns = list(dict.fromkeys(path[-1] for path in paths))
    impacted = [catalog.assets[urn] for urn in impacted_urns]
    findings: list[Finding] = []
    risk = 0

    if change.operation in BREAKING_OPERATIONS:
        risk += 25
        findings.append(Finding(
            "BREAKING_SCHEMA_CHANGE", "high", "Breaking schema operation",
            f"{change.operation} changes the contract for `{change.field}`.", source.urn,
        ))

    if CRITICAL_TAGS.intersection(source.tags):
        risk += 20
        findings.append(Finding(
            "CRITICAL_SOURCE", "critical", "Protected source metadata",
            f"Source carries protected tags: {', '.join(sorted(CRITICAL_TAGS.intersection(source.tags)))}.",
            source.urn,
        ))

    for asset in impacted:
        if asset.environment == "PROD":
            risk += 5
        if asset.kind == "ml_model":
            risk += 18
            findings.append(Finding(
                "MODEL_DEPENDENCY", "critical", "Production model is downstream",
                f"{asset.name} consumes lineage derived from `{change.field}`.", asset.urn,
            ))
        if asset.kind == "dashboard":
            risk += 8
        if not asset.owner:
            risk += 7
            findings.append(Finding(
                "MISSING_OWNER", "high", "Downstream asset has no owner",
                f"{asset.name} cannot receive an accountable migration approval.", asset.urn,
            ))
        overlap = CRITICAL_TAGS.intersection(asset.tags)
        if overlap:
            risk += 8

    risk = min(100, risk)
    hard_block = (
        change.operation in BREAKING_OPERATIONS
        and (risk >= 45 or any(item.kind == "ml_model" for item in impacted))
        and not change.migration_plan
    )
    decision = "BLOCK" if hard_block else ("REVIEW" if risk >= 30 else "ALLOW")

    tickets = _build_tickets(source.name, change, impacted)
    proposed_updates = [
        {
            "tool": "add_tags",
            "arguments": {"urns": [source.urn], "tags": ["ChangeReviewRequired"]},
            "mode": "preview",
        },
        {
            "tool": "save_document",
            "arguments": {
                "title": f"LineageGuard review: {source.name}.{change.field}",
                "content": f"Decision: {decision}. Risk: {risk}/100. Impacted assets: {len(impacted)}.",
            },
            "mode": "preview",
        },
    ]

    report = ImpactReport(
        decision=decision,
        risk_score=risk,
        source=source,
        impacted=impacted,
        paths=paths,
        findings=findings,
        tickets=tickets,
        proposed_datahub_updates=proposed_updates,
    )
    canonical = json.dumps(report.to_dict(), sort_keys=True, separators=(",", ":"))
    report.receipt_sha256 = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return report


def _build_tickets(source_name: str, change: Change, impacted: list) -> list[dict]:
    tickets = [{
        "id": "LG-001",
        "owner": "data-platform",
        "title": f"Publish dual-read migration for {source_name}.{change.field}",
        "acceptance": "Old and new fields coexist for one release; rollback query is tested.",
    }]
    for index, asset in enumerate(impacted, start=2):
        tickets.append({
            "id": f"LG-{index:03d}",
            "owner": asset.owner or "OWNER_REQUIRED",
            "title": f"Validate {asset.name} against the proposed schema",
            "acceptance": "Contract test passes and accountable owner records approval.",
        })
    return tickets

