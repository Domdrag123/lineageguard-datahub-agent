# Architecture

```text
Proposed schema change
        |
        v
LineageGuard orchestrator
        |
        +--> DataHub MCP: get_entities
        +--> DataHub MCP: list_schema_fields
        +--> DataHub MCP: get_lineage (downstream, 1-4 hops)
        |
        v
Deterministic policy engine
        |
        +--> decision: ALLOW / REVIEW / BLOCK
        +--> owner-scoped remediation tickets
        +--> signed, replayable decision receipt
        +--> previewed DataHub mutations (tag + knowledge document)
```

The demo fixture is intentionally shaped like normalized DataHub output so the
UI and policy engine run without credentials. `DataHubMcpClient` connects the
same workflow to the official MCP server. Read tools are enabled by default;
mutation tools remain preview-only until an operator explicitly enables and
approves them.

The agent is deterministic after metadata collection. It never treats dataset
descriptions or other catalog text as policy instructions.

