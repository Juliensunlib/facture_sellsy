import os
import time
import requests
import base64
from pyairtable import Table

# Récupérer les variables d'environnement
SELLSY_CLIENT_ID = os.environ.get("SELLSY_CLIENT_ID")
SELLSY_CLIENT_SECRET = os.environ.get("SELLSY_CLIENT_SECRET")
SELLSY_API_URL = os.environ.get("SELLSY_API_URL", "https://api.sellsy.com/v2")
AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.environ.get("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.environ.get("AIRTABLE_TABLE_NAME")
PDF_STORAGE_DIR = "pdf_invoices"

# Vérifier que le répertoire de stockage des PDF existe
if not os.path.exists(PDF_STORAGE_DIR):
    os.makedirs(PDF_STORAGE_DIR)

def get_access_token():
    """Obtient un token d'accès Sellsy"""
    url = "https://login.sellsy.com/oauth2/access-tokens"
    
    # Authentification avec les identifiants client en Base64
    auth_string = f"{SELLSY_CLIENT_ID}:{SELLSY_CLIENT_SECRET}"
    auth_bytes = auth_string.encode('ascii')
    auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
    
    headers = {
        "Authorization": f"Basic {auth_b64}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }
    
    data = "grant_type=client_credentials"
    
    print("Tentative d'authentification à l'API Sellsy...")
    
    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data["access_token"]
        print("✅ Token d'accès obtenu avec succès")
        return access_token
    else:
        print(f"❌ Erreur d'authentification: {response.status_code}")
        print(response.text)
        raise Exception(f"Échec de l'authentification Sellsy")

def get_all_invoices_once(token, max_size=500):
    """Récupère toutes les factures en une seule requête avec un nombre maximal"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Paramètres de recherche - récupérer le maximum en une fois
    params = {
        "limit": max_size  # Récupérer le maximum de factures en une seule fois
    }
    
    url = f"{SELLSY_API_URL}/invoices"
    print(f"Récupération de toutes les factures (max {max_size}) en une seule requête...")
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        invoices = data.get("data", [])
        print(f"✅ {len(invoices)} factures récupérées en une seule requête")
        return invoices
    else:
        print(f"❌ Erreur lors de la récupération des factures: {response.status_code}")
        print(response.text)
        return []

def get_invoice_details(token, invoice_id):
    """Récupère les détails d'une facture spécifique"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    
    url = f"{SELLSY_API_URL}/invoices/{invoice_id}"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if "data" in data:
            return data.get("data", {})
        else:
            return data
    else:
        print(f"❌ Impossible de récupérer les détails de la facture {invoice_id}")
        return None

def format_invoice_for_airtable(invoice):
    """Convertit une facture Sellsy au format Airtable"""
    if not invoice:
        return None
    
    # Récupérer l'ID client et le nom du client
    client_id = None
    client_name = ""
    
    if "relation" in invoice:
        if "id" in invoice["relation"]:
            client_id = str(invoice["relation"]["id"])
        if "name" in invoice["relation"]:
            client_name = invoice["relation"]["name"]
    elif "related" in invoice:
        for related in invoice.get("related", []):
            if related.get("type") == "individual" or related.get("type") == "corporation":
                client_id = str(related.get("id", ""))
                client_name = related.get("name", "")
                break
        # Si le nom n'est pas disponible directement
        if not client_name:
            client_name = invoice.get("company_name", invoice.get("client_name", "Client #" + str(client_id) if client_id else ""))
    
    # Gestion de la date
    created_date = ""
    for date_field in ["created_at", "date", "created"]:
        if date_field in invoice and invoice[date_field]:
            created_date = invoice[date_field]
            break
    
    if created_date and "T" in created_date:
        created_date = created_date.split("T")[0]
    else:
        created_date = time.strftime("%Y-%m-%d")
    
    # Récupération des montants
    montant_ht = 0
    montant_ttc = 0
    
    if "amounts" in invoice:
        amounts = invoice["amounts"]
        for key in ["total_excluding_tax", "total_excl_tax", "tax_excl", "total_raw_excl_tax"]:
            if key in amounts and amounts[key] is not None:
                montant_ht = amounts[key]
                break
        
        for key in ["total_including_tax", "total_incl_tax", "tax_incl", "total_incl_tax"]:
            if key in amounts and amounts[key] is not None:
                montant_ttc = amounts[key]
                break
    
    # Fallbacks pour les montants
    if montant_ht == 0 and "amount" in invoice and "tax_excl" in invoice["amount"]:
        montant_ht = invoice["amount"]["tax_excl"]
        
    if montant_ttc == 0 and "amount" in invoice and "tax_incl" in invoice["amount"]:
        montant_ttc = invoice["amount"]["tax_incl"]
    
    if montant_ht == 0 and "total_amount_without_taxes" in invoice:
        montant_ht = invoice["total_amount_without_taxes"]
        
    if montant_ttc == 0 and "total_amount_with_taxes" in invoice:
        montant_ttc = invoice["total_amount_with_taxes"]
    
    # Récupération du numéro de facture
    reference = ""
    for ref_field in ["reference", "number", "decimal_number"]:
        if ref_field in invoice and invoice[ref_field]:
            reference = invoice[ref_field]
            break
        
    # Récupération du statut
    status = invoice.get("status", "")
    
    # Récupération du lien PDF direct
    pdf_link = invoice.get("pdf_link", "")
    
    # Conversion des montants en float
    try:
        montant_ht = float(montant_ht) if montant_ht else 0.0
        montant_ttc = float(montant_ttc) if montant_ttc else 0.0
    except (ValueError, TypeError):
        montant_ht = 0.0
        montant_ttc = 0.0
    
    # Création du dictionnaire pour Airtable
    result = {
        "ID_Facture": str(invoice.get("id", "")),
        "Numéro": reference,
        "Date": created_date,
        "Client": client_name,
        "ID_Client_Sellsy": client_id,
        "Montant_HT": montant_ht,
        "Montant_TTC": montant_ttc,
        "Statut": status,
        "URL": f"https://go.sellsy.com/document/{invoice.get('id', '')}"
    }
    
    # Ajouter le lien PDF si disponible
    if pdf_link:
        result["PDF_URL"] = pdf_link
    
    return result

def find_invoice_by_id(table, sellsy_id):
    """Recherche une facture dans Airtable par son ID Sellsy"""
    if not sellsy_id:
        return None
        
    sellsy_id = str(sellsy_id)  # Conversion en chaîne
    formula = f"{{ID_Facture}}='{sellsy_id}'"
    
    try:
        records = table.all(formula=formula)
        return records[0] if records else None
    except Exception as e:
        print(f"❌ Erreur lors de la recherche de la facture {sellsy_id}: {e}")
        return None

def insert_or_update_invoice(table, invoice_data):
    """Insère ou met à jour une facture dans Airtable"""
    if not invoice_data:
        return None
        
    sellsy_id = str(invoice_data.get("ID_Facture", ""))
    if not sellsy_id:
        return None
    
    try:
        existing_record = find_invoice_by_id(table, sellsy_id)

        if existing_record:
            record_id = existing_record["id"]
            print(f"🔄 Mise à jour de la facture {sellsy_id}...")
            table.update(record_id, invoice_data)
            return record_id
        else:
            print(f"➕ Ajout de la facture {sellsy_id}...")
            record = table.create(invoice_data)
            return record['id']
    except Exception as e:
        print(f"❌ Erreur pour la facture {sellsy_id}: {e}")
        return None

def main():
    """Fonction principale qui exécute la synchronisation complète"""
    print("🚀 Début de la synchronisation directe des factures...")
    
    # Obtenir un token d'accès
    access_token = get_access_token()
    
    # Récupérer toutes les factures en une seule requête
    invoices = get_all_invoices_once(access_token)
    
    if not invoices:
        print("❌ Aucune facture récupérée, fin du processus")
        return
    
    print(f"Traitement de {len(invoices)} factures...")
    
    # Initialiser la connexion à Airtable
    airtable_table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)
    
    # Compteurs pour le suivi
    success_count = 0
    error_count = 0
    
    # Traiter chaque facture
    for idx, invoice in enumerate(invoices):
        try:
            invoice_id = str(invoice["id"])
            print(f"\nFacture {idx+1}/{len(invoices)} - ID: {invoice_id}")
            
            # Récupérer les détails complets de la facture
            invoice_details = get_invoice_details(access_token, invoice_id)
            source_data = invoice_details if invoice_details else invoice
            
            # Formater pour Airtable
            formatted_invoice = format_invoice_for_airtable(source_data)
            
            if formatted_invoice:
                # Insérer ou mettre à jour dans Airtable
                record_id = insert_or_update_invoice(airtable_table, formatted_invoice)
                if record_id:
                    success_count += 1
                    print(f"✅ Facture {invoice_id} traitée avec succès")
                else:
                    error_count += 1
            else:
                print(f"⚠️ Impossible de formater la facture {invoice_id}")
                error_count += 1
        except Exception as e:
            print(f"❌ Erreur pour la facture {invoice.get('id', 'inconnue')}: {e}")
            error_count += 1
    
    print(f"\n✅ Synchronisation terminée: {success_count} factures traitées avec succès, {error_count} erreurs")

if __name__ == "__main__":
    main()
