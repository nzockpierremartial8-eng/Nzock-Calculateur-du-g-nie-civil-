"""
Modèles de base de données pour CivilPower.
Utilise SQLAlchemy (fonctionne avec SQLite pour démarrer,
et pourra migrer vers PostgreSQL sur Render sans changer le code).
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    telephone = db.Column(db.String(30), unique=True, nullable=True)  # pour Mobile Money
    password_hash = db.Column(db.String(255), nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    # Relation 1-1 avec l'abonnement
    abonnement = db.relationship(
        "Abonnement", backref="user", uselist=False, cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def est_premium(self):
        """Vrai si l'utilisateur a un abonnement actif et non expiré."""
        if not self.abonnement:
            return False
        return (
            self.abonnement.statut == "premium"
            and self.abonnement.date_expiration
            and self.abonnement.date_expiration > datetime.utcnow()
        )

    def __repr__(self):
        return f"<User {self.email}>"


class Abonnement(db.Model):
    __tablename__ = "abonnements"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)

    statut = db.Column(db.String(20), default="gratuit")  # gratuit | premium | expire
    moyen_paiement = db.Column(db.String(30), nullable=True)  # mobile_money | carte
    reference_transaction = db.Column(db.String(120), nullable=True)  # ID CinetPay
    date_debut = db.Column(db.DateTime, nullable=True)
    date_expiration = db.Column(db.DateTime, nullable=True)

    def activer_premium(self, duree_jours=30, moyen="mobile_money", reference=None):
        """Active ou prolonge l'abonnement premium après paiement confirmé."""
        maintenant = datetime.utcnow()
        # Si déjà premium et pas encore expiré, on prolonge à partir de la date d'expiration
        base = self.date_expiration if (self.date_expiration and self.date_expiration > maintenant) else maintenant

        self.statut = "premium"
        self.moyen_paiement = moyen
        self.reference_transaction = reference
        self.date_debut = self.date_debut or maintenant
        self.date_expiration = base + timedelta(days=duree_jours)

    def __repr__(self):
        return f"<Abonnement user={self.user_id} statut={self.statut}>"
