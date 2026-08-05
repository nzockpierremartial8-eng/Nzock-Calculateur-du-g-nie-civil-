"""
CivilPower - squelette d'authentification + gestion d'abonnement.

À FUSIONNER avec ton app.py existant (modules de calcul).
Ce fichier montre juste la partie comptes/abonnements ; tes routes
de calcul (structures, béton armé, hydraulique...) viennent se
brancher à côté, en utilisant @login_required et current_user.est_premium()
pour verrouiller les modules payants.
"""

from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)
from functools import wraps
import os
from models import db, User, Abonnement
from paiement import paiement_bp

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-moi-en-production")

# En local : SQLite (aucune config nécessaire).
# Sur Render : définis la variable d'environnement DATABASE_URL fournie
# automatiquement par leur base PostgreSQL gratuite -> aucun changement de code requis.
db_url = os.environ.get("DATABASE_URL", "sqlite:///civilpower.db")
if db_url.startswith("postgres://"):  # Render fournit parfois l'ancien préfixe
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


app.register_blueprint(paiement_bp)


# ---------- Décorateur pour verrouiller les modules premium ----------
def premium_required(f):
    @wraps(f)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.est_premium():
            flash("Ce module nécessite un abonnement premium.")
            return redirect(url_for("abonnement_page"))
        return f(*args, **kwargs)
    return wrapper


# ---------- Inscription ----------
@app.route("/inscription", methods=["GET", "POST"])
def inscription():
    if request.method == "POST":
        nom = request.form["nom"]
        email = request.form["email"]
        telephone = request.form.get("telephone")
        password = request.form["password"]

        if User.query.filter_by(email=email).first():
            flash("Cet email est déjà utilisé.")
            return redirect(url_for("inscription"))

        user = User(nom=nom, email=email, telephone=telephone)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()  # récupère user.id avant commit

        # Création automatique d'un abonnement gratuit
        abonnement = Abonnement(user_id=user.id, statut="gratuit")
        db.session.add(abonnement)
        db.session.commit()

        login_user(user)
        return redirect(url_for("accueil"))

    return render_template("inscription.html")


# ---------- Connexion ----------
@app.route("/connexion", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("accueil"))

        flash("Email ou mot de passe incorrect.")

    return render_template("connexion.html")


@app.route("/deconnexion")
@login_required
def deconnexion():
    logout_user()
    return redirect(url_for("login"))


# ---------- Page d'accueil ----------
@app.route("/")
@login_required
def accueil():
    return render_template("accueil.html", user=current_user)


# ---------- Page d'abonnement (avant paiement) ----------
@app.route("/abonnement")
@login_required
def abonnement_page():
    return render_template("abonnement.html", user=current_user)


# ---------- Exemple de module payant ----------
@app.route("/module/beton-arme")
@premium_required
def module_beton_arme():
    return "Ici viendra ton module de dimensionnement béton armé BAEL/Eurocode."


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
