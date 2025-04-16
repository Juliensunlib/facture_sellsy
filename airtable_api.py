from pyairtable import Table
from config import AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME

class AirtableAPI:
    def __init__(self):
        """Initialisation de la connexion à Airtable"""
        self.table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)

    def format_invoice_for_airtable(self, invoice):
        """Convertit une facture Sellsy au format Airtable"""
        return {
            "ID_Facture": str(invoice.get("id")),  # Conversion explicite en str
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
        sellsy_id = str(sellsy_id)  # Sécurité : conversion en chaîne
        formula = f"{{ID_Facture}}='{sellsy_id}'"
        print(f"🔍 Recherche dans Airtable avec formule : {formula}")
        try:
            records = self.table.all(formula=formula)
            print(f"Résultat de recherche : {len(records)} enregistrement(s) trouvé(s).")
            return records[0] if records else None
        except Exception as e:
            print(f"❌ Erreur lors de la recherche de la facture {sellsy_id} : {e}")
            return None

    def insert_or_update_invoice(self, invoice_data):
        """Insère ou met à jour une facture dans Airtable"""
        sellsy_id = str(invoice_data["ID_Facture"])
        existing_record = self.find_invoice_by_id(sellsy_id)

        if existing_record:
            record_id = existing_record["id"]
            print(f"🔁 Facture {sellsy_id} déjà présente, mise à jour en cours...")
            self.table.update(record_id, invoice_data)
            print(f"✅ Facture {sellsy_id} mise à jour avec succès.")
            return record_id
        else:
            print(f"➕ Facture {sellsy_id} non trouvée, insertion en cours...")
            record = self.table.create(invoice_data)
            print(f"✅ Facture {sellsy_id} ajoutée avec succès à Airtable (ID: {record['id']}).")
            return record["id"]

# Code principal pour synchroniser les factures Sellsy avec Airtable
def sync_invoices_to_airtable(sellsy_api_client):
    print("🚀 Début de la synchronisation des factures Sellsy vers Airtable...")

    # Récupère toutes les factures depuis Sellsy
    invoices = sellsy_api_client.get_all_invoices()

    if invoices:
        print(f"📦 {len(invoices)} factures récupérées depuis Sellsy.")
        airtable_api = AirtableAPI()

        # Parcours des factures récupérées et insertion ou mise à jour dans Airtable
        for invoice in invoices:
            formatted_invoice = airtable_api.format_invoice_for_airtable(invoice)
            airtable_api.insert_or_update_invoice(formatted_invoice)

        print("✅ Synchronisation terminée.")
    else:
        print("⚠️ Aucune facture récupérée depuis Sellsy.")

# Exécution directe (à remplacer ou adapter selon ton client Sellsy)
if __name__ == "__main__":
    from sellsy_client import SellsyClient  # Ton client Sellsy à part
    sellsy_api_client = SellsyClient()
    sync_invoices_to_airtable(sellsy_api_client)
