from pyairtable import Table
from config import AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME

class AirtableAPI:
    def __init__(self):
        self.table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)
    
    def format_invoice_for_airtable(self, invoice):
        """Convertit une facture Sellsy au format Airtable selon les champs de l'API v2"""
        # Format adapté pour l'API v2 de Sellsy
        return {
            "ID_Facture": invoice.get("id"),
            "Numéro": invoice.get("reference"), # Changement possible selon la documentation
            "Date": invoice.get("created_at"),
            "Client": invoice.get("relation", {}).get("name", ""),
            "Montant_HT": invoice.get("total_amount_without_taxes"),
            "Montant_TTC": invoice.get("total_amount_with_taxes"),
            "Statut": invoice.get("status"),
            "URL": f"https://go.sellsy.com/document/{invoice.get('id')}"
        }
    
    def find_invoice_by_id(self, sellsy_id):
        """Recherche une facture dans Airtable par son ID Sellsy"""
        records = self.table.all(formula=f"{{ID_Facture}}='{sellsy_id}'")
        return records[0] if records else None
    
    def insert_or_update_invoice(self, invoice_data):
        """Insère ou met à jour une facture dans Airtable"""
        sellsy_id = invoice_data["ID_Facture"]
        
        # Vérifier si la facture existe déjà
        existing_record = self.find_invoice_by_id(sellsy_id)
        
        if existing_record:
            # Mise à jour
            record_id = existing_record["id"]
            self.table.update(record_id, invoice_data)
            print(f"Facture {sellsy_id} mise à jour dans Airtable")
            return record_id
        else:
            # Insertion
            record = self.table.create(invoice_data)
            print(f"Facture {sellsy_id} ajoutée à Airtable")
            return record["id"]
