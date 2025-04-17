from pyairtable import Table
from config import AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME
import datetime
import json

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
            
        # Affichage des clés principales pour débogage
        print(f"Structure de la facture - Clés principales: {list(invoice.keys())}")
        
        # Récupérer l'ID client de Sellsy avec gestion des cas où les champs sont manquants
        client_id = None
        client_name = ""
        
        # Vérifier les différentes structures possibles de l'API Sellsy pour les informations client
        if "relation" in invoice:
            if "id" in invoice["relation"]:
                client_id = str(invoice["relation"]["id"])
            if "name" in invoice["relation"]:
                client_name = invoice["relation"]["name"]
        elif "related" in invoice:
            for related in invoice.get("related", []):
                if related.get("type") == "individual" or related.get("type") == "corporation":
                    client_id = str(related.get("id", ""))
                    break
            # Si le nom n'est pas disponible directement
            client_name = invoice.get("company_name", invoice.get("client_name", "Client #" + str(client_id) if client_id else ""))
        
        # Gestion de la date - vérifier plusieurs chemins possibles dans la structure JSON
        created_date = ""
        if "created_at" in invoice and invoice["created_at"]:
            created_date = invoice["created_at"]
        elif "date" in invoice and invoice["date"]:
            created_date = invoice["date"]
        elif "created" in invoice and invoice["created"]:
            created_date = invoice["created"]
        
        # S'assurer que la date est au format YYYY-MM-DD pour Airtable
        if created_date:
            # Si la date contient un T (format ISO), prendre juste la partie date
            if "T" in created_date:
                created_date = created_date.split("T")[0]
        else:
            # Fournir une date par défaut si aucune n'est disponible
            created_date = datetime.datetime.now().strftime("%Y-%m-%d")
            print(f"⚠️ Date non trouvée pour la facture {invoice.get('id', 'inconnue')}, utilisation de la date actuelle")
        
        # Récupération des montants avec gestion des différentes structures possibles
        montant_ht = 0
        montant_ttc = 0
        
        # Afficher les structures de données liées aux montants pour débogage
        if "amounts" in invoice:
            print(f"Structure amounts: {list(invoice['amounts'].keys())}")
        if "amount" in invoice:
            print(f"Structure amount: {list(invoice['amount'].keys())}")
        
        # Méthode 1: Chemins directs connus
        if "total_amount_without_taxes" in invoice:
            montant_ht = invoice["total_amount_without_taxes"]
        elif "amounts" in invoice and "total_excluding_tax" in invoice["amounts"]:
            montant_ht = invoice["amounts"]["total_excluding_tax"]
        elif "amounts" in invoice and "total_excl_tax" in invoice["amounts"]:  # Ajouté
            montant_ht = invoice["amounts"]["total_excl_tax"]
        elif "amounts" in invoice and "tax_excl" in invoice["amounts"]:
            montant_ht = invoice["amounts"]["tax_excl"]
        elif "amount" in invoice and "tax_excl" in invoice["amount"]:
            montant_ht = invoice["amount"]["tax_excl"]
            
        if "total_amount_with_taxes" in invoice:
            montant_ttc = invoice["total_amount_with_taxes"]
        elif "amounts" in invoice and "total_including_tax" in invoice["amounts"]:
            montant_ttc = invoice["amounts"]["total_including_tax"]
        elif "amounts" in invoice and "total_incl_tax" in invoice["amounts"]:  # Ajouté
            montant_ttc = invoice["amounts"]["total_incl_tax"]
        elif "amounts" in invoice and "tax_incl" in invoice["amounts"]:
            montant_ttc = invoice["amounts"]["tax_incl"]
        elif "amount" in invoice and "tax_incl" in invoice["amount"]:
            montant_ttc = invoice["amount"]["tax_incl"]
        
        # Méthode 2: Si les montants n'ont pas été trouvés, afficher la structure complète
        if montant_ht == 0 or montant_ttc == 0:
            print(f"⚠️ Montants incomplets, recherche de chemins alternatifs")
            if "amounts" in invoice:
                print(f"Structure complète de amounts: {json.dumps(invoice['amounts'], indent=2)}")
            
            # Parcourir récursivement pour trouver des clés contenant 'amount', 'total', etc.
            for key, value in invoice.items():
                if isinstance(value, dict):
                    for subkey, subvalue in value.items():
                        if montant_ht == 0 and isinstance(subvalue, (int, float)) and any(term in subkey.lower() for term in ["excluding", "excl", "ht", "without_tax"]):
                            print(f"Montant HT trouvé à {key}.{subkey}: {subvalue}")
                            montant_ht = subvalue
                        if montant_ttc == 0 and isinstance(subvalue, (int, float)) and any(term in subkey.lower() for term in ["including", "incl", "ttc", "with_tax"]):
                            print(f"Montant TTC trouvé à {key}.{subkey}: {subvalue}")
                            montant_ttc = subvalue
        
        # Méthode 3: Recherche par mots-clés dans la structure complète
        if montant_ht == 0 or montant_ttc == 0:
            def search_in_dict(d, ht_keywords, ttc_keywords, path=""):
                results = {"ht": 0, "ttc": 0}
                for key, value in d.items():
                    current_path = f"{path}.{key}" if path else key
                    if isinstance(value, dict):
                        sub_results = search_in_dict(value, ht_keywords, ttc_keywords, current_path)
                        if sub_results["ht"] != 0 and results["ht"] == 0:
                            results["ht"] = sub_results["ht"]
                        if sub_results["ttc"] != 0 and results["ttc"] == 0:
                            results["ttc"] = sub_results["ttc"]
                    elif isinstance(value, (int, float)):
                        if montant_ht == 0 and any(kw in key.lower() for kw in ht_keywords):
                            print(f"Candidat montant HT trouvé à {current_path}: {value}")
                            results["ht"] = value
                        if montant_ttc == 0 and any(kw in key.lower() for kw in ttc_keywords):
                            print(f"Candidat montant TTC trouvé à {current_path}: {value}")
                            results["ttc"] = value
                return results
            
            ht_keywords = ["without_tax", "excluding", "excl", "ht", "net"]
            ttc_keywords = ["with_tax", "including", "incl", "ttc", "gross"]
            
            amount_results = search_in_dict(invoice, ht_keywords, ttc_keywords)
            if amount_results["ht"] != 0 and montant_ht == 0:
                montant_ht = amount_results["ht"]
            if amount_results["ttc"] != 0 and montant_ttc == 0:
                montant_ttc = amount_results["ttc"]
        
        # Récupération du numéro de facture
        reference = ""
        if "reference" in invoice and invoice["reference"]:
            reference = invoice["reference"]
        elif "number" in invoice and invoice["number"]:
            reference = invoice["number"]
            
        # Récupération du statut
        status = invoice.get("status", "")
        
        # Conversion explicite des montants en float pour éviter les problèmes avec Airtable
        try:
            montant_ht = float(montant_ht) if montant_ht else 0.0
            montant_ttc = float(montant_ttc) if montant_ttc else 0.0
        except (ValueError, TypeError) as e:
            print(f"⚠️ Erreur lors de la conversion des montants: {e}")
            print(f"Valeurs avant conversion: HT={montant_ht}, TTC={montant_ttc}")
            # Assigner des valeurs par défaut en cas d'erreur
            montant_ht = 0.0
            montant_ttc = 0.0
        
        # Créer un dictionnaire avec des valeurs par défaut pour éviter les erreurs
        result = {
            "ID_Facture": str(invoice.get("id", "")),  # Conversion explicite en str
            "Numéro": reference,
            "Date": created_date,  # Date formatée correctement
            "Client": client_name,
            "ID_Client_Sellsy": client_id,  # Ajout de l'ID client Sellsy
            "Montant_HT": montant_ht,  # Maintenant c'est un float
            "Montant_TTC": montant_ttc,  # Maintenant c'est un float
            "Statut": status,
            "URL": f"https://go.sellsy.com/document/{invoice.get('id', '')}"
        }
        
        print(f"Montants finaux (après conversion): HT={montant_ht} (type: {type(montant_ht)}), TTC={montant_ttc} (type: {type(montant_ttc)})")
        return result

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
            print(f"Clés dans les données: {list(invoice_data.keys()) if invoice_data else 'N/A'}")
            print(f"Valeur du champ Date: '{invoice_data.get('Date', 'N/A')}'" if invoice_data else "N/A")
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
