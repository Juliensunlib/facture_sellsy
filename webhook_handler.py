from fastapi import FastAPI, Request, Header, HTTPException, Depends
import hmac
import hashlib
import json
from sellsy_api import SellsyAPI
from airtable_api import AirtableAPI
from config import WEBHOOK_SECRET

app = FastAPI()
sellsy = SellsyAPI()
airtable = AirtableAPI()

async def verify_webhook(request: Request, x_sellsy_signature: str = Header(None)):
    """Vérifie la signature du webhook Sellsy (v2)"""
    if not x_sellsy_signature:
        raise HTTPException(status_code=401, detail="Signature manquante")
    
    body = await request.body()
    
    # Log pour déboguer
    print(f"Webhook reçu - Signature: {x_sellsy_signature}")
    print(f"Contenu du webhook (premiers 100 caractères): {body[:100]}...")
    
    # Calcul de la signature (HMAC SHA-256)
    signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    print(f"Signature calculée: {signature}")
    
    if not hmac.compare_digest(signature, x_sellsy_signature):
        print("❌ Signature invalide, rejeter la requête")
        raise HTTPException(status_code=401, detail="Signature invalide")
    
    print("✅ Signature validée")
    return json.loads(body)

@app.post("/webhook/sellsy")
async def handle_webhook(payload: dict = Depends(verify_webhook)):
    """Gère les webhooks entrants de Sellsy"""
    event_type = payload.get("event_type")
    print(f"Événement reçu: {event_type}")
    
    # Adaptation pour l'API v2 de Sellsy
    if event_type in ["invoice.created", "invoice.updated"]:
        resource_id = payload.get("resource_id")
        
        if resource_id:
            print(f"Traitement de la facture {resource_id} depuis le webhook")
            # Récupérer les détails complets de la facture
            invoice_details = sellsy.get_invoice_details(resource_id)
            
            if invoice_details:
                # Formater la facture pour Airtable
                formatted_invoice = airtable.format_invoice_for_airtable(invoice_details)
                
                if not formatted_invoice:
                    return {"status": "error", "message": "Impossible de formater les données de la facture"}
                
                # Insérer ou mettre à jour dans Airtable (utilise la fonction existante qui gère les deux cas)
                try:
                    record_id = airtable.insert_or_update_invoice(formatted_invoice)
                    return {"status": "success", "message": f"Facture {resource_id} traitée dans Airtable (ID: {record_id})"}
                except Exception as e:
                    print(f"Erreur lors de l'insertion/mise à jour dans Airtable: {e}")
                    return {"status": "error", "message": f"Erreur lors du traitement dans Airtable: {str(e)}"}
            else:
                return {"status": "error", "message": f"Impossible de récupérer les détails de la facture {resource_id}"}
        else:
            return {"status": "error", "message": "ID de ressource manquant dans l'événement"}
    
    return {"status": "ignored", "message": "Événement non traité"}

@app.get("/")
async def root():
    """Route racine pour vérifier que le serveur fonctionne"""
    return {"status": "ok", "message": "Webhook Sellsy-Airtable opérationnel"}
