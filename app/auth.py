"""
auth.py
Gestion de l'authentification : login, logout, session, décorateur login_required.
Les utilisateurs sont définis ici (simulation sans base de données d'utilisateurs).
"""

from flask import session, redirect, url_for, request
from functools import wraps
from datetime import datetime, timezone

# ─── Utilisateurs simulés ─────────────────────────────────────────────────────
# Dans un vrai système, ces données seraient dans MongoDB avec mots de passe hashés.
UTILISATEURS = {
    "admin": {
        "mot_de_passe": "admin123",
        "role": "admin",
        "nom_complet": "Administrateur",
        "avatar": "👨‍💼",
    },
    "sokhna": {
        "mot_de_passe": "sokhna123",
        "role": "user",
        "nom_complet": "Sokhna Arame FAYE",
        "avatar": "👩‍🌾",
    },
    "rose": {
        "mot_de_passe": "rose123",
        "role": "user",
        "nom_complet": "Rose Sylva",
        "avatar": "👩‍🌾",
    },
}

# ─── Suivi des sessions actives (en mémoire) ──────────────────────────────────
# Dictionnaire : { username: { "depuis": datetime, "derniere_activite": datetime } }
SESSIONS_ACTIVES: dict = {}


def enregistrer_connexion(username: str):
    """Enregistre une nouvelle connexion active."""
    SESSIONS_ACTIVES[username] = {
        "depuis": datetime.now(timezone.utc),
        "derniere_activite": datetime.now(timezone.utc),
    }


def supprimer_connexion(username: str):
    """Supprime la session active d'un utilisateur."""
    SESSIONS_ACTIVES.pop(username, None)


def mettre_a_jour_activite(username: str):
    """Met à jour l'heure de dernière activité d'un utilisateur connecté."""
    if username in SESSIONS_ACTIVES:
        SESSIONS_ACTIVES[username]["derniere_activite"] = datetime.now(timezone.utc)


def get_sessions_actives() -> list:
    """Retourne la liste des sessions actives avec infos formatées."""
    resultat = []
    for username, info in SESSIONS_ACTIVES.items():
        user = UTILISATEURS.get(username, {})
        depuis = info["depuis"]
        duree_min = int((datetime.now(timezone.utc) - depuis).total_seconds() / 60)
        resultat.append({
            "username": username,
            "nom_complet": user.get("nom_complet", username),
            "role": user.get("role", "user"),
            "avatar": user.get("avatar", "👤"),
            "depuis": depuis.strftime("%H:%M:%S"),
            "duree_min": duree_min,
        })
    return resultat


# ─── Vérification des identifiants ───────────────────────────────────────────
def verifier_identifiants(username: str, mot_de_passe: str) -> dict | None:
    """
    Vérifie les identifiants.
    Retourne le profil utilisateur si correct, None sinon.
    """
    user = UTILISATEURS.get(username.strip().lower())
    if user and user["mot_de_passe"] == mot_de_passe:
        return user
    return None


# ─── Décorateurs de protection des routes ────────────────────────────────────
def login_required(f):
    """Redirige vers /login si l'utilisateur n'est pas connecté."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("main.login"))
        mettre_a_jour_activite(session["username"])
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Redirige vers /login si l'utilisateur n'est pas admin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("main.login"))
        if session.get("role") != "admin":
            return redirect(url_for("main.dashboard"))
        mettre_a_jour_activite(session["username"])
        return f(*args, **kwargs)
    return decorated
