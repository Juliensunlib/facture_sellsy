# Intégration Sellsy - Airtable

Ce projet permet de synchroniser automatiquement les factures depuis Sellsy vers Airtable.

## Fonctionnalités

- Synchronisation manuelle des factures Sellsy vers Airtable
- Synchronisation des factures manquantes dans Airtable
- Synchronisation automatique via webhook lors de la création ou modification d'une facture
- Compatible avec la nouvelle API Sellsy v2

## Prérequis

- Python 3.10 (via Anaconda)
- Compte Sellsy avec accès API
- Compte Airtable avec une base configurée

## Installation

1. Clonez ce dépôt
2. Créez un environnement Anaconda:
   ```
   conda create -n sellsy_airtable python=3.10
   conda activate sellsy_airtable
   ```
3. Installez les dépendances:
   ```
   pip install requests python-dotenv pyairtable fastapi uvicorn
   ```
4. Configurez votre fichier `.env` avec vos clés API

## Configuration d'Airtable

Créez une table "Factures" avec les colonnes suivantes:
- ID_Facture (texte)
- Numéro (texte)
- Date (date)
- Client (texte)
- Montant_HT (nombre)
- Montant_TTC (nombre)
- Statut (texte)
- URL (URL)

## Utilisation

### Synchronisation manuelle

Pour synchroniser les factures des 30 derniers jours:
```
python main.py sync
```

Pour définir une autre période:
```
python main.py sync --days 60
```

### Synchronisation des factures manquantes

Pour ajouter toutes les factures qui ne sont pas encore dans Airtable:
```
python main.py sync-missing
```

Pour limiter le nombre de factures à vérifier:
```
python main.py sync-missing --limit 500
```

### Démarrer le serveur webhook

En local:
```
python main.py webhook --port 8000
```

## Configuration du webhook dans Sellsy

1. Allez dans Paramètres > API et Webhooks
2. Créez un nouveau webhook
3. URL: votre_url_render/webhook/sellsy (en production)
4. Événements: invoice.created, invoice.updated
5. Enregistrez et copiez la clé secrète dans votre fichier .env

## Déploiement sur Render

1. Créez un compte sur Render.com
2. Créez un nouveau Web Service
3. Connectez votre dépôt GitHub
4. Configurez:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python main.py webhook`
   - Variables d'environnement: ajoutez celles de votre fichier .env

## Contribution

N'hésitez pas à contribuer à ce projet en soumettant des pull requests.
