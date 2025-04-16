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
    
    # Calcul de la signature (HMAC SHA-256)
    signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(signature, x_sellsy_signature):
        raise HTTPException(status_code=401, detail="Signature invalide")
    
    return json.loads(body)

@app.post("/webhook/sellsy")
async def handle_webhook(payload: dict = Depends(verify_webhook)):
    """Gère les webhooks entrants de Sellsy"""
    event_type = payload.get("event_type")
    
    # Adaptation pour l'API v2 de Sellsy
    if event_type in ["invoice.created", "invoice.updated"]:
        resource_id = payload.get("resource_id")
        
        if resource_id:
            # Récupérer les détails complets de la facture
            invoice_details = sellsy.get_invoice_details(resource_id)
            
            if invoice_details:
                # Formater et enregistrer dans Airtable
                formatted_invoice = airtable.format_invoice_for_airtable(invoice_details)
                airtable.insert_or_update_invoice(formatted_invoice)
                return {"status": "success", "message": f"Facture {resource_id} traitée"}
    
    return {"status": "ignored", "message": "Événement non traité"}
