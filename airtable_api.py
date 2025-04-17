from pyairtable import Table
from config import AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME

class AirtableAPI:
    def __init__(self):
        """Initialisation de la connexion à Airtable"""
        self.table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)

    def format_invoice_for_airtable(self, invoice):
        """Convertit une facture Sellsy au format Airtable"""
        # Vérifications de sécurité pour éviter les erreurs si des champs sont manquants
        if not invoice:
            print("⚠️ Données de facture invalides ou vides")
            return None
            
        # Récupérer l'ID client de Sellsy avec gestion des cas où les champs sont manquants
        client_id = None
        client_name = ""
        
        if "relation" in invoice:
            if "id" in invoice["relation"]:
                client_id = str(invoice["relation"]["id"])
            if "name" in invoice["relation"]:
                client_name = invoice["relation"]["name"]
        
        # Créer un dictionnaire avec des valeurs par défaut pour éviter les erreurs
        return {
            "ID_Facture": str(invoice.get("id", "")),  # Conversion explicite en str
            "Numéro": invoice.get("reference", ""),
            "Date": invoice.get("created_at", ""),
            "Client": client_name,
            "ID_Client_Sellsy": client_id,  # Ajout de l'ID client Sellsy
            "Montant_HT": invoice.get("total_amount_without_taxes", 0),
            "Montant_TTC": invoice.get("total_amount_with_taxes", 0),
            "Statut": invoice.get("status", ""),
            "URL": f"https://go.sellsy.com/document/{invoice.get('id', '')}"
        }

    def find_invoice_by_id(self, sellsy_id):
        """Recherche une facture dans Airtable par son ID Sellsy"""
        if not sellsy_id:
            print("⚠️ ID Sellsy vide, impossible de rechercher la facture")
            return None
            
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
        if not invoice_data:
            print("❌ Données de facture invalides, impossible d'insérer/mettre à jour")
            return None
            
        sellsy_id = str(invoice_data.get("ID_Facture", ""))
        if not sellsy_id:
            print("❌ ID Sellsy manquant dans les données, impossible d'insérer/mettre à jour")
            return None
            
        try:
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
                return record['id']
        except Exception as e:
            print(f"❌ Erreur lors de l'insertion/mise à jour de la facture {sellsy_id}: {e}")
            # Afficher les clés pour le débogage
            print(f"Clés dans les données: {list(invoice_data.keys())}")
            raise e

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
            if formatted_invoice:
                airtable_api.insert_or_update_invoice(formatted_invoice)

        print("✅ Synchronisation terminée.")
    else:
        print("⚠️ Aucune facture récupérée depuis Sellsy.")

# Exécution directe (à remplacer ou adapter selon ton client Sellsy)
if __name__ == "__main__":
    from sellsy_api import SellsyAPI  # Import your SellsyAPI class
    sellsy_api_client = SellsyAPI()
    sync_invoices_to_airtable(sellsy_api_client)
