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
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        asset_urn: $("asset").value,
        field: $("field").value,
        operation,
        migration_plan: $("plan").value.trim() || null,
      }),
    });
    if (!response.ok) throw new Error(`Analysis failed (${response.status})`);
    render(await response.json());
  } finally {
    button.disabled = false;
    button.firstChild.textContent = "Analyze with DataHub ";
  }
}

$("analyze").addEventListener("click", analyze);
$("copy").addEventListener("click", async () => {
  await navigator.clipboard.writeText($("receipt").textContent);
  $("copy").textContent = "Copied";
  setTimeout(() => { $("copy").textContent = "Copy"; }, 1200);
});
analyze();

