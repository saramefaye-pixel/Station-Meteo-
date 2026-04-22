"""
alertes.py
Moteur d'alertes intelligentes et de recommandations agronomiques.
Analysé et appelé par le simulateur à chaque cycle de mesures.
"""

from datetime import datetime, timezone
from app.database import get_db


# ─── Seuils agronomiques ──────────────────────────────────────────────────────
SEUILS = {
    "temperature": {
        "critique_haut": 40.0,
        "warning_haut":  35.0,
        "warning_bas":   10.0,
        "critique_bas":   5.0,
    },
    "humidite": {
        "critique_bas":  20.0,
        "warning_bas":   30.0,
        "optimal_min":   40.0,
        "optimal_max":   70.0,
        "warning_haut":  85.0,
        "critique_haut": 95.0,
    },
    "ph_sol": {
        "critique_bas":  5.0,
        "warning_bas":   5.5,
        "optimal_min":   6.0,
        "optimal_max":   7.5,
        "warning_haut":  8.0,
        "critique_haut": 8.5,
    },
}

# ─── Messages agronomiques par situation ─────────────────────────────────────
def _message_temperature(valeur: float, parcelle: str) -> dict | None:
    s = SEUILS["temperature"]
    if valeur >= s["critique_haut"]:
        return {
            "niveau": "critique",
            "icone": "🔴",
            "titre": f"Stress thermique critique — {parcelle}",
            "message": f"Température de {valeur}°C détectée. Risque de brûlure des cultures.",
            "recommandation": "Activer l'irrigation de refroidissement immédiatement. Protéger les jeunes plants.",
        }
    if valeur >= s["warning_haut"]:
        return {
            "niveau": "warning",
            "icone": "🟡",
            "titre": f"Température élevée — {parcelle}",
            "message": f"Température de {valeur}°C. Surveillance accrue recommandée.",
            "recommandation": "Prévoir une irrigation en début de matinée (6h-8h). Vérifier l'ombrage.",
        }
    if valeur <= s["critique_bas"]:
        return {
            "niveau": "critique",
            "icone": "🔴",
            "titre": f"Gel imminent — {parcelle}",
            "message": f"Température de {valeur}°C. Risque de gel des cultures.",
            "recommandation": "Couvrir les cultures sensibles. Activer le chauffage si disponible.",
        }
    if valeur <= s["warning_bas"]:
        return {
            "niveau": "warning",
            "icone": "🟡",
            "titre": f"Température basse — {parcelle}",
            "message": f"Température de {valeur}°C. Risque pour les cultures tropicales.",
            "recommandation": "Surveiller les prévisions météo. Prévoir une protection nocturne.",
        }
    return None


def _message_humidite(valeur: float, parcelle: str) -> dict | None:
    s = SEUILS["humidite"]
    if valeur <= s["critique_bas"]:
        return {
            "niveau": "critique",
            "icone": "🔴",
            "titre": f"Sécheresse critique — {parcelle}",
            "message": f"Humidité de {valeur}%. Sol extrêmement sec. Irrigation URGENTE.",
            "recommandation": "Irriguer immédiatement pendant 45-60 min. Vérifier le système d'irrigation.",
        }
    if valeur <= s["warning_bas"]:
        return {
            "niveau": "warning",
            "icone": "🟡",
            "titre": f"Irrigation nécessaire — {parcelle}",
            "message": f"Humidité de {valeur}%. Le sol commence à se dessécher.",
            "recommandation": "Programmer une irrigation de 20-30 min dans les 2 prochaines heures.",
        }
    if valeur >= s["critique_haut"]:
        return {
            "niveau": "critique",
            "icone": "🔴",
            "titre": f"Excès d'eau — {parcelle}",
            "message": f"Humidité de {valeur}%. Risque d'asphyxie racinaire et de maladies fongiques.",
            "recommandation": "Arrêter toute irrigation. Vérifier le drainage. Traitement fongicide préventif.",
        }
    if valeur >= s["warning_haut"]:
        return {
            "niveau": "warning",
            "icone": "🟡",
            "titre": f"Humidité excessive — {parcelle}",
            "message": f"Humidité de {valeur}%. Conditions favorables aux champignons.",
            "recommandation": "Réduire l'irrigation. Améliorer la ventilation. Surveiller les feuilles.",
        }
    return None


def _message_ph(valeur: float, parcelle: str) -> dict | None:
    s = SEUILS["ph_sol"]
    if valeur <= s["critique_bas"]:
        return {
            "niveau": "critique",
            "icone": "🔴",
            "titre": f"Sol très acide — {parcelle}",
            "message": f"pH de {valeur}. Sol trop acide, nutriments bloqués.",
            "recommandation": "Apporter de la chaux agricole (2-3 t/ha). Réévaluer dans 2 semaines.",
        }
    if valeur <= s["warning_bas"]:
        return {
            "niveau": "warning",
            "icone": "🟡",
            "titre": f"Sol acide — {parcelle}",
            "message": f"pH de {valeur}. Légère acidité, absorption des nutriments réduite.",
            "recommandation": "Apporter de la chaux dolomitique (1 t/ha). Éviter les engrais acidifiants.",
        }
    if valeur >= s["critique_haut"]:
        return {
            "niveau": "critique",
            "icone": "🔴",
            "titre": f"Sol très alcalin — {parcelle}",
            "message": f"pH de {valeur}. Sol trop basique, carence en fer et manganèse.",
            "recommandation": "Apporter du soufre agricole ou de la tourbe. Utiliser des engrais acidifiants.",
        }
    if valeur >= s["warning_haut"]:
        return {
            "niveau": "warning",
            "icone": "🟡",
            "titre": f"Sol alcalin — {parcelle}",
            "message": f"pH de {valeur}. Légère alcalinité, surveiller les carences.",
            "recommandation": "Utiliser des engrais légèrement acidifiants (sulfate d'ammonium).",
        }
    return None


# ─── Recommandation globale par parcelle ─────────────────────────────────────
def _recommandation_globale(temp: float, hum: float, ph: float, parcelle: str) -> dict:
    """Génère un conseil global basé sur la combinaison des 3 capteurs."""
    s_hum  = SEUILS["humidite"]
    s_temp = SEUILS["temperature"]
    s_ph   = SEUILS["ph_sol"]

    # Conditions optimales
    if (s_temp["warning_bas"] < temp < s_temp["warning_haut"] and
        s_hum["optimal_min"]  < hum  < s_hum["optimal_max"] and
        s_ph["optimal_min"]   < ph   < s_ph["optimal_max"]):
        return {
            "statut": "optimal",
            "icone": "✅",
            "conseil": "Conditions optimales pour la croissance. Maintenir le rythme d'irrigation actuel.",
        }

    # Besoin d'arrosage + chaleur
    if hum < s_hum["warning_bas"] and temp > s_temp["warning_haut"]:
        return {
            "statut": "urgent",
            "icone": "🚨",
            "conseil": "URGENT : Sol sec + forte chaleur. Irriguer immédiatement pour éviter le flétrissement.",
        }

    # Bon dans l'ensemble
    return {
        "statut": "acceptable",
        "icone": "⚠️",
        "conseil": "Conditions acceptables mais quelques paramètres nécessitent attention. Voir les alertes.",
    }


# ─── Fonction principale : analyser et sauvegarder les alertes ───────────────
def analyser_et_sauvegarder(mesures_par_capteur: list):
    """
    Reçoit la liste des mesures du cycle courant,
    génère les alertes et recommandations, les sauvegarde dans MongoDB.
    """
    try:
        db = get_db()
        now = datetime.now(timezone.utc)

        # Organiser par parcelle
        par_parcelle: dict = {}
        for m in mesures_par_capteur:
            p = m["parcelle"]
            if p not in par_parcelle:
                par_parcelle[p] = {}
            par_parcelle[p][m["type"]] = m["valeur"]

        alertes_a_inserer       = []
        recommandations_a_inserer = []

        for parcelle, capteurs in par_parcelle.items():
            temp = capteurs.get("temperature")
            hum  = capteurs.get("humidite")
            ph   = capteurs.get("ph_sol")

            # ── Générer les alertes ──────────────────────────────────────────
            for fn, val in [
                (_message_temperature, temp),
                (_message_humidite,    hum),
                (_message_ph,          ph),
            ]:
                if val is not None:
                    alerte = fn(val, parcelle)
                    if alerte:
                        alerte["parcelle"]  = parcelle
                        alerte["timestamp"] = now
                        alerte["valeur"]    = val
                        alertes_a_inserer.append(alerte)

            # ── Générer la recommandation globale ────────────────────────────
            if temp is not None and hum is not None and ph is not None:
                reco = _recommandation_globale(temp, hum, ph, parcelle)
                reco["parcelle"]    = parcelle
                reco["timestamp"]   = now
                reco["temperature"] = temp
                reco["humidite"]    = hum
                reco["ph_sol"]      = ph
                recommandations_a_inserer.append(reco)

        # ── Sauvegarder dans MongoDB ─────────────────────────────────────────
        if alertes_a_inserer:
            db.alertes.insert_many(alertes_a_inserer)

        if recommandations_a_inserer:
            db.recommandations.insert_many(recommandations_a_inserer)

        nb_alertes = len(alertes_a_inserer)
        if nb_alertes:
            print(f"    ⚠️  {nb_alertes} alerte(s) générée(s).")

    except Exception as e:
        print(f"[Alertes] Erreur : {e}")
