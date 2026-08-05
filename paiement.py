"""
Intégration CinetPay pour CivilPower.

Documentation officielle : https://docs.cinetpay.com

Étapes :
1. L'utilisateur clique "Payer" -> on appelle CinetPay pour générer un lien de paiement
2. On redirige l'utilisateur vers ce lien (il choisit Mobile Money ou carte sur la page CinetPay)
3. Une fois le paiement effectué, CinetPay appelle notre webhook -> on active le premium
4. CinetPay redirige aussi l'utilisateur vers une page de retour dans notre app
"""

import os
import uuid
import requests
from flask import Blueprint, redirect, request, jsonify, url_for, flash
from flask_login import login_required, current_user
from models import db, Abonnement

paiement_bp = Blueprint("paiement", __name__)

# --- Configuration : à remplir avec tes vraies clés CinetPay ---
CINETPAY_API_KEY = os.environ.get("CINETPAY_API_KEY", "TA_CLE_API_ICI")
CINETPAY_SITE_ID = os.environ.get("CINETPAY_SITE_ID", "TON_SITE_ID_ICI")
CINETPAY_API_URL = "https://api-checkout.cinetpay.com/v2/payment"

PRIX_ABONNEMENT = 5000  # en FCFA, à ajuster
DUREE_JOURS = 30


@paiement_bp.route("/paiement/initier", methods=["POST"])
@login_required
def initier_paiement():
    """Génère un lien de paiement CinetPay et redirige l'utilisateur vers lui."""

    transaction_id = str(uuid.uuid4())

    payload = {
        "apikey": CINETPAY_API_KEY,
        "site_id": CINETPAY_SITE_ID,
        "transaction_id": transaction_id,
        "amount": PRIX_ABONNEMENT,
        "currency": "XOF",  # FCFA
        "description": "Abonnement Premium CivilPower - 1 mois",
        "customer_name": current_user.nom,
        "customer_email": current_user.email,
        "customer_phone_number": current_user.telephone or "",
        # URL que CinetPay appelle automatiquement après paiement (côté serveur)
        "notify_url": url_for("paiement.webhook_cinetpay", _external=True),
        # URL vers laquelle l'utilisateur est redirigé après paiement (côté navigateur)
        "return_url": url_for("paiement.retour_paiement", _external=True),
        "channels": "ALL",  # autorise Mobile Money ET carte bancaire
    }

    try:
        response = requests.post(CINETPAY_API_URL, json=payload, timeout=15)
        data = response.json()
    except requests.RequestException:
        flash("Impossible de contacter le service de paiement. Réessaie plus tard.")
        return redirect(url_for("abonnement_page"))

    if data.get("code") == "201":
        # On garde la référence de transaction en attente sur l'abonnement
        abonnement = current_user.abonnement
        abonnement.reference_transaction = transaction_id
        db.session.commit()

        lien_paiement = data["data"]["payment_url"]
        return redirect(lien_paiement)
    else:
        flash("Erreur lors de la création du paiement : " + data.get("message", ""))
        return redirect(url_for("abonnement_page"))


@paiement_bp.route("/paiement/webhook", methods=["POST"])
def webhook_cinetpay():
    """
    CinetPay appelle cette route automatiquement après un paiement.
    C'est ICI que l'abonnement est réellement activé (jamais côté navigateur,
    pour éviter qu'un utilisateur triche en visitant juste /retour).
    """
    transaction_id = request.form.get("cpm_trans_id") or request.json.get("cpm_trans_id")

    if not transaction_id:
        return jsonify({"error": "transaction_id manquant"}), 400

    # Vérification officielle du statut auprès de CinetPay (obligatoire,
    # ne jamais faire confiance aux données brutes reçues)
    verif_payload = {
        "apikey": CINETPAY_API_KEY,
        "site_id": CINETPAY_SITE_ID,
        "transaction_id": transaction_id,
    }
    verif = requests.post(
        "https://api-checkout.cinetpay.com/v2/payment/check", json=verif_payload, timeout=15
    ).json()

    if verif.get("data", {}).get("status") == "ACCEPTED":
        abonnement = Abonnement.query.filter_by(reference_transaction=transaction_id).first()
        if abonnement:
            moyen = verif["data"].get("payment_method", "inconnu")
            abonnement.activer_premium(duree_jours=DUREE_JOURS, moyen=moyen, reference=transaction_id)
            db.session.commit()

    return jsonify({"status": "ok"}), 200


@paiement_bp.route("/paiement/retour")
@login_required
def retour_paiement():
    """Page affichée à l'utilisateur après son paiement (le webhook a déjà fait le travail)."""
    if current_user.est_premium():
        flash("Paiement confirmé ! Bienvenue en Premium.")
    else:
        flash("Paiement en cours de vérification, actualise dans quelques instants.")
    return redirect(url_for("accueil"))
