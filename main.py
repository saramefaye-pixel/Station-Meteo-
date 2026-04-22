"""
main.py
Point d'entrée de la station météo agricole.
Lancement : python main.py
Accès     : http://localhost:5000
"""

from app import create_app
from app.database import init_db
from app.simulator import demarrer_simulateur

if __name__ == "__main__":
    print("\n" + "="*55)
    print("  🌾  Station Météo Agricole — AgroTic L2")
    print("="*55)

    # 1. Connexion + initialisation MongoDB
    print("\n🔌  Connexion à MongoDB...")
    init_db()

    # 2. Démarrage du simulateur IoT (thread daemon)
    print("\n📡  Démarrage du simulateur de capteurs IoT...")
    demarrer_simulateur(intervalle_secondes=60)

    # 3. Démarrage du serveur Flask
    print("\n🌐  Serveur Flask démarré.")
    print("    👉  Ouvrez votre navigateur sur : http://localhost:5000")
    print("\n    (Appuyez sur CTRL+C pour arrêter)\n")
    print("="*55 + "\n")

    app = create_app()
    app.run(debug=False, host="0.0.0.0", port=5000, use_reloader=False)
