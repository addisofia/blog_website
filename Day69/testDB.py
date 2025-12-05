from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

# Crée une instance Flask
app = Flask(__name__)

# Récupère la DB_URI depuis les variables d'environnement
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DB_URI")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Crée l'objet SQLAlchemy
db = SQLAlchemy(app)

# Fonction pour tester la connexion
def test_connection():
    try:
        with app.app_context():
            # Exécute une requête simple
            result = db.engine.execute("SELECT 1")
            print("Connexion PostgreSQL OK ✅")
            for row in result:
                print("Résultat test :", row[0])
    except Exception as e:
        print("Erreur de connexion PostgreSQL ❌")
        print(e)

# Lance le test
if __name__ == "__main__":
    test_connection()