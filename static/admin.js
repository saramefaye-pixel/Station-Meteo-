"use strict";

// ─── Init ────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  chargerTout();
  // Rafraîchissement automatique toutes les 10s pour les sessions, 60s pour le reste
  setInterval(chargerSessions, 10_000);
  setInterval(chargerStats, 60_000);
  setInterval(chargerAlertesRecentes, 60_000);
});

async function chargerTout() {
  await Promise.all([
    chargerStats(),
    chargerSessions(),
    chargerAlertesRecentes(),
  ]);
}

// ─── Statistiques globales ────────────────────────────────────────────────────
async function chargerStats() {
  const el = document.getElementById("adminStats");
  const colEl = document.getElementById("collectionsGrid");
  try {
    const d = await fetchJson("/api/admin/stats");
    el.innerHTML = `
      <div class="admin-stat-card">
        <div class="label">Mesures totales</div>
        <div class="value">${d.nb_mesures_total}</div>
        <div class="unit">documents MongoDB</div>
      </div>
      <div class="admin-stat-card bleu">
        <div class="label">Mesures (1 dernière heure)</div>
        <div class="value">${d.nb_mesures_1h}</div>
        <div class="unit">nouvelles mesures</div>
      </div>
      <div class="admin-stat-card rouge">
        <div class="label">Alertes critiques (1h)</div>
        <div class="value">${d.nb_alertes_critiques}</div>
        <div class="unit">alertes actives</div>
      </div>
      <div class="admin-stat-card ambre">
        <div class="label">Avertissements (1h)</div>
        <div class="value">${d.nb_alertes_warnings}</div>
        <div class="unit">warnings actifs</div>
      </div>
      <div class="admin-stat-card">
        <div class="label">Capteurs IoT</div>
        <div class="value">${d.nb_capteurs}</div>
        <div class="unit">sur ${d.nb_parcelles} parcelles</div>
      </div>
      <div class="admin-stat-card">
        <div class="label">Heure serveur</div>
        <div class="value" style="font-size:1.1rem;">${d.heure_serveur}</div>
        <div class="unit">temps universel</div>
      </div>
    `;
    // Collections
    const cols = d.collections;
    colEl.innerHTML = Object.entries(cols).map(([nom, count]) => `
      <div class="collection-card">
        <div class="collection-nom">${nom}</div>
        <div class="collection-count">${count}</div>
        <div class="collection-unit">documents</div>
      </div>
    `).join("");
  } catch(e) {
    el.innerHTML = `<div class="admin-stat-card loading">Erreur : ${e.message}</div>`;
  }
}

// ─── Sessions actives ─────────────────────────────────────────────────────────
async function chargerSessions() {
  const el = document.getElementById("sessionsListe");
  try {
    const data = await fetchJson("/api/admin/sessions");
    if (!data.length) {
      el.innerHTML = `<div class="empty">Aucun utilisateur connecté en ce moment.</div>`;
      return;
    }
    el.innerHTML = data.map(s => `
      <div class="session-card">
        <div class="session-avatar">${s.avatar}</div>
        <div class="session-info">
          <div class="session-nom">${s.nom_complet} <span class="session-badge ${s.role}">${s.role}</span></div>
          <div class="session-detail">@${s.username} — connecté depuis ${s.depuis}</div>
        </div>
        <div class="session-duree">${s.duree_min} min</div>
      </div>
    `).join("");
  } catch(e) {
    el.innerHTML = `<div class="empty">Erreur : ${e.message}</div>`;
  }
}

// ─── Alertes récentes ─────────────────────────────────────────────────────────
async function chargerAlertesRecentes() {
  const tbody = document.getElementById("tbodyAlertesAdmin");
  try {
    const data = await fetchJson("/api/admin/alertes_recentes");
    if (!data.length) {
      tbody.innerHTML = `<tr><td colspan="5" class="empty">Aucune alerte.</td></tr>`;
      return;
    }
    tbody.innerHTML = data.map(a => `
      <tr>
        <td>${a.timestamp ? a.timestamp.slice(11,19) : "—"}</td>
        <td><span class="${a.niveau==="critique"?"alerte-critique":"alerte-warning"}">${a.icone} ${a.niveau}</span></td>
        <td>${a.parcelle}</td>
        <td style="font-weight:600;">${a.titre}</td>
        <td style="font-size:0.8rem;color:var(--texte-doux);">${a.recommandation}</td>
      </tr>
    `).join("");
  } catch(e) {
    tbody.innerHTML = `<tr><td colspan="5" class="empty">Erreur : ${e.message}</td></tr>`;
  }
}

// ─── Action : vider les anciennes mesures ─────────────────────────────────────
async function viderMesures() {
  const msg = document.getElementById("msgVider");
  if (!confirm("Supprimer les mesures de plus de 7 jours ? Cette action est irréversible.")) return;
  try {
    const data = await fetchJson("/api/admin/vider_mesures", "POST");
    msg.className = "action-msg ok";
    msg.textContent = `✅ ${data.supprimees} mesures supprimées avec succès.`;
    chargerStats();
  } catch(e) {
    msg.className = "action-msg err";
    msg.textContent = `❌ Erreur : ${e.message}`;
  }
}

// ─── Utilitaire fetch ─────────────────────────────────────────────────────────
async function fetchJson(url, method="GET") {
  const opts = { method };
  if (method === "POST") opts.headers = { "Content-Type": "application/json" };
  const r = await fetch(url, opts);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  const d = await r.json();
  if (d.erreur) throw new Error(d.erreur);
  return d;
}
