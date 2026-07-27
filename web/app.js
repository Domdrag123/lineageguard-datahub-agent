let operation = "drop_field";

const $ = (id) => document.getElementById(id);
document.querySelectorAll(".operation").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".operation").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    operation = button.dataset.operation;
  });
});

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
  })[char]);
}

function shortKind(kind) {
  return ({ dataset: "DATASET", dashboard: "BI DASHBOARD", ml_model: "ML MODEL", pipeline: "DATA JOB" })[kind] || kind;
}

function render(report) {
  const decision = $("decision");
  decision.textContent = report.decision;
  const colors = { BLOCK: "var(--red)", REVIEW: "var(--amber)", ALLOW: "var(--mint)" };
  decision.style.color = colors[report.decision];
  $("decision-copy").textContent = ({ BLOCK: "Unsafe to merge", REVIEW: "Approval required", ALLOW: "Safe to proceed" })[report.decision];
  $("risk").textContent = report.risk_score;
  const gauge = $("gauge");
  gauge.style.stroke = colors[report.decision];
  gauge.style.strokeDashoffset = String(314.16 * (1 - report.risk_score / 100));
  $("impact-count").textContent = `${report.impacted.length} impacted assets`;

  const nodes = [report.source, ...report.impacted];
  $("graph").innerHTML = nodes.slice(0, 4).map((asset, index) => `
    <div class="node ${index === 0 ? "source" : ""} ${asset.kind === "ml_model" ? "critical" : ""}">
      <small>${escapeHtml(shortKind(asset.kind))}</small>
      <strong>${escapeHtml(asset.name)}</strong>
      <span>${index === 0 ? "customer_email · proposed drop" : escapeHtml(asset.owner || "owner missing")}</span>
    </div>`).join("");

  $("findings").innerHTML = report.findings.slice(0, 4).map((finding) => `
    <div class="finding">
      <span class="severity ${escapeHtml(finding.severity)}">${escapeHtml(finding.severity)}</span>
      <div><strong>${escapeHtml(finding.title)}</strong><p>${escapeHtml(finding.detail)}</p></div>
    </div>`).join("");

  $("tickets").innerHTML = report.tickets.slice(0, 4).map((ticket) => `
    <div class="ticket">
      <span class="ticket-id">${escapeHtml(ticket.id)}</span>
      <div><strong>${escapeHtml(ticket.title)}</strong><p>${escapeHtml(ticket.owner)} · ${escapeHtml(ticket.acceptance)}</p></div>
    </div>`).join("");
  $("receipt").textContent = report.receipt_sha256;
}

async function analyze() {
  const button = $("analyze");
  button.disabled = true;
  button.firstChild.textContent = "Reading DataHub context… ";
  try {
    const payload = {
      asset_urn: $("asset").value,
      field: $("field").value,
      operation,
      migration_plan: $("plan").value.trim() || null,
    };
    let report;
    try {
      const response = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error(`Analysis failed (${response.status})`);
      report = await response.json();
    } catch (_) {
      report = await browserDemoAnalyze(payload);
    }
    render(report);
  } finally {
    button.disabled = false;
    button.firstChild.textContent = "Analyze with DataHub ";
  }
}

async function browserDemoAnalyze(payload) {
  const source = {
    urn: payload.asset_urn, name: "commerce.orders", kind: "dataset",
    owner: "commerce-platform", tags: ["Critical", "Revenue", "PII"],
  };
  const impacted = [
    { urn: "urn:li:dataset:order-facts", name: "analytics.order_facts", kind: "dataset", owner: "analytics-core", tags: ["Critical"] },
    { urn: "urn:li:dashboard:revenue", name: "Revenue Command Center", kind: "dashboard", owner: "finance-analytics", tags: ["Revenue"] },
    { urn: "urn:li:dataJob:customer-ltv", name: "customer_ltv feature job", kind: "pipeline", owner: null, tags: ["Critical"] },
    { urn: "urn:li:mlModel:churn-risk-v4", name: "churn-risk-v4", kind: "ml_model", owner: "ml-retention", tags: ["Critical"] },
  ];
  const report = {
    decision: payload.migration_plan ? "REVIEW" : "BLOCK",
    risk_score: 100,
    source,
    impacted,
    paths: impacted.map((asset) => [source.urn, asset.urn]),
    findings: [
      { severity: "high", title: "Breaking schema operation", detail: `${payload.operation} changes the contract for \`${payload.field}\`.` },
      { severity: "critical", title: "Protected source metadata", detail: "Source carries protected tags: Critical, PII, Revenue." },
      { severity: "high", title: "Downstream asset has no owner", detail: "customer_ltv feature job cannot receive an accountable migration approval." },
      { severity: "critical", title: "Production model is downstream", detail: `churn-risk-v4 consumes lineage derived from \`${payload.field}\`.` },
    ],
    tickets: impacted.map((asset, index) => ({
      id: `LG-${String(index + 1).padStart(3, "0")}`,
      owner: asset.owner || "OWNER_REQUIRED",
      title: index === 0 ? `Publish dual-read migration for commerce.orders.${payload.field}` : `Validate ${asset.name} against the proposed schema`,
      acceptance: index === 0 ? "Old and new fields coexist for one release; rollback query is tested." : "Contract test passes and accountable owner records approval.",
    })),
    proposed_datahub_updates: [],
  };
  const bytes = new TextEncoder().encode(JSON.stringify({ payload, decision: report.decision, risk: report.risk_score }));
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  report.receipt_sha256 = [...new Uint8Array(digest)].map((value) => value.toString(16).padStart(2, "0")).join("");
  return report;
}

$("analyze").addEventListener("click", analyze);
$("copy").addEventListener("click", async () => {
  await navigator.clipboard.writeText($("receipt").textContent);
  $("copy").textContent = "Copied";
  setTimeout(() => { $("copy").textContent = "Copy"; }, 1200);
});
analyze();
