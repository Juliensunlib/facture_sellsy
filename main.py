import argparse
from sellsy_api import SellsyAPI
from airtable_api import AirtableAPI
import uvicorn
from webhook_handler import app
import time

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
    
    for idx, invoice in enumerate(invoices):
        try:
            # Récupérer les détails complets si nécessaire
            invoice_id = str(invoice["id"])
            print(f"Traitement de la facture {invoice_id} ({idx+1}/{len(invoices)})...")
            
            # Ajouter un délai entre les requêtes pour éviter les limitations d'API
            if idx > 0 and idx % 10 == 0:
                print("Pause de 2 secondes pour éviter les limitations d'API...")
                time.sleep(2)
                
            invoice_details = sellsy.get_invoice_details(invoice_id)
            
            if invoice_details:
                # Formater pour Airtable
                formatted_invoice = airtable.format_invoice_for_airtable(invoice_details)
                
                # Insérer ou mettre à jour dans Airtable
                airtable.insert_or_update_invoice(formatted_invoice)
                print(f"✅ Facture {invoice_id} traitée ({idx+1}/{len(invoices)}).")
            else:
                print(f"⚠️ Impossible de récupérer les détails de la facture {invoice_id} - utilisation des données de base")
                # Utilisez les données de base si les détails ne sont pas disponibles
                basic_invoice = {
                    "id": invoice["id"],
                    "reference": invoice.get("reference", ""),
                    "status": invoice.get("status", ""),
                    "created_at": invoice.get("created_at", ""),
                    "total_amount_without_taxes": invoice.get("total_amount_without_taxes", 0),
                    "total_amount_with_taxes": invoice.get("total_amount_with_taxes", 0),
                    "relation": {
                        "id": invoice.get("client_id", ""),
                        "name": invoice.get("client_name", "")
                    }
                }
                formatted_invoice = airtable.format_invoice_for_airtable(basic_invoice)
                airtable.insert_or_update_invoice(formatted_invoice)
        except Exception as e:
            print(f"❌ Erreur lors du traitement de la facture {invoice.get('id')}: {e}")
    
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
    updated_count = 0
    error_count = 0
    
    for idx, invoice in enumerate(all_invoices):
        try:
            invoice_id = str(invoice["id"])
            print(f"Traitement de la facture {invoice_id} ({idx+1}/{len(all_invoices)})...")
            
            # Ajouter un délai entre les requêtes pour éviter les limitations d'API
            if idx > 0 and idx % 10 == 0:
                print("Pause de 2 secondes pour éviter les limitations d'API...")
                time.sleep(2)
            
            # Vérifier d'abord si la facture existe déjà dans Airtable
            existing_record = airtable.find_invoice_by_id(invoice_id)
            
            if existing_record:
                # Si la facture existe déjà, pas besoin de récupérer les détails complets
                print(f"🔄 Facture {invoice_id} déjà présente dans Airtable, passage à la suivante.")
                updated_count += 1
                continue
                
            # Récupérer les détails complets de la facture
            invoice_details = sellsy.get_invoice_details(invoice_id)
            
            if not invoice_details:
                print(f"⚠️ Impossible de récupérer les détails de la facture {invoice_id} - utilisation des données de base")
                # Utilisez les données de base si les détails ne sont pas disponibles
                basic_invoice = {
                    "id": invoice["id"],
                    "reference": invoice.get("reference", ""),
                    "status": invoice.get("status", ""),
                    "created_at": invoice.get("created_at", ""),
                    "total_amount_without_taxes": invoice.get("total_amount_without_taxes", 0),
                    "total_amount_with_taxes": invoice.get("total_amount_with_taxes", 0),
                    "relation": {
                        "id": invoice.get("client_id", ""),
                        "name": invoice.get("client_name", "")
                    }
                }
                formatted_invoice = airtable.format_invoice_for_airtable(basic_invoice)
            else:
                # Formater pour Airtable
                formatted_invoice = airtable.format_invoice_for_airtable(invoice_details)
            
            # Ajouter à Airtable
            try:
                airtable.table.create(formatted_invoice)
                added_count += 1
                print(f"➕ Facture {invoice_id} ajoutée ({idx+1}/{len(all_invoices)}).")
            except Exception as e:
                print(f"❌ Erreur lors de l'ajout de la facture {invoice_id} à Airtable: {e}")
                error_count += 1
                
        except Exception as e:
            print(f"❌ Erreur lors du traitement de la facture {invoice.get('id')}: {e}")
            error_count += 1
    
    print(f"Synchronisation terminée. {added_count} nouvelles factures ajoutées, {updated_count} factures déjà présentes, {error_count} erreurs.")

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
