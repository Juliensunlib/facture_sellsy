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

def sync_missing_invoices(limit=1000):
    """Synchronise les factures manquantes dans Airtable"""
    sellsy = SellsyAPI()
    airtable = AirtableAPI()
    
    print(f"Récupération de toutes les factures de Sellsy (max {limit})...")
    all_invoices = sellsy.get_all_invoices(limit)
    
    if not all_invoices:
        print("Aucune facture trouvée.")
        return
    
    print(f"{len(all_invoices)} factures trouvées dans Sellsy.")
    
    added_count = 0
    for invoice in all_invoices:
        # Vérifier si la facture existe déjà dans Airtable
        existing = airtable.find_invoice_by_id(invoice["id"])
        
        if not existing:
            # Si la facture n'existe pas, récupérer les détails complets
            invoice_details = sellsy.get_invoice_details(invoice["id"])
            
            if invoice_details:
                # Formater pour Airtable
                formatted_invoice = airtable.format_invoice_for_airtable(invoice_details)
                
                # Insérer dans Airtable
                airtable.insert_or_update_invoice(formatted_invoice)
                added_count += 1
    
    print(f"Synchronisation terminée. {added_count} nouvelles factures ajoutées.")

def start_webhook_server(host="0.0.0.0", port=8000):
    """Démarre le serveur webhook"""
    print(f"Démarrage du serveur webhook sur {host}:{port}")
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Outil de synchronisation Sellsy - Airtable")
    
    subparsers = parser.add_subparsers(dest="command", help="Commandes disponibles")
    
    # Commande sync
    sync_parser = subparsers.add_parser("sync", help="Synchroniser les factures des derniers jours")
    sync_parser.add_argument("--days", type=int, default=30, help="Nombre de jours à synchroniser")
    
    # Commande sync-missing
    missing_parser = subparsers.add_parser("sync-missing", help="Synchroniser les factures manquantes")
    missing_parser.add_argument("--limit", type=int, default=1000, help="Nombre maximum de factures à vérifier")
    
    # Commande webhook
    webhook_parser = subparsers.add_parser("webhook", help="Démarrer le serveur webhook")
    webhook_parser.add_argument("--host", type=str, default="0.0.0.0", help="Hôte du serveur")
    webhook_parser.add_argument("--port", type=int, default=8000, help="Port du serveur")
    
    args = parser.parse_args()
    
    if args.command == "sync":
        sync_invoices(args.days)
    elif args.command == "sync-missing":
        sync_missing_invoices(args.limit)
    elif args.command == "webhook":
        start_webhook_server(args.host, args.port)
    else:
        parser.print_help()
