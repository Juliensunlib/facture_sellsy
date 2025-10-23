# Diagnostic des factures sans ID Sellsy

## Problème
Deux dernières factures sont apparues dans Airtable sans numéro d'ID Sellsy.

## Causes possibles

1. **L'API Sellsy ne renvoie pas l'ID dans certains cas**
   - Facture en brouillon non finalisée
   - Webhook déclenché trop tôt (avant finalisation)
   - Format de réponse API différent selon le contexte

2. **Le champ `id` est dans une structure différente**
   - Peut être dans `data.id` au lieu de `id` directement
   - Peut avoir un nom différent (`invoice_id`, `document_id`, etc.)

3. **Race condition avec le webhook**
   - Le webhook arrive avant que Sellsy n'ait assigné un ID définitif

## Corrections apportées

### 1. Validation stricte de l'ID (airtable_api.py)
```python
# Refuse maintenant d'insérer une facture sans ID
if not invoice_id:
    logger.error("ID de facture manquant")
    return None
```

### 2. Récupération de l'ID depuis la requête (sellsy_api.py)
```python
# Si l'API ne renvoie pas l'ID dans les détails, on l'ajoute
if "id" not in invoice_data:
    invoice_data["id"] = invoice_id
```

### 3. Logs de debug détaillés
- Fichier log : `airtable_sync_debug.log`
- Affiche la structure exacte des données reçues
- Permet d'identifier les factures problématiques

## Comment diagnostiquer

### Étape 1 : Vérifier les logs actuels
```bash
# Consulter le fichier de log de debug
cat airtable_sync_debug.log | grep "ID reçu"
```

### Étape 2 : Exécuter le script de debug
```bash
python debug_sellsy_data.py
```
Cela affichera la structure exacte des 10 dernières factures.

### Étape 3 : Identifier les factures sans ID dans Airtable
```bash
python cleanup_empty_ids.py
```
Cela listera toutes les factures avec ID vide.

### Étape 4 : Surveiller le webhook en temps réel
Si le problème vient du webhook :
1. Consulter les logs du serveur webhook
2. Vérifier les payloads reçus dans `webhook_handler.py`
3. Ajouter un délai avant traitement si nécessaire

## Solution temporaire

Si le webhook continue à créer des factures sans ID :

### Option 1 : Ajouter un délai
Dans `webhook_handler.py`, ligne 142, ajouter :
```python
import time
time.sleep(2)  # Attendre 2 secondes avant de récupérer les détails
invoice_details = sellsy.get_invoice_details(resource_id)
```

### Option 2 : Retry avec backoff
Si la première tentative échoue, réessayer après quelques secondes.

### Option 3 : Désactiver temporairement le webhook
Et utiliser uniquement la synchronisation manuelle quotidienne :
```bash
python main.py sync --days 1
```

## Nettoyage des données existantes

Pour supprimer les 2 factures problématiques dans Airtable :
```bash
python cleanup_empty_ids.py
```

Puis re-synchroniser :
```bash
python main.py sync --days 7
```

## Prévention future

1. **Logs activés** : Le fichier `airtable_sync_debug.log` enregistre maintenant tous les IDs
2. **Validation stricte** : Les factures sans ID sont rejetées
3. **ID de secours** : Si l'ID manque dans les détails, on utilise l'ID de la requête

## Surveillance

Vérifier régulièrement :
```bash
# Compter les factures sans ID
grep "ID de facture manquant" airtable_sync_debug.log | wc -l

# Voir les dernières erreurs
tail -50 airtable_sync_debug.log | grep -i error
```
