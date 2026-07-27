from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Asset:
    urn: str
    name: str
    kind: str
    owner: str | None
    tags: tuple[str, ...] = ()
    fields: tuple[str, ...] = ()
    environment: str = "PROD"


@dataclass(frozen=True)
class Edge:
    upstream: str
    downstream: str
    field_map: dict[str, tuple[str, ...]] = field(default_factory=dict)


@dataclass(frozen=True)
class Change:
    asset_urn: str
    field: str
    operation: str
    new_value: str | None = None
    migration_plan: str | None = None


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    title: str
    detail: str
    asset_urn: str


@dataclass
class ImpactReport:
    decision: str
    risk_score: int
    source: Asset
    impacted: list[Asset]
    paths: list[list[str]]
    findings: list[Finding]
    tickets: list[dict[str, Any]]
    proposed_datahub_updates: list[dict[str, Any]]
    receipt_sha256: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

