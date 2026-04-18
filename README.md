# 🌾 Station Météo Agricole — AgroTic L1
## TP Internet des Objets — MongoDB + Python + Flask

---

## 📁 Structure du projet

```
station_meteo/
├── main.py                  ← Point d'entrée unique
├── requirements.txt         ← Dépendances Python
├── README.md                ← Ce fichier
├── app/
│   ├── __init__.py          ← Fabrique Flask
│   ├── database.py          ← Connexion + initialisation MongoDB
│   ├── simulator.py         ← Simulateur de capteurs IoT (thread)
│   └── routes.py            ← Routes Flask + requêtes MongoDB
├── templates/
│   └── index.html           ← Interface web (HTML)
└── static/
    ├── style.css            ← Styles CSS
    └── app.js               ← JavaScript (Chart.js + fetch API)
```

---

## ⚙️ Prérequis

- Python 3.8 ou supérieur
- MongoDB 6.0 ou supérieur installé localement
- pip (gestionnaire de paquets Python)

---

## 🔧 Installation étape par étape

### Étape 1 — Installer MongoDB

**Linux / WSL (Ubuntu) :**
```bash
# Importer la clé GPG de MongoDB
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor

# Ajouter le dépôt
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] \
https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | \
sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list

# Installer
sudo apt-get update
sudo apt-get install -y mongodb-org

# Démarrer MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod   # Démarrage automatique
```

**macOS (avec Homebrew) :**
```bash
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community
```

**Windows :**
Téléchargez l'installateur sur : https://www.mongodb.com/try/download/community
Cochez "Install MongoDB as a Service" pendant l'installation.

### Étape 2 — Vérifier que MongoDB est démarré

```bash
mongosh --eval "db.adminCommand('ping')"
# Doit afficher : { ok: 1 }
```

### Étape 3 — Installer les dépendances Python

```bash
# Se placer dans le dossier du projet
cd station_meteo

# (Recommandé) Créer un environnement virtuel
python3 -m venv venv
source venv/bin/activate        # Linux/macOS
# ou : venv\Scripts\activate    # Windows

# Installer les dépendances
pip install -r requirements.txt
```

### Étape 4 — Lancer le projet

```bash
python main.py
```

Vous devriez voir :
```
=======================================================
  🌾  Station Météo Agricole — AgroTic L1
=======================================================

🔌  Connexion à MongoDB...
✅  9 capteurs insérés dans la collection 'capteurs'.

📡  Démarrage du simulateur de capteurs IoT...
🚀  Simulateur démarré (intervalle : 60s).
[HH:MM:SS] ✅ 9 mesures insérées.

🌐  Serveur Flask démarré.
    👉  Ouvrez votre navigateur sur : http://localhost:5000
```

### Étape 5 — Ouvrir l'interface

Ouvrez votre navigateur et allez sur :
```
http://localhost:5000
```

---

## 🗄️ Base de données MongoDB

### Collection `capteurs`
```json
{
  "capteur_id": "C001",
  "parcelle": "Parcelle A",
  "type": "temperature"
}
```

### Collection `mesures`
```json
{
  "capteur_id": "C001",
  "parcelle": "Parcelle A",
  "type": "temperature",
  "valeur": 28.4,
  "unite": "°C",
  "timestamp": ISODate("2025-01-15T14:32:00Z")
}
```

---

## 🔌 API REST disponibles

| Méthode | URL | Description |
|---------|-----|-------------|
| GET | `/api/status` | État connexion MongoDB |
| GET | `/api/parcelles` | Liste des parcelles |
| GET | `/api/capteurs` | Liste des capteurs |
| GET | `/api/mesures?parcelle=X&type=Y&limite=100` | Mesures filtrables |
| GET | `/api/anomalies?parcelle=X` | Humidité < 30% |
| GET | `/api/stats/temperature` | Agrégation 24h par parcelle |
| GET | `/api/evolution?capteur_id=C001&heures=24` | Évolution horaire |

---

## 🐛 Problèmes courants

**MongoDB ne démarre pas :**
```bash
sudo systemctl status mongod    # Voir le statut
sudo systemctl start mongod     # Démarrer
journalctl -u mongod            # Voir les logs
```

**Erreur "port already in use" (port 5000) :**
```bash
lsof -i :5000
kill -9 <PID>
```

**Erreur d'importation Python :**
```bash
# Vérifier que l'environnement virtuel est activé
which python    # Doit pointer vers venv/bin/python
pip list        # Doit montrer flask et pymongo
```

---

## 👩‍💻 Auteur
Projet réalisé dans le cadre du TP IoT — Licence 1 AgroTic
UFR SFI — Université Sine Saloum El Hadj Ibrahima Niass
Année académique 2024–2025
