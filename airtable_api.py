from pyairtable import Table
from config import AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME

class AirtableAPI:
    def __init__(self):
        # Connexion à la table Airtable
        self.table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)
    
    def format_invoice_for_airtable(self, invoice):
        """Convertit une facture Sellsy au format Airtable selon les champs de l'API v2"""
        return {
            "ID_Facture": invoice.get("id"),  # ID de la facture dans Sellsy
            "Numéro": invoice.get("reference"),  # Numéro de la facture
            "Date": invoice.get("created_at"),  # Date de création
            "Client": invoice.get("relation", {}).get("name", ""),  # Nom du client
            "Montant_HT": invoice.get("total_amount_without_taxes"),  # Montant hors taxes
            "Montant_TTC": invoice.get("total_amount_with_taxes"),  # Montant TTC
            "Statut": invoice.get("status"),  # Statut de la facture
            "URL": f"https://go.sellsy.com/document/{invoice.get('id')}"  # Lien vers la facture
        }
    
    def find_invoice_by_id(self, sellsy_id):
        """Recherche une facture dans Airtable par son ID Sellsy"""
        records = self.table.all(formula=f"{{ID_Facture}}='{sellsy_id}'")
        return records[0] if records else None
    
    def insert_or_update_invoice(self, invoice_data):
        """Insère ou met à jour une facture dans Airtable"""
        sellsy_id = invoice_data["ID_Facture"]
        
        # Recherche si la facture existe déjà dans Airtable
        existing_record = self.find_invoice_by_id(sellsy_id)
        
        if existing_record:
            # Mise à jour de la facture existante
            record_id = existing_record["id"]
            self.table.update(record_id, invoice_data)
            print(f"Facture {sellsy_id} mise à jour dans Airtable")
            return record_id
        else:
            # Si la facture n'existe pas, l'insérer
            print(f"Facture {sellsy_id} n'existe pas dans Airtable, insertion...")
            record = self.table.create(invoice_data)
            print(f"Facture {sellsy_id} ajoutée à Airtable avec ID {record['id']}")
            return record["id"]

# Code principal pour récupérer les factures de Sellsy et les insérer dans Airtable
def sync_invoices_to_airtable(sellsy_api_client):
    print("Début de la synchronisation des factures manquantes...")
    
    # Récupérer les factures depuis Sellsy (maximum 1000 factures par appel)
    invoices = sellsy_api_client.get_all_invoices()
    
    if invoices:
        print(f"{len(invoices)} factures récupérées depuis Sellsy.")
        
        airtable_api = AirtableAPI()
        
        # Parcourir chaque facture récupérée de Sellsy
        for invoice in invoices:
            formatted_invoice = airtable_api.format_invoice_for_airtable(invoice)
            airtable_api.insert_or_update_invoice(formatted_invoice)
    else:
        print("Aucune facture récupérée depuis Sellsy.")

# Exécution du processus de synchronisation
if __name__ == "__main__":
    # Cette ligne devrait être remplacée par le client Sellsy qui permet de récupérer les factures
    sellsy_api_client = None  # Remplacer par l'instance de ton client Sellsy
    sync_invoices_to_airtable(sellsy_api_client)
