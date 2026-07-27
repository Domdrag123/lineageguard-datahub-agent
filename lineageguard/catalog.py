from __future__ import annotations

import json
from collections import deque
from pathlib import Path

from .models import Asset, Edge


class Catalog:
    """Small normalized view of DataHub metadata used by the policy engine."""

    def __init__(self, assets: list[Asset], edges: list[Edge]) -> None:
        self.assets = {asset.urn: asset for asset in assets}
        self.edges = edges

    @classmethod
    def from_file(cls, path: str | Path) -> "Catalog":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        assets = [
            Asset(
                urn=item["urn"],
                name=item["name"],
                kind=item["kind"],
                owner=item.get("owner"),
                tags=tuple(item.get("tags", [])),
                fields=tuple(item.get("fields", [])),
                environment=item.get("environment", "PROD"),
            )
            for item in payload["assets"]
        ]
        edges = [
            Edge(
                upstream=item["upstream"],
                downstream=item["downstream"],
                field_map={key: tuple(value) for key, value in item.get("field_map", {}).items()},
            )
            for item in payload["edges"]
        ]
        return cls(assets, edges)

    def downstream_paths(self, source: str, field: str, max_hops: int = 4) -> list[list[str]]:
        paths: list[list[str]] = []
        queue: deque[tuple[str, str, list[str]]] = deque([(source, field, [source])])
        visited: set[tuple[str, str]] = set()
        while queue:
            urn, current_field, path = queue.popleft()
            if len(path) > max_hops + 1:
                continue
            for edge in self.edges:
                if edge.upstream != urn:
                    continue
                mapped_fields = edge.field_map.get(current_field, (current_field,))
                for mapped in mapped_fields:
                    state = (edge.downstream, mapped)
                    if state in visited:
                        continue
                    visited.add(state)
                    next_path = [*path, edge.downstream]
                    paths.append(next_path)
                    queue.append((edge.downstream, mapped, next_path))
        return paths

