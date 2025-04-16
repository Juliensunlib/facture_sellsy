import argparse
from sellsy_api import SellsyAPI
from airtable_api import AirtableAPI
import uvicorn
from webhook_handler import app

def sync_invoices(days=30):
    """Synchronise les factures des X derniers jours"""
    sellsy = SellsyAPI()
    airtable = AirtableAPI()
    
    print(f"Récupération des factures des {days} derniers jours...")
    invoices = sellsy.get_invoices(days)
    
    if not invoices:
        print("Aucune facture trouvée.")
        return
    
    print(f"{len(invoices)} factures trouvées.")
    
    for invoice in invoices:
        # Récupérer les détails complets si nécessaire
        invoice_details = sellsy.get_invoice_details(invoice["id"])
        
        if invoice_details:
            # Formater pour Airtable
            formatted_invoice = airtable.format_invoice_for_airtable(invoice_details)
            
            # Insérer ou mettre à jour dans Airtable
            airtable.insert_or_update_invoice(formatted_invoice)
    
    print("Synchronisation terminée.")

def start_webhook_server(host="0.0.0.0", port=8000):
    """Démarre le serveur webhook"""
    print(f"Démarrage du serveur webhook sur {host}:{port}")
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Outil de synchronisation Sellsy - Airtable")
    
    subparsers = parser.add_subparsers(dest="command", help="Commandes disponibles")
    
    # Commande sync
    sync_parser = subparsers.add_parser("sync", help="Synchroniser les factures")
    sync_parser.add_argument("--days", type=int, default=30, help="Nombre de jours à synchroniser")
    
    # Commande webhook
    webhook_parser = subparsers.add_parser("webhook", help="Démarrer le serveur webhook")
    webhook_parser.add_argument("--host", type=str, default="0.0.0.0", help="Hôte du serveur")
    webhook_parser.add_argument("--port", type=int, default=8000, help="Port du serveur")
    
    args = parser.parse_args()
    
    if args.command == "sync":
        sync_invoices(args.days)
    elif args.command == "webhook":
        start_webhook_server(args.host, args.port)
    else:
        parser.print_help()