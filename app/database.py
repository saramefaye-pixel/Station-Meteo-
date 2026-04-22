"""
database.py
Gestion de la connexion MongoDB et initialisation des collections.
"""

from pymongo import MongoClient, ASCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import sys


# ─── Configuration ────────────────────────────────────────────────────────────
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME   = "station_meteo_agricole"

# ─── Données initiales des capteurs ───────────────────────────────────────────
CAPTEURS_INITIAUX = [
    {"capteur_id": "C001", "parcelle": "Parcelle A", "type": "temperature"},
    {"capteur_id": "C002", "parcelle": "Parcelle A", "type": "humidite"},
    {"capteur_id": "C003", "parcelle": "Parcelle A", "type": "ph_sol"},
    {"capteur_id": "C004", "parcelle": "Parcelle B", "type": "temperature"},
    {"capteur_id": "C005", "parcelle": "Parcelle B", "type": "humidite"},
    {"capteur_id": "C006", "parcelle": "Parcelle B", "type": "ph_sol"},
    {"capteur_id": "C007", "parcelle": "Parcelle C", "type": "temperature"},
    {"capteur_id": "C008", "parcelle": "Parcelle C", "type": "humidite"},
    {"capteur_id": "C009", "parcelle": "Parcelle C", "type": "ph_sol"},
]


def get_db():
    """
    Retourne la base de données MongoDB.
    Lève une exception avec un message clair si la connexion échoue.
    """
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
        # Force une vraie vérification de connexion
        client.admin.command("ping")
        return client[DB_NAME]
    except (ConnectionFailure, ServerSelectionTimeoutError):
        print("\n" + "="*60)
        print("❌  ERREUR : Impossible de se connecter à MongoDB.")
        print("    Vérifiez que MongoDB est démarré sur votre machine.")
        print("    Commande : sudo systemctl start mongod   (Linux/WSL)")
        print("               brew services start mongodb-community  (Mac)")
        print("               Démarrez MongoDB depuis Services   (Windows)")
        print("="*60 + "\n")
        sys.exit(1)


def init_db():
    """
    Initialise la base de données :
      - Crée (si absent) un index TTL sur les mesures (optionnel)
      - Crée un index sur capteur_id + timestamp pour les requêtes rapides
      - Insère les capteurs de référence si la collection est vide
    Retourne l'objet db.
    """
    db = get_db()

    # ── Index sur la collection mesures ──────────────────────────────────────
    db.mesures.create_index(
        [("capteur_id", ASCENDING), ("timestamp", ASCENDING)],
        name="idx_capteur_timestamp"
    )
    db.mesures.create_index(
        [("timestamp", ASCENDING)],
        name="idx_timestamp"
    )

    # ── Insertion des capteurs si la collection est vide ──────────────────────
    if db.capteurs.count_documents({}) == 0:
        db.capteurs.insert_many(CAPTEURS_INITIAUX)
        print(f"✅  {len(CAPTEURS_INITIAUX)} capteurs insérés dans la collection 'capteurs'.")
    else:
        print(f"✅  Collection 'capteurs' déjà initialisée ({db.capteurs.count_documents({})} capteurs).")

    return db
