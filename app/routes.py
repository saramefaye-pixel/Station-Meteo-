"""
routes.py
Toutes les routes Flask :
  - GET /                        → page HTML principale
  - GET /api/parcelles           → liste des parcelles
  - GET /api/mesures             → mesures filtrables
  - GET /api/anomalies           → humidité < 30 %
  - GET /api/stats/temperature   → moyenne température par parcelle (24h)
  - GET /api/evolution           → évolution horaire d'un capteur
  - GET /api/status              → état de la connexion MongoDB
"""

from flask import Blueprint, jsonify, render_template, request
from datetime import datetime, timezone, timedelta
from app.database import get_db

bp = Blueprint("main", __name__)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _serialiser(doc: dict) -> dict:
    """Convertit un document MongoDB en dict JSON-compatible."""
    doc.pop("_id", None)
    if isinstance(doc.get("timestamp"), datetime):
        doc["timestamp"] = doc["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
    return doc


# ─── Page principale ──────────────────────────────────────────────────────────

@bp.route("/")
def index():
    return render_template("index.html")


# ─── API : état connexion ─────────────────────────────────────────────────────

@bp.route("/api/status")
def status():
    try:
        db = get_db()
        nb_mesures  = db.mesures.count_documents({})
        nb_capteurs = db.capteurs.count_documents({})
        return jsonify({
            "ok": True,
            "nb_mesures": nb_mesures,
            "nb_capteurs": nb_capteurs
        })
    except Exception as e:
        return jsonify({"ok": False, "erreur": str(e)}), 500


# ─── API : liste des parcelles ────────────────────────────────────────────────

@bp.route("/api/parcelles")
def parcelles():
    try:
        db = get_db()
        liste = db.capteurs.distinct("parcelle")
        return jsonify(sorted(liste))
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500


# ─── API : mesures (filtrables par parcelle et type) ─────────────────────────

@bp.route("/api/mesures")
def mesures():
    """
    Paramètres GET optionnels :
      - parcelle : filtre par parcelle (ex. "Parcelle A")
      - type     : filtre par type (temperature / humidite / ph_sol)
      - limite   : nombre max de résultats (défaut 100)
    """
    try:
        parcelle = request.args.get("parcelle")
        type_cap = request.args.get("type")
        limite   = int(request.args.get("limite", 100))

        db = get_db()
        filtre = {}
        if parcelle:
            filtre["parcelle"] = parcelle
        if type_cap:
            filtre["type"] = type_cap

        docs = (
            db.mesures.find(filtre)
            .sort("timestamp", -1)
            .limit(limite)
        )
        resultats = [_serialiser(d) for d in docs]
        return jsonify(resultats)
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500


# ─── API : anomalies (humidité < 30 %) ───────────────────────────────────────

@bp.route("/api/anomalies")
def anomalies():
    """
    Retourne les mesures d'humidité inférieures à 30 %.
    Paramètre GET optionnel : parcelle
    """
    try:
        parcelle = request.args.get("parcelle")
        db = get_db()

        filtre = {"type": "humidite", "valeur": {"$lt": 30}}
        if parcelle:
            filtre["parcelle"] = parcelle

        docs = (
            db.mesures.find(filtre)
            .sort("timestamp", -1)
            .limit(200)
        )
        resultats = [_serialiser(d) for d in docs]
        return jsonify(resultats)
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500


# ─── API : moyenne température par parcelle sur 24h (agrégation) ─────────────

@bp.route("/api/stats/temperature")
def stats_temperature():
    """
    Agrégation MongoDB :
    Moyenne de température par parcelle sur les dernières 24 heures.
    """
    try:
        db = get_db()
        hier = datetime.now(timezone.utc) - timedelta(hours=24)

        pipeline = [
            # Étape 1 : filtrer les mesures de température des 24 dernières heures
            {
                "$match": {
                    "type": "temperature",
                    "timestamp": {"$gte": hier}
                }
            },
            # Étape 2 : grouper par parcelle et calculer les statistiques
            {
                "$group": {
                    "_id": "$parcelle",
                    "moyenne":  {"$avg": "$valeur"},
                    "min":      {"$min": "$valeur"},
                    "max":      {"$max": "$valeur"},
                    "nb_mesures": {"$sum": 1}
                }
            },
            # Étape 3 : renommer _id en parcelle et arrondir
            {
                "$project": {
                    "_id": 0,
                    "parcelle":   "$_id",
                    "moyenne":    {"$round": ["$moyenne", 2]},
                    "min":        {"$round": ["$min", 2]},
                    "max":        {"$round": ["$max", 2]},
                    "nb_mesures": 1
                }
            },
            {"$sort": {"parcelle": 1}}
        ]

        resultats = list(db.mesures.aggregate(pipeline))
        return jsonify(resultats)
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500


# ─── API : évolution horaire d'un capteur ────────────────────────────────────

@bp.route("/api/evolution")
def evolution():
    """
    Évolution horaire moyenne d'un capteur donné.
    Paramètre GET obligatoire : capteur_id
    Paramètre GET optionnel  : heures (fenêtre temporelle, défaut 24)
    """
    try:
        capteur_id = request.args.get("capteur_id")
        heures     = int(request.args.get("heures", 24))

        if not capteur_id:
            return jsonify({"erreur": "Paramètre 'capteur_id' obligatoire."}), 400

        db = get_db()
        debut = datetime.now(timezone.utc) - timedelta(hours=heures)

        pipeline = [
            {
                "$match": {
                    "capteur_id": capteur_id,
                    "timestamp": {"$gte": debut}
                }
            },
            # Regroupe par heure
            {
                "$group": {
                    "_id": {
                        "heure": {"$dateToString": {
                            "format": "%Y-%m-%d %H:00",
                            "date": "$timestamp"
                        }}
                    },
                    "moyenne": {"$avg": "$valeur"},
                    "min":     {"$min": "$valeur"},
                    "max":     {"$max": "$valeur"},
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "heure":   "$_id.heure",
                    "moyenne": {"$round": ["$moyenne", 2]},
                    "min":     {"$round": ["$min", 2]},
                    "max":     {"$round": ["$max", 2]},
                }
            },
            {"$sort": {"heure": 1}}
        ]

        resultats = list(db.mesures.aggregate(pipeline))
        return jsonify(resultats)
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500


# ─── API : liste des capteurs ─────────────────────────────────────────────────

@bp.route("/api/capteurs")
def capteurs():
    try:
        parcelle = request.args.get("parcelle")
        db = get_db()
        filtre = {}
        if parcelle:
            filtre["parcelle"] = parcelle
        docs = list(db.capteurs.find(filtre, {"_id": 0}))
        return jsonify(docs)
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500


# ─── API : alertes intelligentes ─────────────────────────────────────────────

@bp.route("/api/alertes")
def alertes():
    """
    Retourne les alertes récentes (toutes parcelles ou filtrées).
    Paramètres GET optionnels : parcelle, niveau (critique/warning), limite
    """
    try:
        parcelle = request.args.get("parcelle")
        niveau   = request.args.get("niveau")
        limite   = int(request.args.get("limite", 50))

        db = get_db()
        filtre = {}
        if parcelle:
            filtre["parcelle"] = parcelle
        if niveau:
            filtre["niveau"] = niveau

        docs = (
            db.alertes.find(filtre)
            .sort("timestamp", -1)
            .limit(limite)
        )
        return jsonify([_serialiser(d) for d in docs])
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500


@bp.route("/api/alertes/resume")
def alertes_resume():
    """Résumé : nombre d'alertes critiques et warnings actives (dernière heure)."""
    try:
        db = get_db()
        une_heure = datetime.now(timezone.utc) - timedelta(hours=1)
        critiques = db.alertes.count_documents({"niveau": "critique", "timestamp": {"$gte": une_heure}})
        warnings  = db.alertes.count_documents({"niveau": "warning",  "timestamp": {"$gte": une_heure}})
        return jsonify({"critiques": critiques, "warnings": warnings})
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500


# ─── API : recommandations agronomiques ──────────────────────────────────────

@bp.route("/api/recommandations")
def recommandations():
    """
    Dernières recommandations globales par parcelle.
    """
    try:
        parcelle = request.args.get("parcelle")
        db = get_db()

        # Récupérer la dernière recommandation par parcelle
        pipeline = [
            {"$match": {"parcelle": parcelle} if parcelle else {}},
            {"$sort": {"timestamp": -1}},
            {"$group": {
                "_id": "$parcelle",
                "statut":      {"$first": "$statut"},
                "icone":       {"$first": "$icone"},
                "conseil":     {"$first": "$conseil"},
                "temperature": {"$first": "$temperature"},
                "humidite":    {"$first": "$humidite"},
                "ph_sol":      {"$first": "$ph_sol"},
                "timestamp":   {"$first": "$timestamp"},
            }},
            {"$project": {
                "_id": 0,
                "parcelle":    "$_id",
                "statut":      1,
                "icone":       1,
                "conseil":     1,
                "temperature": 1,
                "humidite":    1,
                "ph_sol":      1,
                "timestamp":   1,
            }},
            {"$sort": {"parcelle": 1}}
        ]

        docs = list(db.recommandations.aggregate(pipeline))
        return jsonify([_serialiser(d) for d in docs])
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500
