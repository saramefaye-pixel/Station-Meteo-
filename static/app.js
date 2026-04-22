/**
 * app.js v2 — Station Météo Agricole AgroTic
 * Alertes intelligentes + Recommandations agronomiques + Dashboard
 */
"use strict";

let chartInstance = null;
let niveauFiltreAlerte = "";

// ─── Seuils pour colorer les valeurs dans le tableau ─────────────────────────
const SEUILS = {
  temperature: { critique_haut:40, warning_haut:35, warning_bas:10, critique_bas:5 },
  humidite:    { critique_bas:20, warning_bas:30, warning_haut:85, critique_haut:95 },
  ph_sol:      { critique_bas:5.0, warning_bas:5.5, warning_haut:8.0, critique_haut:8.5 },
};

function etatValeur(type, valeur) {
  const s = SEUILS[type];
  if (!s) return { label: "—", cls: "" };
  if (type === "temperature") {
    if (valeur >= s.critique_haut || valeur <= s.critique_bas) return { label: "🔴 Critique", cls: "etat-critique" };
    if (valeur >= s.warning_haut  || valeur <= s.warning_bas)  return { label: "🟡 Warning",  cls: "etat-warning"  };
  } else if (type === "humidite") {
    if (valeur <= s.critique_bas || valeur >= s.critique_haut) return { label: "🔴 Critique", cls: "etat-critique" };
    if (valeur <= s.warning_bas  || valeur >= s.warning_haut)  return { label: "🟡 Warning",  cls: "etat-warning"  };
  } else if (type === "ph_sol") {
    if (valeur <= s.critique_bas || valeur >= s.critique_haut) return { label: "🔴 Critique", cls: "etat-critique" };
    if (valeur <= s.warning_bas  || valeur >= s.warning_haut)  return { label: "🟡 Warning",  cls: "etat-warning"  };
  }
  return { label: "✅ Normal", cls: "etat-ok" };
}

// ─── Init ────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  configurerOnglets();
  chargerParcelles();
  chargerTout();
  setInterval(chargerTout, 60_000);
});

function configurerOnglets() {
  document.querySelectorAll(".tab").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
    });
  });
}

// ─── Chargement global ───────────────────────────────────────────────────────
async function chargerTout() {
  const icon = document.getElementById("refreshIcon");
  icon.classList.add("spin");
  try {
    await Promise.all([
      verifierStatut(),
      chargerMesures(),
      chargerAnomalies(),
      chargerAggregation(),
      chargerAlertes(),
      chargerRecommandations(),
    ]);
  } finally {
    icon.classList.remove("spin");
  }
}

// ─── Statut ──────────────────────────────────────────────────────────────────
async function verifierStatut() {
  const badge = document.getElementById("statusBadge");
  const texte = document.getElementById("statusText");
  const statsEl = document.getElementById("statsGrid");
  try {
    const data = await fetchJson("/api/status");
    if (data.ok) {
      badge.className = "status-badge connected";
      texte.textContent = "Connecté";
      statsEl.innerHTML = `
        <div class="stat-card">
          <div class="label">Total mesures</div>
          <div class="value">${data.nb_mesures}</div>
          <div class="unit">enregistrements</div>
        </div>
        <div class="stat-card">
          <div class="label">Capteurs actifs</div>
          <div class="value">${data.nb_capteurs}</div>
          <div class="unit">capteurs IoT</div>
        </div>
        <div class="stat-card">
          <div class="label">Fréquence</div>
          <div class="value">1</div>
          <div class="unit">mesure / minute</div>
        </div>
        <div class="stat-card">
          <div class="label">Mise à jour</div>
          <div class="value" style="font-size:1rem;">${heureActuelle()}</div>
          <div class="unit">heure locale</div>
        </div>
      `;
    } else {
      badge.className = "status-badge error";
      texte.textContent = "Erreur MongoDB";
    }
  } catch(e) {
    badge.className = "status-badge error";
    texte.textContent = "Hors ligne";
  }
}

// ─── Mesures ─────────────────────────────────────────────────────────────────
async function chargerMesures() {
  const parcelle = document.getElementById("selectParcelle").value;
  const type     = document.getElementById("selectType").value;
  const limite   = document.getElementById("selectLimite").value;
  const tbody    = document.getElementById("tbodyMesures");
  tbody.innerHTML = `<tr><td colspan="7" class="empty">Chargement…</td></tr>`;
  const params = new URLSearchParams();
  if (parcelle) params.set("parcelle", parcelle);
  if (type)     params.set("type", type);
  params.set("limite", limite);
  try {
    const data = await fetchJson("/api/mesures?" + params);
    if (!data.length) {
      tbody.innerHTML = `<tr><td colspan="7" class="empty">Aucune mesure trouvée.</td></tr>`;
      return;
    }
    tbody.innerHTML = data.map(m => {
      const etat = etatValeur(m.type, m.valeur);
      return `<tr>
        <td>${m.timestamp}</td>
        <td>${m.capteur_id}</td>
        <td>${m.parcelle}</td>
        <td><span class="type-badge badge-${m.type}">${libelle(m.type)}</span></td>
        <td><strong>${m.valeur}</strong></td>
        <td>${m.unite}</td>
        <td class="${etat.cls}">${etat.label}</td>
      </tr>`;
    }).join("");
  } catch(e) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty">Erreur : ${e.message}</td></tr>`;
  }
}

// ─── Anomalies ───────────────────────────────────────────────────────────────
async function chargerAnomalies() {
  const parcelle = document.getElementById("selectParcelle").value;
  const tbody = document.getElementById("tbodyAnomalies");
  const params = new URLSearchParams();
  if (parcelle) params.set("parcelle", parcelle);
  try {
    const data = await fetchJson("/api/anomalies?" + params);
    if (!data.length) {
      tbody.innerHTML = `<tr><td colspan="5" class="empty">✅ Aucune anomalie détectée.</td></tr>`;
      return;
    }
    tbody.innerHTML = data.map(m => {
      const n = m.valeur < 20
        ? `<span class="etat-critique">🔴 Critique</span>`
        : `<span class="etat-warning">🟡 Avertissement</span>`;
      return `<tr>
        <td>${m.timestamp}</td><td>${m.capteur_id}</td>
        <td>${m.parcelle}</td><td><strong>${m.valeur} %</strong></td><td>${n}</td>
      </tr>`;
    }).join("");
  } catch(e) {
    tbody.innerHTML = `<tr><td colspan="5" class="empty">Erreur : ${e.message}</td></tr>`;
  }
}

// ─── Alertes intelligentes ───────────────────────────────────────────────────
async function chargerAlertes() {
  await chargerResumeAlertes();
  await afficherAlertes(niveauFiltreAlerte);
}

async function chargerResumeAlertes() {
  try {
    const data = await fetchJson("/api/alertes/resume");
    const compteurs = document.getElementById("alerteCompteurs");
    const badge     = document.getElementById("badgeAlertes");
    const banniere  = document.getElementById("banniereAlerte");

    const total = data.critiques + data.warnings;

    // Compteurs dans le header
    if (total > 0) {
      compteurs.style.display = "flex";
      document.getElementById("cptCritique").textContent = `${data.critiques} critique${data.critiques > 1 ? "s" : ""}`;
      document.getElementById("cptWarning").textContent  = `${data.warnings} warning${data.warnings > 1 ? "s" : ""}`;
    } else {
      compteurs.style.display = "none";
    }

    // Badge sur l'onglet
    if (total > 0) {
      badge.style.display = "inline-block";
      badge.textContent = total;
    } else {
      badge.style.display = "none";
    }

    // Bannière critique
    if (data.critiques > 0) {
      banniere.style.display = "flex";
      document.getElementById("banniereTexte").textContent =
        `${data.critiques} alerte(s) critique(s) détectée(s) sur vos parcelles ! Vérifiez l'onglet Alertes.`;
    }
  } catch(e) {}
}

async function afficherAlertes(niveau) {
  const liste = document.getElementById("alertesListe");
  const parcelle = document.getElementById("selectParcelle").value;
  liste.innerHTML = `<div class="empty">Chargement…</div>`;
  const params = new URLSearchParams({ limite: 40 });
  if (niveau)   params.set("niveau", niveau);
  if (parcelle) params.set("parcelle", parcelle);
  try {
    const data = await fetchJson("/api/alertes?" + params);
    if (!data.length) {
      liste.innerHTML = `<div class="empty">✅ Aucune alerte${niveau ? " de ce type" : ""} pour le moment.</div>`;
      return;
    }
    liste.innerHTML = data.map(a => `
      <div class="alerte-card ${a.niveau}">
        <div class="alerte-icone">${a.icone}</div>
        <div class="alerte-body">
          <div class="alerte-titre">${a.titre}</div>
          <div class="alerte-message">${a.message}</div>
          <div class="alerte-reco">💡 ${a.recommandation}</div>
        </div>
        <div class="alerte-meta">
          <div class="alerte-ts">${a.timestamp ? a.timestamp.slice(11,16) : ""}</div>
          <div class="alerte-parcelle">${a.parcelle}</div>
        </div>
      </div>
    `).join("");
  } catch(e) {
    liste.innerHTML = `<div class="empty">Erreur : ${e.message}</div>`;
  }
}

function filtrerAlertes(niveau) {
  niveauFiltreAlerte = niveau;
  document.querySelectorAll(".btn-filtre").forEach(b => b.classList.remove("active"));
  const map = { "": "fAll", "critique": "fCritique", "warning": "fWarning" };
  const el = document.getElementById(map[niveau]);
  if (el) el.classList.add("active");
  afficherAlertes(niveau);
}

// ─── Recommandations agronomiques ────────────────────────────────────────────
async function chargerRecommandations() {
  const grid = document.getElementById("recoGrid");
  const parcelle = document.getElementById("selectParcelle").value;
  const params = new URLSearchParams();
  if (parcelle) params.set("parcelle", parcelle);
  try {
    const data = await fetchJson("/api/recommandations?" + params);
    if (!data.length) {
      grid.innerHTML = `<div class="reco-card loading">Pas encore de données. Patientez 1 minute...</div>`;
      return;
    }
    grid.innerHTML = data.map(r => `
      <div class="reco-card statut-${r.statut}">
        <div class="reco-parcelle">🌿 ${r.parcelle}</div>
        <div class="reco-statut">${r.icone} ${r.statut.charAt(0).toUpperCase() + r.statut.slice(1)}</div>
        <div class="reco-conseil">${r.conseil}</div>
        <div class="reco-valeurs">
          <span class="reco-val">🌡️ ${r.temperature}°C</span>
          <span class="reco-val">💧 ${r.humidite}%</span>
          <span class="reco-val">⚗️ pH ${r.ph_sol}</span>
        </div>
      </div>
    `).join("");
  } catch(e) {
    grid.innerHTML = `<div class="reco-card loading">Erreur : ${e.message}</div>`;
  }
}

// ─── Agrégation ──────────────────────────────────────────────────────────────
async function chargerAggregation() {
  const conteneur = document.getElementById("agregCards");
  conteneur.innerHTML = `<div class="agreg-card loading">Chargement…</div>`;
  try {
    const data = await fetchJson("/api/stats/temperature");
    if (!data.length) {
      conteneur.innerHTML = `<div class="agreg-card loading">Pas encore de données sur 24h.</div>`;
      return;
    }
    conteneur.innerHTML = data.map(d => `
      <div class="agreg-card">
        <div class="parcelle-title">🌿 ${d.parcelle}</div>
        <div class="metric"><span class="metric-label">Moyenne (24h)</span><span class="metric-value moyenne">${d.moyenne} °C</span></div>
        <div class="metric"><span class="metric-label">Minimum</span><span class="metric-value">${d.min} °C</span></div>
        <div class="metric"><span class="metric-label">Maximum</span><span class="metric-value">${d.max} °C</span></div>
        <div class="metric"><span class="metric-label">Nb. mesures</span><span class="metric-value">${d.nb_mesures}</span></div>
      </div>
    `).join("");
  } catch(e) {
    conteneur.innerHTML = `<div class="agreg-card loading">Erreur : ${e.message}</div>`;
  }
}

// ─── Parcelles & Graphique ───────────────────────────────────────────────────
async function chargerParcelles() {
  try {
    const [parcelles, capteurs] = await Promise.all([
      fetchJson("/api/parcelles"),
      fetchJson("/api/capteurs"),
    ]);
    const sel = document.getElementById("selectParcelle");
    parcelles.forEach(p => {
      const o = document.createElement("option");
      o.value = p; o.textContent = p;
      sel.appendChild(o);
    });
    const selC = document.getElementById("selectCapteurGraph");
    capteurs.forEach(c => {
      const o = document.createElement("option");
      o.value = c.capteur_id;
      o.textContent = `${c.capteur_id} — ${c.parcelle} (${libelle(c.type)})`;
      selC.appendChild(o);
    });
    if (capteurs.length) chargerGraphique();
  } catch(e) {}
}

async function chargerGraphique() {
  const capteurId = document.getElementById("selectCapteurGraph").value;
  const heures    = document.getElementById("selectHeures").value;
  const emptyMsg  = document.getElementById("chartEmpty");
  const canvas    = document.getElementById("chartEvolution");
  if (!capteurId) return;
  try {
    const data = await fetchJson(`/api/evolution?capteur_id=${capteurId}&heures=${heures}`);
    if (!data.length) {
      canvas.style.display = "none"; emptyMsg.style.display = "block"; return;
    }
    canvas.style.display = "block"; emptyMsg.style.display = "none";
    const labels   = data.map(d => d.heure.slice(11, 16));
    const moyennes = data.map(d => d.moyenne);
    const mins     = data.map(d => d.min);
    const maxs     = data.map(d => d.max);
    if (chartInstance) chartInstance.destroy();
    chartInstance = new Chart(canvas, {
      type: "line",
      data: {
        labels,
        datasets: [
          { label: "Moyenne", data: moyennes, borderColor: "#2d6a4f", backgroundColor: "rgba(45,106,79,0.1)", borderWidth: 2.5, pointRadius: 4, tension: 0.4, fill: true },
          { label: "Min",     data: mins,     borderColor: "#52b788", borderWidth: 1.5, borderDash:[5,5], pointRadius: 2, tension: 0.4, fill: false },
          { label: "Max",     data: maxs,     borderColor: "#e9c46a", borderWidth: 1.5, borderDash:[5,5], pointRadius: 2, tension: 0.4, fill: false },
        ],
      },
      options: {
        responsive: true,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { position: "top" },
          title: { display: true, text: `Évolution horaire — ${capteurId} (${heures}h)`, font: { size: 14, weight:"600" }, color: "#1a3a2a" },
        },
        scales: {
          y: { grid: { color: "rgba(45,106,79,0.1)" }, ticks: { font: { family: "Space Mono" } } },
          x: { grid: { display: false }, ticks: { font: { family: "Space Mono", size: 11 } } },
        },
      },
    });
  } catch(e) {}
}

// ─── Utilitaires ─────────────────────────────────────────────────────────────
async function fetchJson(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  const d = await r.json();
  if (d.erreur) throw new Error(d.erreur);
  return d;
}
function libelle(type) {
  return { temperature:"Température", humidite:"Humidité", ph_sol:"pH sol" }[type] || type;
}
function heureActuelle() {
  return new Date().toLocaleTimeString("fr-FR", { hour:"2-digit", minute:"2-digit", second:"2-digit" });
}
