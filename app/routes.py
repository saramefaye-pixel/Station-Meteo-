"""
routes.py — version avec authentification complète.
"""

from flask import Blueprint, jsonify, render_template, request, session, redirect, url_for
from datetime import datetime, timezone, timedelta
from app.database import get_db
from app.auth import (
    verifier_identifiants, enregistrer_connexion, supprimer_connexion,
    get_sessions_actives, login_required, admin_required, UTILISATEURS
)

bp = Blueprint("main", __name__)

def _serialiser(doc):
    doc.pop("_id", None)
    if isinstance(doc.get("timestamp"), datetime):
        doc["timestamp"] = doc["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
    return doc

# ── Auth ──────────────────────────────────────────────────────────────────────

@bp.route("/login", methods=["GET", "POST"])
def login():
    if "username" in session:
        return redirect(url_for("main.index"))
    erreur = None
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        mdp = request.form.get("mot_de_passe", "")
        user = verifier_identifiants(username, mdp)
        if user:
            session["username"]    = username
            session["role"]        = user["role"]
            session["nom_complet"] = user["nom_complet"]
            session["avatar"]      = user["avatar"]
            enregistrer_connexion(username)
            return redirect(url_for("main.index"))
        erreur = "Identifiants incorrects. Vérifiez votre nom d'utilisateur et mot de passe."
    return render_template("login.html", erreur=erreur)

@bp.route("/logout")
def logout():
    username = session.get("username")
    if username:
        supprimer_connexion(username)
    session.clear()
    return redirect(url_for("main.login"))

@bp.route("/")
@login_required
def index():
    if session.get("role") == "admin":
        return redirect(url_for("main.admin"))
    return redirect(url_for("main.dashboard"))

@bp.route("/dashboard")
@login_required
def dashboard():
    if session.get("role") == "admin":
        return redirect(url_for("main.admin"))
    return render_template("index.html",
        username=session.get("username"),
        nom_complet=session.get("nom_complet"),
        avatar=session.get("avatar"),
    )

@bp.route("/admin")
@admin_required
def admin():
    return render_template("admin.html",
        nom_complet=session.get("nom_complet"),
        avatar=session.get("avatar"),
        nb_utilisateurs=len([u for u,d in UTILISATEURS.items() if d["role"]=="user"]),
    )

# ── API Admin ─────────────────────────────────────────────────────────────────

@bp.route("/api/admin/stats")
@admin_required
def admin_stats():
    try:
        db = get_db()
        une_heure = datetime.now(timezone.utc) - timedelta(hours=1)
        return jsonify({
            "nb_mesures_total":     db.mesures.count_documents({}),
            "nb_mesures_1h":        db.mesures.count_documents({"timestamp": {"$gte": une_heure}}),
            "nb_alertes_critiques": db.alertes.count_documents({"niveau": "critique", "timestamp": {"$gte": une_heure}}),
            "nb_alertes_warnings":  db.alertes.count_documents({"niveau": "warning",  "timestamp": {"$gte": une_heure}}),
            "nb_capteurs":          db.capteurs.count_documents({}),
            "nb_parcelles":         len(db.capteurs.distinct("parcelle")),
            "collections": {
                "mesures":         db.mesures.count_documents({}),
                "capteurs":        db.capteurs.count_documents({}),
                "alertes":         db.alertes.count_documents({}),
                "recommandations": db.recommandations.count_documents({}),
            },
            "heure_serveur": datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
        })
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500

@bp.route("/api/admin/sessions")
@admin_required
def admin_sessions():
    return jsonify(get_sessions_actives())

@bp.route("/api/admin/alertes_recentes")
@admin_required
def admin_alertes_recentes():
    try:
        db = get_db()
        docs = db.alertes.find({}).sort("timestamp", -1).limit(20)
        return jsonify([_serialiser(d) for d in docs])
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500

@bp.route("/api/admin/vider_mesures", methods=["POST"])
@admin_required
def admin_vider_mesures():
    try:
        db = get_db()
        sept_jours = datetime.now(timezone.utc) - timedelta(days=7)
        result = db.mesures.delete_many({"timestamp": {"$lt": sept_jours}})
        return jsonify({"supprimees": result.deleted_count})
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500

# ── API existantes protégées ──────────────────────────────────────────────────

@bp.route("/api/status")
@login_required
def status():
    try:
        db = get_db()
        return jsonify({"ok": True, "nb_mesures": db.mesures.count_documents({}), "nb_capteurs": db.capteurs.count_documents({})})
    except Exception as e:
        return jsonify({"ok": False, "erreur": str(e)}), 500

@bp.route("/api/parcelles")
@login_required
def parcelles():
    try:
        db = get_db()
        return jsonify(sorted(db.capteurs.distinct("parcelle")))
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500

@bp.route("/api/mesures")
@login_required
def mesures():
    try:
        parcelle = request.args.get("parcelle")
        type_cap = request.args.get("type")
        limite   = int(request.args.get("limite", 100))
        db = get_db()
        filtre = {}
        if parcelle: filtre["parcelle"] = parcelle
        if type_cap: filtre["type"] = type_cap
        docs = db.mesures.find(filtre).sort("timestamp", -1).limit(limite)
        return jsonify([_serialiser(d) for d in docs])
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500

@bp.route("/api/anomalies")
@login_required
def anomalies():
    try:
        parcelle = request.args.get("parcelle")
        db = get_db()
        filtre = {"type": "humidite", "valeur": {"$lt": 30}}
        if parcelle: filtre["parcelle"] = parcelle
        docs = db.mesures.find(filtre).sort("timestamp", -1).limit(200)
        return jsonify([_serialiser(d) for d in docs])
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500

@bp.route("/api/stats/temperature")
@login_required
def stats_temperature():
    try:
        db = get_db()
        hier = datetime.now(timezone.utc) - timedelta(hours=24)
        pipeline = [
            {"$match": {"type": "temperature", "timestamp": {"$gte": hier}}},
            {"$group": {"_id": "$parcelle", "moyenne": {"$avg": "$valeur"},
                        "min": {"$min": "$valeur"}, "max": {"$max": "$valeur"}, "nb_mesures": {"$sum": 1}}},
            {"$project": {"_id": 0, "parcelle": "$_id",
                          "moyenne": {"$round": ["$moyenne", 2]},
                          "min": {"$round": ["$min", 2]},
                          "max": {"$round": ["$max", 2]}, "nb_mesures": 1}},
            {"$sort": {"parcelle": 1}}
        ]
        return jsonify(list(db.mesures.aggregate(pipeline)))
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500

@bp.route("/api/evolution")
@login_required
def evolution():
    try:
        capteur_id = request.args.get("capteur_id")
        heures = int(request.args.get("heures", 24))
        if not capteur_id:
            return jsonify({"erreur": "capteur_id obligatoire"}), 400
        db = get_db()
        debut = datetime.now(timezone.utc) - timedelta(hours=heures)
        pipeline = [
            {"$match": {"capteur_id": capteur_id, "timestamp": {"$gte": debut}}},
            {"$group": {"_id": {"heure": {"$dateToString": {"format": "%Y-%m-%d %H:00", "date": "$timestamp"}}},
                        "moyenne": {"$avg": "$valeur"}, "min": {"$min": "$valeur"}, "max": {"$max": "$valeur"}}},
            {"$project": {"_id": 0, "heure": "$_id.heure",
                          "moyenne": {"$round": ["$moyenne", 2]},
                          "min": {"$round": ["$min", 2]},
                          "max": {"$round": ["$max", 2]}}},
            {"$sort": {"heure": 1}}
        ]
        return jsonify(list(db.mesures.aggregate(pipeline)))
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500

@bp.route("/api/capteurs")
@login_required
def capteurs():
    try:
        parcelle = request.args.get("parcelle")
        db = get_db()
        filtre = {}
        if parcelle: filtre["parcelle"] = parcelle
        return jsonify(list(db.capteurs.find(filtre, {"_id": 0})))
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500

@bp.route("/api/alertes")
@login_required
def alertes():
    try:
        parcelle = request.args.get("parcelle")
        niveau   = request.args.get("niveau")
        limite   = int(request.args.get("limite", 50))
        db = get_db()
        filtre = {}
        if parcelle: filtre["parcelle"] = parcelle
        if niveau:   filtre["niveau"] = niveau
        docs = db.alertes.find(filtre).sort("timestamp", -1).limit(limite)
        return jsonify([_serialiser(d) for d in docs])
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500

@bp.route("/api/alertes/resume")
@login_required
def alertes_resume():
    try:
        db = get_db()
        une_heure = datetime.now(timezone.utc) - timedelta(hours=1)
        return jsonify({
            "critiques": db.alertes.count_documents({"niveau": "critique", "timestamp": {"$gte": une_heure}}),
            "warnings":  db.alertes.count_documents({"niveau": "warning",  "timestamp": {"$gte": une_heure}}),
        })
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500

@bp.route("/api/recommandations")
@login_required
def recommandations():
    try:
        parcelle = request.args.get("parcelle")
        db = get_db()
        pipeline = [
            {"$match": {"parcelle": parcelle} if parcelle else {}},
            {"$sort": {"timestamp": -1}},
            {"$group": {"_id": "$parcelle", "statut": {"$first": "$statut"},
                        "icone": {"$first": "$icone"}, "conseil": {"$first": "$conseil"},
                        "temperature": {"$first": "$temperature"}, "humidite": {"$first": "$humidite"},
                        "ph_sol": {"$first": "$ph_sol"}, "timestamp": {"$first": "$timestamp"}}},
            {"$project": {"_id": 0, "parcelle": "$_id", "statut": 1, "icone": 1,
                          "conseil": 1, "temperature": 1, "humidite": 1, "ph_sol": 1, "timestamp": 1}},
            {"$sort": {"parcelle": 1}}
        ]
        docs = list(db.recommandations.aggregate(pipeline))
        return jsonify([_serialiser(d) for d in docs])
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500
