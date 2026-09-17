const scenarios = {
  latency: {
    id: "CR-028",
    sourceNode: "SYS-REQ-142",
    current: "250 ms",
    proposed: "150 ms",
    description: "SYS-REQ-142 telemetri paketlerinin en yüksek yük altında uçtan uca iletim eşiğini düşürür.",
    confidence: 92,
    summary: "Yüksek etkili değişiklik",
    note: "Üç kritik varlık aynı sürüm hedefinde. Canlıya alımdan önce arayüz, zamanlayıcı ve yük testinin birlikte güncellenmesi gerekir.",
    pathCount: 5,
    items: [
      { id: "INT-017", label: "Telemetri API sözleşmesi", type: "Arayüz", risk: "critical", score: 93, owner: "Sistem Mühendisliği", path: "SYS-REQ-142 → INT-017", reason: "Yanıt süresi sözleşmesi doğrudan 250 ms eşiğini referanslıyor.", status: "İnceleme gerekli" },
      { id: "SW-203", label: "Paket zamanlayıcı", type: "Yazılım", risk: "critical", score: 89, owner: "Gömülü Yazılım", path: "SYS-REQ-142 → INT-017 → SW-203", reason: "Zamanlayıcı kuyruğu mevcut gecikme bütçesine göre yapılandırılmış.", status: "İnceleme gerekli" },
      { id: "TC-408", label: "Tepe yük testi", type: "Test", risk: "critical", score: 91, owner: "Doğrulama", path: "SYS-REQ-142 → TC-408", reason: "Kabul kriteri 250 ms üst sınırını doğruluyor; test verisi ve eşik güncellenmeli.", status: "Bloke" },
      { id: "SAF-09", label: "Telemetri hazard kaydı", type: "Güvenlik", risk: "high", score: 84, owner: "Emniyet", path: "SYS-REQ-142 → INT-017 → SAF-09", reason: "Paket kaybı olasılığı düşük gecikme hedefiyle yeniden değerlendirilmelidir.", status: "Atanmadı" },
      { id: "CFG-12", label: "Timeout yapılandırması", type: "Konfigürasyon", risk: "high", score: 81, owner: "DevOps", path: "INT-017 → CFG-12", reason: "Üretim timeout değeri yeni hedefin üzerinde kalıyor.", status: "Atanmadı" },
      { id: "TC-412", label: "Yeniden deneme testi", type: "Test", risk: "medium", score: 77, owner: "Doğrulama", path: "SW-203 → TC-412", reason: "Retry penceresi toplam gecikme bütçesini aşabilir.", status: "Planlandı" },
      { id: "DOC-77", label: "Arayüz kontrol dokümanı", type: "Doküman", risk: "medium", score: 64, owner: "Konfigürasyon", path: "INT-017 → DOC-77", reason: "ICD-07 bölüm 4.2 eski zamanlama değerini içeriyor.", status: "Planlandı" },
      { id: "REL-31", label: "Sürüm temel çizgisi", type: "Sürüm", risk: "medium", score: 58, owner: "Konfigürasyon", path: "SW-203 → REL-31", reason: "Değişiklik, dondurulmuş uçuş yazılımı temel çizgisini etkiliyor.", status: "Onay bekliyor" }
    ]
  },
  encryption: {
    id: "CR-031",
    sourceNode: "SEC-REQ-055",
    current: "AES-128",
    proposed: "AES-256",
    description: "SEC-REQ-055 yer istasyonu ile hava aracı arasındaki telemetri şifreleme standardını yükseltir.",
    confidence: 88,
    summary: "Güvenlik odaklı değişiklik",
    note: "Anahtar yönetimi, işlemci yükü ve uyumluluk testleri aynı değişiklik paketi içinde ele alınmalıdır.",
    pathCount: 4,
    items: [
      { id: "SEC-API-4", label: "Kripto servis sözleşmesi", type: "Arayüz", risk: "critical", score: 94, owner: "Siber Güvenlik", path: "SEC-REQ-055 → SEC-API-4", reason: "Anahtar uzunluğu ve algoritma kimliği servis sözleşmesinde sabit.", status: "İnceleme gerekli" },
      { id: "SW-318", label: "Kripto sağlayıcı", type: "Yazılım", risk: "critical", score: 90, owner: "Platform Yazılımı", path: "SEC-API-4 → SW-318", reason: "Mevcut donanım hızlandırıcı yapılandırması AES-128 profilini kullanıyor.", status: "Bloke" },
      { id: "PERF-22", label: "CPU yük bütçesi", type: "Performans", risk: "high", score: 83, owner: "Sistem Mühendisliği", path: "SW-318 → PERF-22", reason: "Şifreleme maliyeti görev bilgisayarı işlem bütçesini etkileyebilir.", status: "Atanmadı" },
      { id: "TC-509", label: "Kripto uyumluluk testi", type: "Test", risk: "high", score: 80, owner: "Doğrulama", path: "SEC-REQ-055 → TC-509", reason: "Test vektörleri ve sertifika profili güncel algoritmayı kapsamıyor.", status: "Planlandı" },
      { id: "KEY-7", label: "Anahtar döndürme politikası", type: "Politika", risk: "medium", score: 68, owner: "Siber Güvenlik", path: "SEC-API-4 → KEY-7", reason: "Anahtar yaşam döngüsü belgesi algoritma değişikliğine bağlanmalı.", status: "Planlandı" },
      { id: "DOC-91", label: "Güvenlik tasarım dokümanı", type: "Doküman", risk: "medium", score: 61, owner: "Sistem Mühendisliği", path: "SEC-REQ-055 → DOC-91", reason: "Tehdit modeli ve algoritma seçimi bölümü eski standardı içeriyor.", status: "Onay bekliyor" }
    ]
  },
  sampling: {
    id: "CR-044",
    sourceNode: "SNS-REQ-021",
    current: "60 Hz",
    proposed: "100 Hz",
    description: "SNS-REQ-021 uçuş kontrol sensörlerinin örnekleme sıklığını artırır.",
    confidence: 86,
    summary: "Performans etkili değişiklik",
    note: "Veri yolu kapasitesi, filtre katsayıları ve gerçek zamanlı görev bütçesi birlikte doğrulanmalıdır.",
    pathCount: 4,
    items: [
      { id: "BUS-11", label: "Sensör veri yolu", type: "Arayüz", risk: "critical", score: 92, owner: "Aviyonik", path: "SNS-REQ-021 → BUS-11", reason: "Artan mesaj sıklığı veri yolu kullanım oranını yükseltiyor.", status: "İnceleme gerekli" },
      { id: "SW-141", label: "Sinyal filtreleme", type: "Yazılım", risk: "critical", score: 88, owner: "Uçuş Yazılımı", path: "SNS-REQ-021 → SW-141", reason: "Filtre katsayıları 60 Hz örnekleme periyoduna göre hesaplanmış.", status: "Bloke" },
      { id: "RT-06", label: "Gerçek zamanlı görev bütçesi", type: "Performans", risk: "high", score: 85, owner: "Sistem Mühendisliği", path: "SW-141 → RT-06", reason: "Görev yürütme süresi yeni periyotta zaman aşımına yaklaşabilir.", status: "Atanmadı" },
      { id: "TC-244", label: "Sensör bant genişliği testi", type: "Test", risk: "high", score: 79, owner: "Doğrulama", path: "BUS-11 → TC-244", reason: "Mevcut test yalnızca 60 Hz üst sınırını doğruluyor.", status: "Planlandı" },
      { id: "SIM-4", label: "Uçuş dinamiği modeli", type: "Simülasyon", risk: "medium", score: 67, owner: "Modelleme", path: "SW-141 → SIM-4", reason: "Simülasyon veri adımı yeni örnekleme süresiyle eşleşmiyor.", status: "Planlandı" },
      { id: "DOC-32", label: "Sensör ICD", type: "Doküman", risk: "medium", score: 59, owner: "Konfigürasyon", path: "BUS-11 → DOC-32", reason: "Mesaj periyodu ve bant genişliği tabloları güncellenmeli.", status: "Onay bekliyor" }
    ]
  }
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
const importCard = document.querySelector("#importCard");
const fromVersion = document.querySelector("#fromVersion");
const toVersion = document.querySelector("#toVersion");
const compareVersionsButton = document.querySelector("#compareVersionsButton");
const versionMessage = document.querySelector("#versionMessage");
let currentScenario = scenarios.latency;
let currentFilter = "all";
let analyzed = false;
let currentProjectId = "demo";
let currentAnalysisId = null;
let setupRequired = false;
let currentUser = null;
let availableProjects = [];
let currentVersions = [];
let passwordChangeForced = false;

function showAuthGate(requiresSetup = false) {
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
  importCard.hidden = !isAdmin;
  loadAvailableProjects();
  if (isAdmin) loadAccessData();
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
    if (currentProjectId === "demo") changedNodeInput.value = currentScenario.sourceNode;
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
  return { seed: "Başlangıç", csv: "CSV", migration: "Aktarılan" }[source] || source;
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

function syncSelectedAccountStatus() {
  const selected = document.querySelector("#accountUser").selectedOptions[0];
  if (!selected?.value) return;
  document.querySelector("#accountActive").value = selected.dataset.active === "true" ? "true" : "false";
}

function updateScenarioText() {
  currentScenario = scenarios[scenarioSelect.value];
  document.querySelector("#scenarioId").textContent = currentScenario.id;
  document.querySelector("#currentValue").textContent = currentScenario.current;
  document.querySelector("#proposedValue").textContent = currentScenario.proposed;
  document.querySelector("#scenarioDescription").textContent = currentScenario.description;
  if (currentProjectId === "demo") changedNodeInput.value = currentScenario.sourceNode;
  resetAnalysis();
}

function resetAnalysis() {
  analyzed = false;
  currentAnalysisId = null;
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
  document.querySelector("#summaryNote").textContent = "Analiz, izlenebilirlik grafiğindeki doğrulanmış ilişkileri ve sürüm bilgilerini kullanır.";
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
  document.querySelector("#confidenceRing").textContent = `%${currentScenario.confidence}`;
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
  const root = { id: changedNodeInput.value.trim(), label: "Değişiklik kaynağı", risk: "source", score: null };
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
        current_value: currentScenario.current,
        proposed_value: currentScenario.proposed
      })
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Analiz tamamlanamadı.");

    currentScenario = {
      ...currentScenario,
      items: result.items,
      confidence: result.confidence,
      summary: result.summary,
      note: result.note,
      pathCount: result.path_count
    };
    currentAnalysisId = result.analysis_id;
    analyzed = true;
    renderSummary();
    renderGraph();
    renderTable();
    graphStage.classList.add("analyzed");
    analysisState.className = "analysis-state complete";
    analysisState.innerHTML = `<span></span> Analiz tamamlandı · ${result.duration_ms} ms`;
    buildAuditLog();
  } catch (error) {
    analysisState.className = "analysis-state error";
    analysisState.innerHTML = "<span></span>";
    analysisState.append(document.createTextNode(` ${error.message}`));
  } finally {
    analyzeButton.disabled = false;
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
  const safeCell = value => {
    const text = String(value);
    return /^[=+\-@]/.test(text) ? `'${text}` : text;
  };
  const rows = [
    ["Analiz", currentScenario.id],
    ["Varlık", "Tür", "Kanıt yolu", "Risk", "Puan", "Durum", "Gerekçe"],
    ...currentScenario.items.map(item => [item.id, item.type, item.path, riskLabel(item.risk), item.score, item.status, item.reason])
  ];
  const csv = rows.map(row => row.map(value => `"${safeCell(value).replaceAll('"', '""')}"`).join(",")).join("\n");
  const blob = new Blob(["\ufeff", csv], { type: "text/csv;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `${currentScenario.id}-nextrace-etki-kanitlari.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
}

function buildAuditLog() {
  const analysisId = currentAnalysisId || "Henüz analiz oluşturulmadı";
  const events = [
    ["09:42:11", `${currentScenario.id} değişiklik girdisi kaydedildi`, "SYS-REQ kaynak sürümü: 7.3"],
    ["09:42:12", "İzlenebilirlik grafiği tarandı", `${currentScenario.items.length} etkilenmiş varlık, ${currentScenario.pathCount} kanıt yolu`],
    ["09:42:13", "Risk puanları üretildi", `Güven skoru: %${currentScenario.confidence}`],
    ["09:42:14", "Sonuç paketi kalıcı depoya kaydedildi", `Analiz kimliği: ${analysisId}`]
  ];
  document.querySelector("#auditTimeline").innerHTML = events.map(([time, title, meta]) => `
    <div class="audit-event"><time>${time}</time><strong>${title}</strong><span>${meta}</span></div>`).join("");
}

document.querySelectorAll(".nav-item").forEach(button => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach(item => item.classList.toggle("active", item === button));
    document.querySelectorAll(".view").forEach(view => view.classList.toggle("active", view.dataset.viewPanel === button.dataset.view));
    if (button.dataset.view === "access") loadAccessData();
    if (button.dataset.view === "versions") loadProjectVersions();
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
  if (currentProjectId === "demo") changedNodeInput.value = currentScenario.sourceNode;
  resetAnalysis();
  applySelectedProjectAccess();
  if (document.querySelector('[data-view-panel="versions"]').classList.contains("active")) loadProjectVersions();
});
analyzeButton.addEventListener("click", runAnalysis);
importButton.addEventListener("click", importGraph);
compareVersionsButton.addEventListener("click", compareProjectVersions);
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
document.querySelector("#markReviewed").addEventListener("click", () => {
  document.querySelector("#markReviewed").textContent = "İncelendi ✓";
  document.querySelector("#markReviewed").disabled = true;
});
document.querySelector("#exportButton").addEventListener("click", exportCsv);
document.querySelector("#exportButtonSecondary").addEventListener("click", exportCsv);

buildAuditLog();
initializeAuth();
