from fastapi import FastAPI, Request, Header, HTTPException, Depends
import hmac
import hashlib
import json
import os
import logging
from datetime import datetime
from sellsy_api import SellsyAPI
from airtable_api import AirtableAPI
from config import WEBHOOK_SECRET

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("webhook_handler")

app = FastAPI()
sellsy = SellsyAPI()
airtable = AirtableAPI()

# Mode de développement temporaire pour accepter toutes les signatures
# ATTENTION: Ne pas laisser activé en production sans restriction d'IP
DEBUG_SKIP_SIGNATURE = True  # Mettre à False une fois le problème résolu

async def verify_webhook(request: Request):
    """Vérifie la signature du webhook Sellsy (v2)"""
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"Webhook request received from {client_ip}")
    
    # Récupérer tous les headers pour déboguer
    headers = dict(request.headers.items())
    logger.info(f"Received headers: {headers}")
    
    # Vérifier tous les headers possibles pour la signature Sellsy
    sellsy_signature = (headers.get('x-sellsy-signature') or 
                        headers.get('X-Sellsy-Signature') or 
                        headers.get('x-sellsy-signature-256') or 
                        headers.get('X-Sellsy-Signature-256') or
                        headers.get('x-webhook-signature') or
                        headers.get('X-Webhook-Signature'))
    
    # En mode debug, continuer même sans signature
    if not sellsy_signature and not DEBUG_SKIP_SIGNATURE:
        logger.warning("Missing Sellsy signature in request")
        raise HTTPException(status_code=401, detail="Signature manquante")
    
    # Récupérer le contenu brut de la requête
    body = await request.body()
    
    # Log pour déboguer
    if sellsy_signature:
        logger.info(f"Webhook received - Signature: {sellsy_signature}")
    body_str = body.decode('utf-8') if body else "empty"
    logger.info(f"Raw body content (first 200 chars): {body_str[:200]}...")
    
    # Analyser le JSON pour comprendre le type d'événement
    try:
        body_json = json.loads(body)
        
        # Adapter à la structure réelle du webhook
        event_type = body_json.get("eventType", "unknown")
        
        # Trouver l'ID de ressource via la structure du webhook
        resource_id = None
        if "relatedid" in body_json:
            resource_id = body_json.get("relatedid")
        elif "resource_id" in body_json:
            resource_id = body_json.get("resource_id")
            
        logger.info(f"Event type: {event_type}, Resource ID: {resource_id}")
    except json.JSONDecodeError as e:
        logger.error(f"Could not parse webhook body as JSON: {e}")
        raise HTTPException(status_code=400, detail="JSON invalide")
    
    # En mode debug, on peut sauter la vérification de signature
    if DEBUG_SKIP_SIGNATURE:
        logger.warning("⚠️ Mode DEBUG actif : vérification de signature désactivée")
        return body_json
    
    # Vérifier si le secret webhook est configuré
    if not WEBHOOK_SECRET:
        logger.error("WEBHOOK_SECRET is not configured in environment variables")
        raise HTTPException(status_code=500, detail="Configuration de webhook incomplète")
    
    # Essayer différentes méthodes de calcul de signature
    signature_methods = [
        # SHA-1 standard
        lambda: hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha1).hexdigest(),
        # SHA-1 avec trimming des blancs
        lambda: hmac.new(WEBHOOK_SECRET.encode(), body.strip(), hashlib.sha1).hexdigest(),
        # SHA-256 (au cas où)
        lambda: hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest(),
        # Essayer avec un secret sans espaces
        lambda: hmac.new(WEBHOOK_SECRET.strip().encode(), body, hashlib.sha1).hexdigest(),
    ]
    
    # Tester toutes les méthodes
    for i, signature_method in enumerate(signature_methods):
        try:
            calculated_signature = signature_method()
            logger.info(f"Méthode {i+1}: Signature calculée: {calculated_signature}")
            
            if hmac.compare_digest(calculated_signature, sellsy_signature):
                logger.info(f"✅ Signature validée avec la méthode {i+1}")
                return body_json
        except Exception as e:
            logger.error(f"Erreur avec la méthode {i+1}: {str(e)}")
    
    # Si aucune méthode ne fonctionne
    logger.warning("❌ Signature invalide avec toutes les méthodes essayées")
    raise HTTPException(status_code=401, detail="Signature invalide")

@app.post("/webhook/sellsy")
async def handle_webhook(request: Request):
    """Gère les webhooks entrants de Sellsy"""
    try:
        payload = await verify_webhook(request)
        
        # Adapter pour utiliser la structure réelle du webhook
        event_type = payload.get("eventType")
        
        # Dans cette structure, l'ID de la facture est soit dans relatedid, soit dans un autre champ
        resource_id = payload.get("relatedid") or payload.get("resource_id", "unknown")
        related_type = payload.get("relatedtype", "unknown")
        
        logger.info(f"Processing webhook: {event_type} for {related_type} {resource_id}")
        
        # Vérifier que c'est bien une facture
        if related_type == "invoice" and resource_id:
            # Accepter soit les événements docslog, soit les événements invoice standards
            if event_type in ["docslog", "invoice.created", "invoice.updated"]:
                logger.info(f"Traitement de la facture {resource_id} depuis le webhook")
                
                try:
                    # Récupérer les détails complets de la facture
                    logger.info(f"Récupération des détails de la facture {resource_id}...")
                    invoice_details = sellsy.get_invoice_details(resource_id)
                    
                    if not invoice_details:
                        logger.error(f"Impossible de récupérer les détails de la facture {resource_id}")
                        return {"status": "error", "message": f"Impossible de récupérer les détails de la facture {resource_id}"}
                    
                    logger.info(f"Détails de la facture {resource_id} récupérés avec succès")
                    
                    # Formater la facture pour Airtable
                    logger.info("Formatage des données de la facture pour Airtable...")
                    formatted_invoice = airtable.format_invoice_for_airtable(invoice_details)
                    
                    if not formatted_invoice:
                        logger.error("Échec du formatage des données de la facture")
                        return {"status": "error", "message": "Impossible de formater les données de la facture"}
                    
                    logger.info("Données de la facture formatées avec succès")
                    
                    # Télécharger le PDF de la facture
                    logger.info(f"Téléchargement du PDF de la facture {resource_id}...")
                    pdf_path = sellsy.download_invoice_pdf(resource_id)
                    logger.info(f"PDF téléchargé: {pdf_path if pdf_path else 'échec'}")
                    
                    # Insérer ou mettre à jour dans Airtable
                    logger.info("Insertion/mise à jour dans Airtable...")
                    record_id = airtable.insert_or_update_invoice(formatted_invoice, pdf_path)
                    
                    logger.info(f"✅ Facture {resource_id} traitée avec succès dans Airtable (ID: {record_id})")
                    return {
                        "status": "success", 
                        "message": f"Facture {resource_id} traitée dans Airtable (ID: {record_id})",
                        "timestamp": str(datetime.now())
                    }
                    
                except Exception as e:
                    logger.exception(f"Exception lors du traitement du webhook pour la facture {resource_id}: {e}")
                    return {
                        "status": "error", 
                        "message": f"Erreur lors du traitement: {str(e)}",
                        "timestamp": str(datetime.now())
                    }
            else:
                logger.info(f"Type d'événement non géré: {event_type}")
                return {"status": "ignored", "message": f"Type d'événement non géré: {event_type}"}
        else:
            logger.info(f"Type de ressource non géré: {related_type}")
            return {"status": "ignored", "message": f"Type de ressource non géré: {related_type}"}
    except HTTPException as http_ex:
        # Réutiliser l'exception HTTP déjà levée
        raise http_ex
    except Exception as e:
        logger.exception(f"Erreur non gérée dans le handler webhook: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne du serveur: {str(e)}")

@app.get("/webhook/test")
async def test_webhook():
    """Endpoint de test pour vérifier que le serveur est en ligne"""
    logger.info(f"Test endpoint called at {datetime.now()}")
    
    # Vérifier la présence des variables d'environnement nécessaires
    env_vars = {
        "WEBHOOK_SECRET": bool(WEBHOOK_SECRET),
        "SELLSY_CLIENT_ID": bool(os.environ.get("SELLSY_CLIENT_ID")),
        "SELLSY_CLIENT_SECRET": bool(os.environ.get("SELLSY_CLIENT_SECRET")),
        "AIRTABLE_API_KEY": bool(os.environ.get("AIRTABLE_API_KEY")),
        "AIRTABLE_BASE_ID": bool(os.environ.get("AIRTABLE_BASE_ID")),
        "AIRTABLE_TABLE_NAME": bool(os.environ.get("AIRTABLE_TABLE_NAME"))
    }
    
    # Tester la connexion à l'API Sellsy
    sellsy_status = "unknown"
    try:
        token = sellsy.get_access_token()
        sellsy_status = "connected" if token else "failed_to_get_token"
    except Exception as e:
        sellsy_status = f"error: {str(e)}"
    
    # Afficher le webhook secret (partiellement masqué)
    secret_display = "Non configuré"
    if WEBHOOK_SECRET:
        secret_len = len(WEBHOOK_SECRET)
        if secret_len > 8:
            secret_display = WEBHOOK_SECRET[:4] + "..." + WEBHOOK_SECRET[-4:]
        else:
            secret_display = "Configuré (trop court pour afficher partiellement)"
    
    return {
        "status": "online", 
        "time": str(datetime.now()),
        "env_vars_present": env_vars,
        "sellsy_api_status": sellsy_status,
        "webhook_secret": secret_display,
        "debug_mode": DEBUG_SKIP_SIGNATURE
    }

@app.get("/")
async def root():
    """Page d'accueil simple"""
    return {
        "service": "Sellsy-Airtable Integration",
        "status": "running",
        "endpoints": {
            "webhook": "/webhook/sellsy",
            "test": "/webhook/test"
        }
    }
