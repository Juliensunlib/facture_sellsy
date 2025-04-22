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

async def verify_webhook(request: Request):
    """Vérifie la signature du webhook Sellsy (v2)"""
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"Webhook request received from {client_ip}")
    
    # Récupérer tous les headers pour déboguer
    headers = dict(request.headers.items())
    logger.info(f"Received headers: {headers}")
    
    # Vérifier tous les headers possibles pour la signature Sellsy
    # Ajouter x-webhook-signature qui est le format utilisé selon les logs
    sellsy_signature = (headers.get('x-sellsy-signature') or 
                        headers.get('X-Sellsy-Signature') or 
                        headers.get('x-sellsy-signature-256') or 
                        headers.get('X-Sellsy-Signature-256') or
                        headers.get('x-webhook-signature') or
                        headers.get('X-Webhook-Signature'))
    
    # Vérifier si la signature est présente
    if not sellsy_signature:
        logger.warning("Missing Sellsy signature in request")
        raise HTTPException(status_code=401, detail="Signature manquante")
    
    # Récupérer le contenu brut de la requête
    body = await request.body()
    
    # Log pour déboguer
    logger.info(f"Webhook received - Signature: {sellsy_signature}")
    body_str = body.decode('utf-8') if body else "empty"
    logger.info(f"Raw body content (first 200 chars): {body_str[:200]}...")
    
    # Analyser le JSON pour comprendre le type d'événement
    try:
        body_json = json.loads(body)
        
        # Adapter à la structure réelle du webhook
        # Regarder "eventType" (noté dans les logs) au lieu de "event_type"
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
    
    # Vérifier si le secret webhook est configuré
    if not WEBHOOK_SECRET:
        logger.error("WEBHOOK_SECRET is not configured in environment variables")
        raise HTTPException(status_code=500, detail="Configuration de webhook incomplète")
    
    # Calcul de la signature (HMAC SHA-1)
    try:
        # D'après les logs, le webhook utilise SHA-1
        calculated_signature = hmac.new(
            WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha1
        ).hexdigest()
        
        logger.info(f"Calculated signature: {calculated_signature}")
        logger.info(f"Comparing with received signature: {sellsy_signature}")
        
        # Comparaison sécurisée des signatures
        if not hmac.compare_digest(calculated_signature, sellsy_signature):
            logger.warning("❌ Invalid signature, rejecting request")
            raise HTTPException(status_code=401, detail="Signature invalide")
        
        logger.info("✅ Signature validated successfully")
        return body_json
    except Exception as e:
        logger.error(f"Error during signature verification: {str(e)}")
        raise HTTPException(status_code=401, detail="Erreur lors de la vérification de la signature")

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
    
    return {
        "status": "online", 
        "time": str(datetime.now()),
        "env_vars_present": env_vars,
        "sellsy_api_status": sellsy_status
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
