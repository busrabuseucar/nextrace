const scenarios = {
  latency: {id: "CR-028", sourceNode: "SYS-REQ-142", current: "250 ms", proposed: "150 ms", description: "Sentetik telemetri gecikme değişikliği örneği."},
  encryption: {id: "CR-031", sourceNode: "SEC-REQ-055", current: "AES-128", proposed: "AES-256", description: "Sentetik şifreleme standardı değişikliği örneği."},
  sampling: {id: "CR-044", sourceNode: "SNS-REQ-021", current: "60 Hz", proposed: "100 Hz", description: "Sentetik sensör örnekleme değişikliği örneği."}
};

const graphPositions = [
  { x: 70, y: 166 },
  { x: 312, y: 48 }, { x: 312, y: 166 }, { x: 312, y: 284 },
  { x: 594, y: 35 }, { x: 594, y: 126 }, { x: 594, y: 217 }, { x: 594, y: 308 },
  { x: 824, y: 171 }
];

const scenarioSelect = document.querySelector("#scenarioSelect");
const analyzeButton = document.querySelector("#analyzeButton");
const analyzeButtonLabel = document.querySelector("#analyzeButtonLabel");
const analysisState = document.querySelector("#analysisState");
const evidenceTable = document.querySelector("#evidenceTable");
const traceGraph = document.querySelector("#traceGraph");
const graphStage = document.querySelector("#graphStage");
const changedNodeInput = document.querySelector("#changedNodeInput");
const importButton = document.querySelector("#importButton");
const importStatus = document.querySelector("#importStatus");
const projectSelect = document.querySelector("#projectSelect");
const authGate = document.querySelector("#authGate");
const authForm = document.querySelector("#authForm");
const authMessage = document.querySelector("#authMessage");
const logoutButton = document.querySelector("#logoutButton");
const passwordButton = document.querySelector("#passwordButton");
const passwordGate = document.querySelector("#passwordGate");
const passwordForm = document.querySelector("#passwordForm");
const passwordMessage = document.querySelector("#passwordMessage");
const passwordCancel = document.querySelector("#passwordCancel");
const accessNav = document.querySelector("#accessNav");
const connectorNav = document.querySelector("#connectorNav");
const importCard = document.querySelector("#importCard");
const fromVersion = document.querySelector("#fromVersion");
const toVersion = document.querySelector("#toVersion");
const compareVersionsButton = document.querySelector("#compareVersionsButton");
const versionMessage = document.querySelector("#versionMessage");
let currentScenario = scenarios.latency;
let currentFilter = "all";
let analyzed = false;
let analysisGeneration = 0;
let lastAnalysis = null;
let currentProjectId = "demo";
let currentAnalysisId = null;
let setupRequired = false;
let currentUser = null;
let availableProjects = [];
let currentVersions = [];
let passwordChangeForced = false;

function showAuthGate(requiresSetup = false) {
  resetAnalysis();
  setupRequired = requiresSetup;
  authGate.hidden = false;
  authForm.hidden = false;
  document.querySelector("#authTitle").textContent = requiresSetup ? "İlk yönetici hesabını oluştur" : "Oturum aç";
  document.querySelector("#authHint").textContent = requiresSetup
    ? "Bu işlem yalnızca bir kez yapılır. En az 12 karakterli, harf ve rakam içeren bir parola belirle."
    : "Proje verilerine erişmek için yönetici hesabınla giriş yap.";
  document.querySelector("#authSubmit").textContent = requiresSetup ? "Yönetici hesabını oluştur" : "Giriş yap";
  document.querySelector("#authPassword").autocomplete = requiresSetup ? "new-password" : "current-password";
  logoutButton.hidden = true;
  passwordButton.hidden = true;
  passwordGate.hidden = true;
}

function hideAuthGate(user) {
  currentUser = user;
  authGate.hidden = true;
  authMessage.textContent = "";
  authForm.reset();
  logoutButton.hidden = false;
  logoutButton.textContent = `${user.email} · Çıkış`;
  if (user.must_change_password) {
    passwordButton.hidden = true;
    accessNav.hidden = true;
    importCard.hidden = true;
    showPasswordGate(true);
    return;
  }
  passwordButton.hidden = false;
  passwordGate.hidden = true;
  const isAdmin = user.role === "admin";
  accessNav.hidden = !isAdmin;
  connectorNav.hidden = !isAdmin;
  importCard.hidden = !isAdmin;
  loadAvailableProjects();
  if (isAdmin) {
    loadAccessData();
  } else if (document.querySelector('[data-view-panel="access"].active, [data-view-panel="connectors"].active')) {
    document.querySelector('[data-view="analysis"]').click();
  }
}

function showPasswordGate(forced = false) {
  passwordChangeForced = forced;
  passwordGate.hidden = false;
  passwordForm.reset();
  passwordMessage.textContent = "";
  passwordCancel.hidden = forced;
  document.querySelector("#passwordTitle").textContent = forced
    ? "Geçici parolanı değiştir"
    : "Parolanı değiştir";
  document.querySelector("#passwordHint").textContent = forced
    ? "Projeye erişmeden önce yönetici tarafından verilen geçici parolanı yenilemelisin."
    : "Yeni parolan en az 12 karakter, bir harf ve bir rakam içermelidir.";
  document.querySelector("#currentPassword").focus();
}

function hidePasswordGate() {
  if (passwordChangeForced) return;
  passwordGate.hidden = true;
  passwordMessage.textContent = "";
  passwordForm.reset();
}

async function initializeAuth() {
  try {
    const response = await fetch("/api/auth/status", { cache: "no-store" });
    if (!response.ok) throw new Error("Kimlik doğrulama servisi yanıt vermedi.");
    const result = await response.json();
    if (result.authenticated) hideAuthGate(result.user);
    else showAuthGate(result.setup_required);
  } catch (error) {
    document.querySelector("#authTitle").textContent = "MVP sunucusu çalışmıyor";
    document.querySelector("#authHint").textContent = "Uygulamayı statik sunucuyla değil, python backend/server.py komutuyla başlat.";
    authMessage.textContent = error.message;
  }
}

async function apiFetch(url, options = {}) {
  const response = await fetch(url, options);
  if (response.status === 401) {
    currentUser = null;
    showAuthGate(false);
  } else if (response.status === 403) {
    const detail = await response.clone().json().catch(() => ({}));
    if (detail.code === "PASSWORD_CHANGE_REQUIRED") showPasswordGate(true);
  }
  return response;
}

function applySelectedProjectAccess() {
  updateSourceLabel();
  const project = availableProjects.find(item => item.id === currentProjectId);
  const canAnalyze = currentUser?.role === "admin" || project?.access_level === "analyst";
  analyzeButton.disabled = !canAnalyze;
  analyzeButtonLabel.textContent = canAnalyze ? "Etkiyi analiz et" : "Yalnızca görüntüleme yetkisi";
  if (!project) {
    analysisState.className = "analysis-state error";
    analysisState.innerHTML = "<span></span> Atanmış proje bulunamadı";
  }
}

async function loadAvailableProjects(preferredProjectId = null) {
  try {
    const response = await apiFetch("/api/projects", { cache: "no-store" });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Projeler alınamadı.");
    availableProjects = result.projects;
    projectSelect.innerHTML = availableProjects.length
      ? availableProjects.map(project => `<option value="${escapeHtml(project.id)}">${escapeHtml(project.name)}</option>`).join("")
      : '<option value="">Atanmış proje yok</option>';
    const requested = preferredProjectId || currentProjectId;
    const selected = availableProjects.find(project => project.id === requested) || availableProjects[0];
    currentProjectId = selected?.id || "";
    projectSelect.value = currentProjectId;
    if (isSeedProject()) changedNodeInput.value = currentScenario.sourceNode;
    else changedNodeInput.value = "";
    resetAnalysis();
    applySelectedProjectAccess();
    if (document.querySelector('[data-view-panel="versions"]').classList.contains("active")) {
      loadProjectVersions();
    }
  } catch (error) {
    analysisState.className = "analysis-state error";
    analysisState.innerHTML = "<span></span>";
    analysisState.append(document.createTextNode(` ${error.message}`));
  }
}

function resetVersionDiff() {
  ["#diffAdded", "#diffRemoved", "#diffModified", "#diffTotal"].forEach(selector => {
    document.querySelector(selector).textContent = "—";
  });
  document.querySelector("#nodeDiffTable").innerHTML = '<tr class="placeholder-row"><td colspan="3">Karşılaştırma bekleniyor.</td></tr>';
  document.querySelector("#edgeDiffTable").innerHTML = '<tr class="placeholder-row"><td colspan="3">Karşılaştırma bekleniyor.</td></tr>';
}

function versionSourceLabel(source) {
  return {
    seed: "Başlangıç", csv: "CSV", migration: "Aktarılan",
    jira: "Jira", gitlab: "GitLab", "jira+gitlab": "Jira + GitLab"
  }[source] || source;
}

function renderVersionHistory() {
  const history = document.querySelector("#versionHistory");
  history.innerHTML = currentVersions.length
    ? currentVersions.map(version => `
      <div class="version-history-item">
        <strong>v${version.version_number}</strong>
        <span>${version.node_count} düğüm · ${version.edge_count} ilişki</span>
        <small>${escapeHtml(version.created_by_email)} · ${new Date(version.created_at).toLocaleString("tr-TR")}</small>
        <span class="version-source">${escapeHtml(versionSourceLabel(version.source))}</span>
      </div>
    `).join("")
    : '<p class="version-message">Bu proje için sürüm kaydı bulunamadı.</p>';
}

async function loadProjectVersions() {
  resetVersionDiff();
  if (!currentProjectId) {
    versionMessage.className = "version-message error";
    versionMessage.textContent = "Karşılaştırılacak bir proje seçilmedi.";
    return;
  }
  versionMessage.className = "version-message";
  versionMessage.textContent = "Sürüm geçmişi alınıyor…";
  try {
    const response = await apiFetch(`/api/projects/versions?project_id=${encodeURIComponent(currentProjectId)}`, { cache: "no-store" });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Sürümler alınamadı.");
    currentVersions = result.versions;
    document.querySelector("#versionCountChip").textContent = `${currentVersions.length} sürüm`;
    const options = currentVersions.map(version =>
      `<option value="${escapeHtml(version.id)}">v${version.version_number} · ${version.node_count} düğüm · ${new Date(version.created_at).toLocaleDateString("tr-TR")}</option>`
    ).join("");
    fromVersion.innerHTML = options;
    toVersion.innerHTML = options;
    if (currentVersions.length >= 2) {
      fromVersion.value = currentVersions[1].id;
      toVersion.value = currentVersions[0].id;
      compareVersionsButton.disabled = false;
      versionMessage.textContent = "Karşılaştırmaya hazır. Varsayılan olarak son iki sürüm seçildi.";
    } else {
      compareVersionsButton.disabled = true;
      versionMessage.textContent = "Fark analizi için aktif projeye en az bir yeni CSV sürümü yükle.";
    }
    renderVersionHistory();
  } catch (error) {
    currentVersions = [];
    compareVersionsButton.disabled = true;
    versionMessage.className = "version-message error";
    versionMessage.textContent = error.message;
  }
}

function diffChangeLabel(change) {
  return { added: "Eklendi", removed: "Kaldırıldı", modified: "Değiştirildi" }[change];
}

function formatDiffFields(item) {
  const fieldLabels = {
    label: "ad", type: "tür", owner: "sorumlu", criticality: "kritiklik", reason: "gerekçe"
  };
  if (item.change === "added") {
    return escapeHtml(item.after?.label || "Yeni kayıt");
  }
  if (item.change === "removed") {
    return escapeHtml(item.before?.label || "Kayıt kaldırıldı");
  }
  return item.fields.map(field => {
    const before = item.before?.[field] ?? "—";
    const after = item.after?.[field] ?? "—";
    return `<span class="diff-field"><b>${escapeHtml(fieldLabels[field] || field)}:</b> ${escapeHtml(before)} → ${escapeHtml(after)}</span>`;
  }).join("");
}

function renderDiffRows(selector, items) {
  document.querySelector(selector).innerHTML = items.length
    ? items.map(item => `
      <tr>
        <td><span class="change-badge ${item.change}">${diffChangeLabel(item.change)}</span></td>
        <td class="artifact-cell"><strong>${escapeHtml(item.identity)}</strong></td>
        <td class="diff-fields">${formatDiffFields(item)}</td>
      </tr>
    `).join("")
    : '<tr class="placeholder-row"><td colspan="3">Bu grupta değişiklik yok.</td></tr>';
}

async function compareProjectVersions() {
  if (!fromVersion.value || !toVersion.value) return;
  compareVersionsButton.disabled = true;
  versionMessage.className = "version-message";
  versionMessage.textContent = "Sürüm anlık görüntüleri karşılaştırılıyor…";
  try {
    const params = new URLSearchParams({
      project_id: currentProjectId,
      from_version: fromVersion.value,
      to_version: toVersion.value
    });
    const response = await apiFetch(`/api/projects/diff?${params}`, { cache: "no-store" });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Sürümler karşılaştırılamadı.");
    const summary = result.summary;
    document.querySelector("#diffAdded").textContent = summary.nodes_added + summary.edges_added;
    document.querySelector("#diffRemoved").textContent = summary.nodes_removed + summary.edges_removed;
    document.querySelector("#diffModified").textContent = summary.nodes_modified + summary.edges_modified;
    document.querySelector("#diffTotal").textContent = summary.total_changes;
    renderDiffRows("#nodeDiffTable", result.node_changes);
    renderDiffRows("#edgeDiffTable", result.edge_changes);
    versionMessage.className = "version-message success";
    versionMessage.textContent = `v${result.from_version.version_number} → v${result.to_version.version_number}: ${summary.total_changes} değişiklik bulundu.`;
  } catch (error) {
    versionMessage.className = "version-message error";
    versionMessage.textContent = error.message;
  } finally {
    compareVersionsButton.disabled = currentVersions.length < 2;
  }
}

async function loadAccessData() {
  if (currentUser?.role !== "admin") return;
  const userStatus = document.querySelector("#createUserStatus");
  try {
    const [usersResponse, projectsResponse, membershipsResponse] = await Promise.all([
      apiFetch("/api/users", { cache: "no-store" }),
      apiFetch("/api/projects", { cache: "no-store" }),
      apiFetch("/api/projects/access", { cache: "no-store" })
    ]);
    const [usersResult, projectsResult, membershipsResult] = await Promise.all([
      usersResponse.json(), projectsResponse.json(), membershipsResponse.json()
    ]);
    if (!usersResponse.ok) throw new Error(usersResult.error || "Kullanıcılar alınamadı.");
    if (!projectsResponse.ok) throw new Error(projectsResult.error || "Projeler alınamadı.");
    if (!membershipsResponse.ok) throw new Error(membershipsResult.error || "Erişimler alınamadı.");

    const users = usersResult.users;
    const projects = projectsResult.projects;
    const memberships = membershipsResult.memberships;
    document.querySelector("#usersTable").innerHTML = users.map(user => `
      <tr>
        <td>${escapeHtml(user.email)}</td>
        <td>${user.role === "admin" ? "Yönetici" : "Analist"}</td>
        <td><span class="account-state ${user.active ? "active" : "inactive"}">${user.active ? "Aktif" : "Kapalı"}</span></td>
        <td><span class="password-state ${user.must_change_password ? "required" : "ready"}">${user.must_change_password ? "Değişmeli" : "Güncel"}</span></td>
        <td>${new Date(user.created_at).toLocaleDateString("tr-TR")}</td>
      </tr>
    `).join("");
    document.querySelector("#membershipsTable").innerHTML = memberships.length
      ? memberships.map(item => `
        <tr><td>${escapeHtml(item.email)}</td><td>${escapeHtml(item.project_name)}</td><td>${item.access_level === "analyst" ? "Analiz" : "Görüntüleme"}</td></tr>
      `).join("")
      : '<tr class="placeholder-row"><td colspan="3">Henüz proje ataması yok.</td></tr>';
    document.querySelector("#accessUser").innerHTML = users
      .filter(user => user.role === "analyst")
      .map(user => `<option value="${escapeHtml(user.id)}">${escapeHtml(user.email)}</option>`).join("");
    document.querySelector("#accessProject").innerHTML = projects
      .map(project => `<option value="${escapeHtml(project.id)}">${escapeHtml(project.name)}</option>`).join("");
    const manageableUsers = users.filter(user => user.id !== currentUser.id);
    const accountUser = document.querySelector("#accountUser");
    accountUser.innerHTML = manageableUsers.length
      ? manageableUsers.map(user => `<option value="${escapeHtml(user.id)}" data-active="${user.active}">${escapeHtml(user.email)}</option>`).join("")
      : '<option value="">Yönetilecek başka kullanıcı yok</option>';
    accountUser.disabled = !manageableUsers.length;
    document.querySelectorAll("#resetPasswordForm button, #resetPasswordForm input, #accountStatusForm button, #accountStatusForm select")
      .forEach(element => { element.disabled = !manageableUsers.length; });
    syncSelectedAccountStatus();
  } catch (error) {
    userStatus.className = "admin-status error";
    userStatus.textContent = error.message;
  }
}

function renderConnectorState(name, connector) {
  const state = document.querySelector(`#${name}ConnectorState`);
  const origin = document.querySelector(`#${name}ConnectorOrigin`);
  state.textContent = connector.configured ? "Hazır" : "Yapılandırılmadı";
  state.className = `connector-state${connector.configured ? " ready" : ""}`;
  origin.textContent = connector.base_url || "Sunucu ortam değişkenleri bekleniyor";
}

async function loadConnectorStatus() {
  if (currentUser?.role !== "admin") return;
  try {
    const response = await apiFetch("/api/connectors/status", { cache: "no-store" });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Bağlayıcı durumu alınamadı.");
    renderConnectorState("jira", result.connectors.jira);
    renderConnectorState("gitlab", result.connectors.gitlab);
  } catch (error) {
    ["jira", "gitlab"].forEach(name => {
      const state = document.querySelector(`#${name}ConnectorState`);
      state.className = "connector-state";
      state.textContent = "Durum alınamadı";
    });
    document.querySelector("#connectorSyncStatus").className = "admin-status error";
    document.querySelector("#connectorSyncStatus").textContent = error.message;
  }
}

async function syncConnectors(event) {
  event.preventDefault();
  const status = document.querySelector("#connectorSyncStatus");
  const button = document.querySelector("#connectorSyncButton");
  const jiraProjectKey = document.querySelector("#jiraProjectKey").value.trim();
  const gitlabProject = document.querySelector("#gitlabProjectPath").value.trim();
  if (!jiraProjectKey && !gitlabProject) {
    status.className = "admin-status error connector-sync-status";
    status.textContent = "En az bir Jira veya GitLab proje bilgisi gir.";
    return;
  }
  button.disabled = true;
  button.textContent = "Eşitleniyor…";
  status.className = "admin-status connector-sync-status";
  status.textContent = "Kaynak kayıtları okunuyor ve grafik oluşturuluyor…";
  try {
    const response = await apiFetch("/api/connectors/sync", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project_id: document.querySelector("#connectorProjectId").value.trim(),
        name: document.querySelector("#connectorProjectName").value.trim(),
        jira_project_key: jiraProjectKey,
        gitlab_project: gitlabProject
      })
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Kaynaklar eşitlenemedi.");
    status.className = "admin-status connector-sync-status";
    status.textContent = `${result.message} ${result.jira_issue_count} issue, ${result.gitlab_commit_count} commit ve ${result.edge_count} kanıt ilişkisi.`;
    document.querySelector("#dataBadge").lastChild.textContent = " Jira / GitLab verisi";
    currentProjectId = result.project_id;
    await loadAvailableProjects(result.project_id);
  } catch (error) {
    status.className = "admin-status error connector-sync-status";
    status.textContent = error.message;
  } finally {
    button.disabled = false;
    button.textContent = "Kaynakları eşitle";
  }
}

function syncSelectedAccountStatus() {
  const selected = document.querySelector("#accountUser").selectedOptions[0];
  if (!selected?.value) return;
  document.querySelector("#accountActive").value = selected.dataset.active === "true" ? "true" : "false";
}

function isSeedProject() {
  return availableProjects.find(project => project.id === currentProjectId)?.latest_source === "seed";
}

function updateSourceLabel() {
  const project = availableProjects.find(item => item.id === currentProjectId);
  const label = !project ? "Proje seçilmedi" : isSeedProject() ? "Sentetik demo verisi" : `Kayıtlı proje verisi · ${project.latest_source}`;
  document.querySelector("#dataBadge").lastChild.textContent = ` ${label}`;
  importStatus.textContent = label;
  scenarioSelect.disabled = !isSeedProject();
  document.querySelector("#scenarioDescription").textContent = isSeedProject() ? currentScenario.description : "Seçili grafikteki başlangıç düğümünü gir. Etki, kayıtlı ilişkilere göre hesaplanır.";
  document.querySelector("#currentValue").textContent = isSeedProject() ? currentScenario.current : "—";
  document.querySelector("#proposedValue").textContent = isSeedProject() ? currentScenario.proposed : "—";
  document.querySelector("#scenarioId").textContent = isSeedProject() ? currentScenario.id : currentProjectId;
}

function updateScenarioText() {
  currentScenario = scenarios[scenarioSelect.value];
  document.querySelector("#scenarioId").textContent = currentScenario.id;
  document.querySelector("#currentValue").textContent = currentScenario.current;
  document.querySelector("#proposedValue").textContent = currentScenario.proposed;
  document.querySelector("#scenarioDescription").textContent = currentScenario.description;
  if (isSeedProject()) changedNodeInput.value = currentScenario.sourceNode;
  else changedNodeInput.value = "";
  resetAnalysis();
}

function resetAnalysis() {
  analysisGeneration += 1;
  analyzed = false;
  lastAnalysis = null;
  document.querySelector("#auditVersion").textContent = "—";
  closeDrawer();
  ["#exportButton", "#exportButtonSecondary"].forEach(id => document.querySelector(id).disabled = true);
  currentAnalysisId = null;
  document.querySelector("#auditTimeline").textContent = "Henüz analiz oluşturulmadı.";
  graphStage.classList.remove("analyzed");
  traceGraph.innerHTML = "";
  evidenceTable.innerHTML = '<tr class="placeholder-row"><td colspan="5">Sonuçlar için etki analizini çalıştır.</td></tr>';
  analysisState.className = "analysis-state";
  analysisState.innerHTML = "<span></span> Analize hazır";
  document.querySelector("#summaryTitle").textContent = "Henüz çalıştırılmadı";
  document.querySelector("#confidenceRing").textContent = "—";
  document.querySelector("#impactCount").textContent = "—";
  document.querySelector("#criticalCount").textContent = "—";
  document.querySelector("#pathCount").textContent = "—";
  document.querySelector("#summaryNote").textContent = "Analiz, izlenebilirlik grafiğindeki kayıtlı ilişkileri ve sürüm bilgilerini kullanır.";
}

function riskLabel(risk) {
  return { critical: "Kritik", high: "Yüksek", medium: "Orta" }[risk];
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, character => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
  })[character]);
}

function renderSummary() {
  const critical = currentScenario.items.filter(item => item.risk === "critical").length;
  document.querySelector("#summaryTitle").textContent = currentScenario.summary;
  document.querySelector("#confidenceRing").textContent = currentScenario.metadataCoverage === null ? "—" : `%${currentScenario.metadataCoverage}`;
  document.querySelector("#impactCount").textContent = currentScenario.items.length;
  document.querySelector("#criticalCount").textContent = critical;
  document.querySelector("#pathCount").textContent = currentScenario.pathCount;
  document.querySelector("#summaryNote").textContent = currentScenario.note;
}

function renderTable() {
  const filtered = currentScenario.items.filter(item => currentFilter === "all" || item.risk === currentFilter);
  evidenceTable.innerHTML = filtered.map(item => `
    <tr data-item-id="${escapeHtml(item.id)}">
      <td class="artifact-cell"><strong>${escapeHtml(item.label)}</strong><span>${escapeHtml(item.id)}</span></td>
      <td>${escapeHtml(item.type)}</td>
      <td>${escapeHtml(item.path)}</td>
      <td><span class="risk-pill ${item.risk}">${riskLabel(item.risk)}</span></td>
      <td><span class="status-pill">${escapeHtml(item.status)}</span></td>
    </tr>`).join("");
  evidenceTable.querySelectorAll("tr[data-item-id]").forEach(row => {
    row.addEventListener("click", () => openDrawer(currentScenario.items.find(item => item.id === row.dataset.itemId)));
  });
}

function createSvg(tag, attrs = {}) {
  const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
  Object.entries(attrs).forEach(([key, value]) => el.setAttribute(key, value));
  return el;
}

function renderGraph() {
  traceGraph.innerHTML = "";
  const root = { id: lastAnalysis.changed_node, label: "Değişiklik kaynağı", risk: "source", score: null };
  const items = [root, ...currentScenario.items.slice(0, 8)];
  const itemIndexes = new Map(items.map((item, index) => [item.id, index]));
  const edges = [];
  const edgeKeys = new Set();
  items.slice(1).forEach((item, itemOffset) => {
    const path = item.path.split("→").map(part => part.trim()).filter(Boolean);
    const predecessor = path.at(-2);
    const from = itemIndexes.get(predecessor) ?? 0;
    const to = itemOffset + 1;
    const edgeKey = `${from}-${to}`;
    if (!edgeKeys.has(edgeKey)) {
      edgeKeys.add(edgeKey);
      edges.push([from, to]);
    }
  });

  edges.forEach(([from, to], index) => {
    const a = graphPositions[from];
    const b = graphPositions[to];
    const targetRisk = items[to].risk || "medium";
    const path = createSvg("path", {
      d: `M ${a.x + 150} ${a.y + 31} C ${a.x + 205} ${a.y + 31}, ${b.x - 55} ${b.y + 31}, ${b.x} ${b.y + 31}`,
      class: `graph-edge ${targetRisk}`,
      style: `animation-delay:${index * 55}ms`
    });
    traceGraph.appendChild(path);
  });

  items.forEach((item, index) => {
    const p = graphPositions[index];
    const group = createSvg("g", { class: `graph-node ${item.risk || "medium"}`, tabindex: "0", style: `animation-delay:${140 + index * 65}ms`, role: "button" });
    group.appendChild(createSvg("rect", { x: p.x, y: p.y, width: 150, height: 62 }));
    const idText = createSvg("text", { x: p.x + 13, y: p.y + 18, class: "node-id" });
    idText.textContent = item.id;
    group.appendChild(idText);
    const labelText = createSvg("text", { x: p.x + 13, y: p.y + 39, class: "node-label" });
    const shortLabel = item.label.length > 22 ? `${item.label.slice(0, 21)}…` : item.label;
    labelText.textContent = shortLabel;
    group.appendChild(labelText);
    if (item.score) {
      const scoreText = createSvg("text", { x: p.x + 136, y: p.y + 18, class: "node-score", "text-anchor": "end" });
      scoreText.textContent = item.score;
      group.appendChild(scoreText);
      group.addEventListener("click", () => openDrawer(item));
      group.addEventListener("keydown", event => { if (event.key === "Enter") openDrawer(item); });
    }
    traceGraph.appendChild(group);
  });
}

async function runAnalysis() {
  resetAnalysis();
  const generation = analysisGeneration;
  analyzeButton.disabled = true;
  analyzeButtonLabel.textContent = "Graf taranıyor…";
  analysisState.className = "analysis-state running";
  analysisState.innerHTML = "<span></span> Kaynak ilişkileri taranıyor";
  graphStage.classList.remove("analyzed");
  try {
    const changedNodeId = changedNodeInput.value.trim();
    if (!changedNodeId) throw new Error("Değişen düğüm kimliği zorunludur.");
    const response = await apiFetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project_id: currentProjectId,
        changed_node_id: changedNodeId,
        current_value: isSeedProject() ? currentScenario.current : "",
        proposed_value: isSeedProject() ? currentScenario.proposed : ""
      })
    });
    const result = await response.json();
    if (generation !== analysisGeneration) return;
    if (!response.ok) throw new Error(result.error || "Analiz tamamlanamadı.");

    currentScenario = {
      ...currentScenario,
      items: result.items,
      metadataCoverage: result.metadata_coverage,
      summary: result.summary,
      note: result.note,
      pathCount: result.path_count
    };
    lastAnalysis = result;
    currentAnalysisId = result.analysis_id;
    ["#exportButton", "#exportButtonSecondary"].forEach(id => document.querySelector(id).disabled = false);
    analyzed = true;
    renderSummary();
    renderGraph();
    renderTable();
    graphStage.classList.add("analyzed");
    analysisState.className = "analysis-state complete";
    analysisState.innerHTML = `<span></span> Analiz tamamlandı · ${result.duration_ms} ms`;
    buildAuditLog();
  } catch (error) {
    if (generation !== analysisGeneration) return;
    analysisState.className = "analysis-state error";
    analysisState.innerHTML = "<span></span>";
    analysisState.append(document.createTextNode(` ${error.message}`));
  } finally {
    applySelectedProjectAccess();
    analyzeButtonLabel.textContent = analyzed ? "Analizi yeniden çalıştır" : "Etkiyi analiz et";
  }
}

async function importGraph() {
  const nodesFile = document.querySelector("#nodesFile").files[0];
  const edgesFile = document.querySelector("#edgesFile").files[0];
  if (!nodesFile || !edgesFile) {
    importStatus.className = "import-status error";
    importStatus.textContent = "İki CSV dosyasını da seçmelisin.";
    return;
  }

  importButton.disabled = true;
  importButton.textContent = "Yükleniyor…";
  importStatus.className = "import-status";
  importStatus.textContent = "CSV dosyaları doğrulanıyor…";
  try {
    const [nodesCsv, edgesCsv] = await Promise.all([nodesFile.text(), edgesFile.text()]);
    const selectedProject = availableProjects.find(project => project.id === currentProjectId);
    if (!selectedProject) throw new Error("Yeni sürüm için aktif bir proje seçmelisin.");
    const response = await apiFetch("/api/projects/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project_id: currentProjectId,
        name: selectedProject.name,
        nodes_csv: nodesCsv,
        edges_csv: edgesCsv
      })
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Grafik yüklenemedi.");
    currentProjectId = result.project_id;
    document.querySelector("#dataBadge").lastChild.textContent = " Yüklenen CSV verisi";
    importStatus.className = "import-status success";
    importStatus.textContent = `${result.message} ${result.node_count} düğüm, ${result.edge_count} ilişki.`;
    await loadAvailableProjects(result.project_id);
  } catch (error) {
    importStatus.className = "import-status error";
    importStatus.textContent = error.message;
  } finally {
    importButton.disabled = false;
    importButton.textContent = "Yeni sürümü yükle";
  }
}

function openDrawer(item) {
  if (!item) return;
  document.querySelector("#drawerTitle").textContent = `${item.id} · ${item.label}`;
  const risk = document.querySelector("#drawerRisk");
  risk.textContent = `${riskLabel(item.risk)} risk · ${item.score}/100`;
  risk.className = `drawer-risk ${item.risk}`;
  document.querySelector("#drawerType").textContent = item.type;
  document.querySelector("#drawerOwner").textContent = item.owner;
  document.querySelector("#drawerPath").textContent = item.path;
  document.querySelector("#drawerReason").textContent = item.reason;
  document.querySelector("#detailDrawer").classList.add("open");
  document.querySelector("#detailDrawer").setAttribute("aria-hidden", "false");
  document.querySelector("#drawerScrim").classList.add("open");
}

function closeDrawer() {
  document.querySelector("#detailDrawer").classList.remove("open");
  document.querySelector("#detailDrawer").setAttribute("aria-hidden", "true");
  document.querySelector("#drawerScrim").classList.remove("open");
}

function exportCsv() {
  if (!analyzed || !lastAnalysis) return;
  const safeCell = value => {
    const text = String(value);
    return /^[\s]*[=+\-@]/.test(text) ? `'${text}` : text;
  };
  const rows = [
    ["Analiz", currentAnalysisId],
    ["Grafik sürümü", lastAnalysis.graph_version],
    ["Kayıt zamanı", lastAnalysis.created_at],
    ["Varlık", "Tür", "Kanıt yolu", "Risk", "Puan", "Durum", "Gerekçe"],
    ...currentScenario.items.map(item => [item.id, item.type, item.path, riskLabel(item.risk), item.score, item.status, item.reason])
  ];
  const csv = rows.map(row => row.map(value => `"${safeCell(value).replaceAll('"', '""')}"`).join(",")).join("\n");
  const blob = new Blob(["\ufeff", csv], { type: "text/csv;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `${currentAnalysisId}-nextrace-etki-kanitlari.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
}

function buildAuditLog() {
  const timeline = document.querySelector("#auditTimeline");
  if (!lastAnalysis) { timeline.textContent = "Henüz analiz oluşturulmadı."; return; }
  document.querySelector("#auditVersion").textContent = `v${lastAnalysis.graph_version_number}`;
  const event = document.createElement("div");
  event.className = "audit-event";
  for (const [tag, text] of [["time", lastAnalysis.created_at], ["strong", "Analiz kaydedildi"], ["span", `${currentAnalysisId} · Grafik v${lastAnalysis.graph_version_number} (${lastAnalysis.graph_version}) · ${lastAnalysis.changed_node}`]]) {
    const element = document.createElement(tag);
    element.textContent = text;
    event.append(element);
  }
  timeline.replaceChildren(event);
}

document.querySelectorAll(".nav-item").forEach(button => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach(item => item.classList.toggle("active", item === button));
    document.querySelectorAll(".view").forEach(view => view.classList.toggle("active", view.dataset.viewPanel === button.dataset.view));
    if (button.dataset.view === "access") loadAccessData();
    if (button.dataset.view === "versions") loadProjectVersions();
    if (button.dataset.view === "connectors") loadConnectorStatus();
  });
});

document.querySelectorAll(".filter").forEach(button => {
  button.addEventListener("click", () => {
    currentFilter = button.dataset.filter;
    document.querySelectorAll(".filter").forEach(item => item.classList.toggle("active", item === button));
    if (analyzed) renderTable();
  });
});

scenarioSelect.addEventListener("change", updateScenarioText);
projectSelect.addEventListener("change", () => {
  currentProjectId = projectSelect.value;
  if (isSeedProject()) changedNodeInput.value = currentScenario.sourceNode;
  else changedNodeInput.value = "";
  resetAnalysis();
  applySelectedProjectAccess();
  if (document.querySelector('[data-view-panel="versions"]').classList.contains("active")) loadProjectVersions();
});
analyzeButton.addEventListener("click", runAnalysis);
importButton.addEventListener("click", importGraph);
compareVersionsButton.addEventListener("click", compareProjectVersions);
document.querySelector("#connectorSyncForm").addEventListener("submit", syncConnectors);
document.querySelector("#createUserForm").addEventListener("submit", async event => {
  event.preventDefault();
  const status = document.querySelector("#createUserStatus");
  status.className = "admin-status";
  status.textContent = "Kullanıcı oluşturuluyor…";
  try {
    const response = await apiFetch("/api/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: document.querySelector("#newUserEmail").value,
        password: document.querySelector("#newUserPassword").value,
        role: document.querySelector("#newUserRole").value
      })
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Kullanıcı oluşturulamadı.");
    status.textContent = `${result.user.email} hesabı oluşturuldu.`;
    event.target.reset();
    await loadAccessData();
  } catch (error) {
    status.className = "admin-status error";
    status.textContent = error.message;
  }
});
document.querySelector("#assignAccessForm").addEventListener("submit", async event => {
  event.preventDefault();
  const status = document.querySelector("#assignAccessStatus");
  status.className = "admin-status";
  status.textContent = "Erişim kaydediliyor…";
  try {
    const response = await apiFetch("/api/projects/access", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: document.querySelector("#accessUser").value,
        project_id: document.querySelector("#accessProject").value,
        access_level: document.querySelector("#accessLevel").value
      })
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Erişim kaydedilemedi.");
    status.textContent = result.message;
    await loadAccessData();
  } catch (error) {
    status.className = "admin-status error";
    status.textContent = error.message;
  }
});
document.querySelector("#accountUser").addEventListener("change", syncSelectedAccountStatus);
document.querySelector("#resetPasswordForm").addEventListener("submit", async event => {
  event.preventDefault();
  const status = document.querySelector("#accountStatus");
  status.className = "admin-status";
  status.textContent = "Geçici parola atanıyor…";
  try {
    const response = await apiFetch("/api/users/password-reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: document.querySelector("#accountUser").value,
        new_password: document.querySelector("#temporaryPassword").value
      })
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Parola sıfırlanamadı.");
    status.textContent = result.message;
    event.target.reset();
    await loadAccessData();
  } catch (error) {
    status.className = "admin-status error";
    status.textContent = error.message;
  }
});
document.querySelector("#accountStatusForm").addEventListener("submit", async event => {
  event.preventDefault();
  const status = document.querySelector("#accountStatus");
  status.className = "admin-status";
  status.textContent = "Hesap durumu güncelleniyor…";
  try {
    const response = await apiFetch("/api/users/status", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: document.querySelector("#accountUser").value,
        active: document.querySelector("#accountActive").value === "true"
      })
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Hesap durumu güncellenemedi.");
    status.textContent = result.message;
    await loadAccessData();
  } catch (error) {
    status.className = "admin-status error";
    status.textContent = error.message;
  }
});
authForm.addEventListener("submit", async event => {
  event.preventDefault();
  authMessage.textContent = "";
  const submit = document.querySelector("#authSubmit");
  submit.disabled = true;
  submit.textContent = setupRequired ? "Hesap oluşturuluyor…" : "Giriş yapılıyor…";
  try {
    const response = await fetch(setupRequired ? "/api/auth/setup" : "/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: document.querySelector("#authEmail").value,
        password: document.querySelector("#authPassword").value
      })
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Kimlik doğrulama başarısız.");
    hideAuthGate(result.user);
  } catch (error) {
    authMessage.textContent = error.message;
  } finally {
    submit.disabled = false;
    submit.textContent = setupRequired ? "Yönetici hesabını oluştur" : "Giriş yap";
  }
});
passwordButton.addEventListener("click", () => showPasswordGate(false));
passwordCancel.addEventListener("click", hidePasswordGate);
passwordForm.addEventListener("submit", async event => {
  event.preventDefault();
  passwordMessage.textContent = "";
  const newPassword = document.querySelector("#newPassword").value;
  if (newPassword !== document.querySelector("#newPasswordConfirm").value) {
    passwordMessage.textContent = "Yeni parola alanları birbiriyle eşleşmiyor.";
    return;
  }
  const submit = document.querySelector("#passwordSubmit");
  submit.disabled = true;
  submit.textContent = "Güncelleniyor…";
  try {
    const response = await fetch("/api/auth/password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        current_password: document.querySelector("#currentPassword").value,
        new_password: newPassword
      })
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Parola güncellenemedi.");
    passwordChangeForced = false;
    passwordGate.hidden = true;
    hideAuthGate(result.user);
  } catch (error) {
    passwordMessage.textContent = error.message;
  } finally {
    submit.disabled = false;
    submit.textContent = "Parolayı güncelle";
  }
});
logoutButton.addEventListener("click", async () => {
  await fetch("/api/auth/logout", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}"
  });
  currentUser = null;
  passwordChangeForced = false;
  showAuthGate(false);
});
document.querySelector("#drawerClose").addEventListener("click", closeDrawer);
document.querySelector("#drawerScrim").addEventListener("click", closeDrawer);
document.querySelector("#exportButton").addEventListener("click", exportCsv);
document.querySelector("#exportButtonSecondary").addEventListener("click", exportCsv);

resetAnalysis();
initializeAuth();

changedNodeInput.addEventListener("input", resetAnalysis);
