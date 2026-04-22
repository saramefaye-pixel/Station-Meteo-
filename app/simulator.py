"""
simulator.py
Simule des mesures IoT réalistes toutes les 60 secondes.
Tourne dans un thread daemon en arrière-plan.
"""

import threading
import time
import random
from datetime import datetime, timezone
from app.database import get_db
from app.alertes import analyser_et_sauvegarder


# ─── Plages réalistes par type de capteur ────────────────────────────────────
PLAGES = {
    "temperature": {"min": 18.0,  "max": 42.0,  "unite": "°C",  "fluctuation": 1.5},
    "humidite":    {"min": 20.0,  "max": 95.0,  "unite": "%",   "fluctuation": 3.0},
    "ph_sol":      {"min": 5.5,   "max": 8.5,   "unite": "pH",  "fluctuation": 0.2},
}

# État interne pour simuler une évolution progressive (pas de sauts brusques)
_etat_capteurs: dict = {}


def _valeur_initiale(type_capteur: str) -> float:
    """Génère une valeur de départ réaliste pour un capteur."""
    p = PLAGES[type_capteur]
    centre = (p["min"] + p["max"]) / 2
    return round(random.uniform(centre - 5, centre + 5), 2)


def _prochaine_valeur(capteur_id: str, type_capteur: str) -> float:
    """
    Fait évoluer la valeur précédente de manière réaliste
    (marche aléatoire bornée).
    """
    p = PLAGES[type_capteur]

    if capteur_id not in _etat_capteurs:
        _etat_capteurs[capteur_id] = _valeur_initiale(type_capteur)

    valeur_actuelle = _etat_capteurs[capteur_id]
    delta = random.uniform(-p["fluctuation"], p["fluctuation"])
    nouvelle_valeur = valeur_actuelle + delta

    # Borne la valeur dans la plage autorisée
    nouvelle_valeur = max(p["min"], min(p["max"], nouvelle_valeur))
    nouvelle_valeur = round(nouvelle_valeur, 2)

    _etat_capteurs[capteur_id] = nouvelle_valeur
    return nouvelle_valeur


def _inserer_mesures():
    """Récupère tous les capteurs et insère une mesure pour chacun."""
    try:
        db = get_db()
        capteurs = list(db.capteurs.find({}, {"_id": 0}))

        mesures = []
        for capteur in capteurs:
            valeur = _prochaine_valeur(capteur["capteur_id"], capteur["type"])
            mesures.append({
                "capteur_id": capteur["capteur_id"],
                "parcelle":   capteur["parcelle"],
                "type":       capteur["type"],
                "valeur":     valeur,
                "unite":      PLAGES[capteur["type"]]["unite"],
                "timestamp":  datetime.now(timezone.utc),
            })

        if mesures:
            db.mesures.insert_many(mesures)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ {len(mesures)} mesures insérées.")
            analyser_et_sauvegarder(mesures)

    except Exception as e:
        print(f"[Simulateur] ⚠️  Erreur lors de l'insertion : {e}")


def _boucle_simulation(intervalle_secondes: int):
    """Boucle infinie : insère des mesures toutes les `intervalle_secondes`."""
    print(f"🚀  Simulateur démarré (intervalle : {intervalle_secondes}s).")
    # Première insertion immédiate au démarrage
    _inserer_mesures()
    while True:
        time.sleep(intervalle_secondes)
        _inserer_mesures()


def demarrer_simulateur(intervalle_secondes: int = 60):
    """
    Lance le simulateur dans un thread daemon.
    Le thread s'arrête automatiquement à la fermeture du programme.
    """
    thread = threading.Thread(
        target=_boucle_simulation,
        args=(intervalle_secondes,),
        daemon=True,
        name="SimulateurIoT"
    )
    thread.start()
    return thread
