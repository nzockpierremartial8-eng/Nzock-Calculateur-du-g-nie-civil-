# CivilPower - Module Comptes & Abonnements

Ce dossier contient la base d'authentification et de gestion d'abonnement
à fusionner avec ton app CivilPower existante (les 18 modules de calcul).

## Contenu

- `models.py` : tables `users` (comptes) et `abonnements` (statut gratuit/premium)
- `app.py` : routes inscription / connexion / déconnexion / page abonnement
- `templates/` : pages HTML minimales (à styliser avec ton thème bleu technique)
- `requirements.txt` : dépendances à installer

## Installation (dans Pydroid ou en ligne)

```bash
pip install -r requirements.txt
python app.py
```

Au premier lancement, la base `civilpower.db` (SQLite) est créée automatiquement.

## Comment fusionner avec ton app existante

1. Copie `models.py` dans ton projet.
2. Dans ton `app.py` principal, ajoute les imports et l'initialisation
   de `db` et `login_manager` (voir le haut de ce fichier `app.py`).
3. Pour chaque route de module PAYANT (ex: béton armé), remplace
   `@app.route(...)` par `@app.route(...)` + `@premium_required`
   (le décorateur défini ici).
4. Pour les modules GRATUITS, ne touche à rien.

## Intégration CinetPay (déjà codée dans `paiement.py`)

Le fichier `paiement.py` contient tout le circuit de paiement :

- `/paiement/initier` : génère un lien de paiement CinetPay (Mobile Money OU carte,
  l'utilisateur choisit sur la page CinetPay) et redirige l'utilisateur
- `/paiement/webhook` : CinetPay appelle cette route automatiquement après paiement.
  C'est LA SEULE route qui active réellement le premium (jamais côté navigateur,
  pour éviter la triche) — elle revérifie le statut auprès de CinetPay avant d'activer
- `/paiement/retour` : page affichée à l'utilisateur après son paiement

### Pour activer ça avec de vraies clés

1. Crée un compte marchand sur https://cinetpay.com
2. Récupère `API_KEY` et `SITE_ID` dans ton tableau de bord CinetPay
3. Définis-les comme variables d'environnement (ne jamais les écrire en dur dans le code) :
   ```bash
   export CINETPAY_API_KEY="ta_vraie_cle"
   export CINETPAY_SITE_ID="ton_vrai_site_id"
   ```
4. **Important** : CinetPay doit pouvoir appeler ton `/paiement/webhook` depuis Internet.
   Ça ne marche PAS tant que l'app tourne uniquement en local sur ton téléphone (127.0.0.1) —
   c'est une bonne raison de prioriser le déploiement Render juste après.
5. Le prix de l'abonnement (`PRIX_ABONNEMENT`) et sa durée (`DUREE_JOURS`) sont
   modifiables en haut de `paiement.py`.

## Déploiement sur Render (étape par étape)

### 1. Préparer GitHub
```bash
git init
git add .
git commit -m "CivilPower - auth + abonnement + CinetPay"
git remote add origin https://github.com/TON_COMPTE/Nzock-Calculateur-du-génie-civil-.git
git push -u origin main
```
(Fusionne d'abord ce contenu avec tes 18 modules existants dans le même dossier.)

### 2. Créer les services sur Render
1. Va sur https://render.com et connecte-toi avec GitHub
2. **New +** → **PostgreSQL** → nom "civilpower-db" → note l'URL de connexion générée (Internal Database URL)
3. **New +** → **Web Service** → sélectionne ton repo GitHub
   - Build command : `pip install -r requirements.txt`
   - Start command : laisse vide (le `Procfile` s'en charge)
4. Dans l'onglet **Environment** du Web Service, ajoute :
   - `DATABASE_URL` = l'URL PostgreSQL notée à l'étape 2
   - `SECRET_KEY` = une chaîne aléatoire longue (ex: générée avec `python -c "import secrets; print(secrets.token_hex(32))"`)
   - `CINETPAY_API_KEY` = ta clé CinetPay
   - `CINETPAY_SITE_ID` = ton site ID CinetPay

### 3. Premier lancement
Render déploie automatiquement à chaque `git push`. Ta première URL publique
ressemblera à `https://civilpower.onrender.com` — c'est CETTE url qu'il faut
donner à CinetPay comme domaine autorisé dans leur tableau de bord.

### Limite du plan gratuit Render
L'app "s'endort" après 15 min d'inactivité et met ~30s à redémarrer au
premier visiteur suivant. Suffisant pour tester avec de vrais utilisateurs ;
un plan payant (~7$/mois) supprime cette limite quand tu auras des abonnés réguliers.
