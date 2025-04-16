from pyairtable import Table
from config import AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME

class AirtableAPI:
    def __init__(self):
        self.table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)
    
    def format_invoice_for_airtable(self, invoice):
        """Convertit une facture Sellsy au format Airtable selon les champs de l'API v2"""
        return {
            "ID_Facture": invoice.get("id"),
            "Numéro": invoice.get("reference"),
            "Date": invoice.get("created_at"),
            "Client": invoice.get("relation", {}).get("name", ""),
            "Montant_HT": invoice.get("total_amount_without_taxes"),
            "Montant_TTC": invoice.get("total_amount_with_taxes"),
            "Statut": invoice.get("status"),
            "URL": f"https://go.sellsy.com/document/{invoice.get('id')}"
        }
    
    def find_invoice_by_id(self, sellsy_id):
        """Recherche une facture dans Airtable par son ID Sellsy"""
        print(f"Recherche de la facture Sellsy ID: {sellsy_id}")
        records = self.table.all(formula=f"{{ID_Facture}}='{sellsy_id}'")
        if records:
            print(f"Facture trouvée dans Airtable: {records[0]}")
        else:
            print("Aucune facture trouvée.")
        return records[0] if records else None
    
    def insert_or_update_invoice(self, invoice_data):
        """Insère ou met à jour une facture dans Airtable"""
        sellsy_id = invoice_data["ID_Facture"]
        
        # Afficher les données de la facture avant insertion
        print(f"Facture à insérer ou mettre à jour: {invoice_data}")
        
        # Vérifier si la facture existe déjà
        existing_record = self.find_invoice_by_id(sellsy_id)
        print(f"Facture existante trouvée: {existing_record}" if existing_record else "Aucune facture existante trouvée")
        
        if existing_record:
            # Mise à jour
            record_id = existing_record["id"]
            self.table.update(record_id, invoice_data)
            print(f"Facture {sellsy_id} mise à jour dans Airtable")
            return record_id
        else:
            # Insertion
            print(f"Ajout de la facture {sellsy_id} dans Airtable")
            record = self.table.create(invoice_data)
            print(f"Facture {sellsy_id} ajoutée à Airtable avec ID : {record['id']}")
            return record["id"]
