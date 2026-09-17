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
let currentScenario = scenarios.latency;
let currentFilter = "all";
let analyzed = false;
let currentProjectId = "demo";
let currentAnalysisId = null;

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
    const response = await fetch("/api/analyze", {
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
    const projectId = `uploaded-${Date.now()}`;
    const response = await fetch("/api/projects/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_id: projectId, nodes_csv: nodesCsv, edges_csv: edgesCsv })
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Grafik yüklenemedi.");
    currentProjectId = result.project_id;
    document.querySelector("#dataBadge").lastChild.textContent = " Yüklenen CSV verisi";
    importStatus.className = "import-status success";
    importStatus.textContent = `Aktif veri kümesi: ${result.node_count} düğüm, ${result.edge_count} ilişki`;
    resetAnalysis();
  } catch (error) {
    importStatus.className = "import-status error";
    importStatus.textContent = error.message;
  } finally {
    importButton.disabled = false;
    importButton.textContent = "Grafiği yükle";
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
analyzeButton.addEventListener("click", runAnalysis);
importButton.addEventListener("click", importGraph);
document.querySelector("#drawerClose").addEventListener("click", closeDrawer);
document.querySelector("#drawerScrim").addEventListener("click", closeDrawer);
document.querySelector("#markReviewed").addEventListener("click", () => {
  document.querySelector("#markReviewed").textContent = "İncelendi ✓";
  document.querySelector("#markReviewed").disabled = true;
});
document.querySelector("#exportButton").addEventListener("click", exportCsv);
document.querySelector("#exportButtonSecondary").addEventListener("click", exportCsv);

buildAuditLog();
