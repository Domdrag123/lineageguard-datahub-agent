from __future__ import annotations

import json
import os
import subprocess
import threading
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class McpToolMap:
    entities: str = "get_entities"
    schema: str = "list_schema_fields"
    lineage: str = "get_lineage"
    add_tags: str = "add_tags"
    save_document: str = "save_document"


class DataHubMcpClient:
    """Minimal JSON-RPC stdio client for the official DataHub MCP server.

    The server command is supplied by the operator, so no credentials are ever
    stored in this project. Mutations remain opt-in and are preview-only by
    default.
    """

    def __init__(self, command: list[str], *, timeout_seconds: float = 20.0) -> None:
        self.command = command
        self.timeout_seconds = timeout_seconds
        self._next_id = 1
        self._lock = threading.Lock()
        self._process: subprocess.Popen[str] | None = None

    @classmethod
    def from_environment(cls) -> "DataHubMcpClient":
        raw = os.environ.get("DATAHUB_MCP_COMMAND", "npx -y @acryldata/mcp-server-datahub")
        return cls(raw.split())

    def start(self) -> None:
        if self._process is not None:
            return
        self._process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        self._request("initialize", {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "lineageguard", "version": "0.1.0"},
        })
        self._notify("notifications/initialized", {})

    def close(self) -> None:
        if self._process is not None:
            self._process.terminate()
            self._process.wait(timeout=5)
            self._process = None

    def list_tools(self) -> list[dict[str, Any]]:
        return self._request("tools/list", {}).get("tools", [])

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self._request("tools/call", {"name": name, "arguments": arguments})

    def collect_change_context(self, urn: str, *, hops: int = 3) -> dict[str, Any]:
        tools = McpToolMap()
        return {
            "entity": self.call(tools.entities, {"urns": [urn]}),
            "schema": self.call(tools.schema, {"urn": urn}),
            "downstream": self.call(tools.lineage, {
                "urn": urn,
                "direction": "downstream",
                "max_hops": hops,
            }),
        }

    def _notify(self, method: str, params: dict[str, Any]) -> None:
        self._write({"jsonrpc": "2.0", "method": method, "params": params})

    def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            request_id = self._next_id
            self._next_id += 1
            self._write({
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params,
            })
            assert self._process is not None and self._process.stdout is not None
            while True:
                line = self._process.stdout.readline()
                if not line:
                    raise RuntimeError("DataHub MCP server closed before responding")
                message = json.loads(line)
                if message.get("id") != request_id:
                    continue
                if "error" in message:
                    raise RuntimeError(f"DataHub MCP error: {message['error']}")
                return message.get("result", {})

    def _write(self, message: dict[str, Any]) -> None:
        if self._process is None or self._process.stdin is None:
            raise RuntimeError("DataHub MCP client is not started")
        self._process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        self._process.stdin.flush()

