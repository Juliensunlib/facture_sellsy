import requests
import json
import time
import base64
import os
from config import SELLSY_CLIENT_ID, SELLSY_CLIENT_SECRET, SELLSY_API_URL, PDF_STORAGE_DIR

class SellsyAPI:
    def __init__(self):
        self.access_token = None
        self.token_expires_at = 0
        self.api_url = SELLSY_API_URL
        print(f"API URL configurée: {self.api_url}")
        if not SELLSY_CLIENT_ID or not SELLSY_CLIENT_SECRET:
            print("ERREUR: Identifiants Sellsy manquants dans les variables d'environnement")
        
        if not os.path.exists(PDF_STORAGE_DIR):
            os.makedirs(PDF_STORAGE_DIR)
            print(f"Répertoire de stockage des PDF créé: {PDF_STORAGE_DIR}")

    def get_access_token(self):
        """Obtient ou renouvelle le token d'accès Sellsy selon la documentation v2"""
        current_time = time.time()
        
        if self.access_token and current_time < self.token_expires_at - 60:
            return self.access_token
        
        url = "https://login.sellsy.com/oauth2/access-tokens"
        
        auth_string = f"{SELLSY_CLIENT_ID}:{SELLSY_CLIENT_SECRET}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        headers = {
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        
        data = "grant_type=client_credentials"
        
        try:
            response = requests.post(url, headers=headers, data=data)
            
            if response.status_code == 200:
                try:
                    token_data = response.json()
                    self.access_token = token_data["access_token"]
                    self.token_expires_at = current_time + token_data["expires_in"]
                    print("Token d'accès obtenu avec succès")
                    return self.access_token
                except json.JSONDecodeError as e:
                    print(f"Erreur de décodage JSON: {e}")
                    raise Exception("Réponse de l'API Sellsy invalide")
            else:
                print(f"Erreur d'authentification Sellsy: Code {response.status_code}")
                raise Exception(f"Échec de l'authentification Sellsy (code {response.status_code})")
        except requests.exceptions.RequestException as e:
            print(f"Erreur de connexion à l'API Sellsy: {e}")
            raise Exception(f"Impossible de se connecter à l'API Sellsy: {e}")

    def get_invoices(self, days=365):
        """Récupère les factures des derniers jours spécifiés (par défaut 1 an)"""
        token = self.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        start_date = time.strftime("%Y-%m-%d", time.localtime(time.time() - days * 86400))
        
        all_invoices = []
        current_page = 1
        page_size = 100
        has_more_pages = True
        
        print(f"Recherche des factures depuis {start_date}")
        
        while has_more_pages:
            params = {
                "page": current_page,
                "limit": page_size,
                "created_after": f"{start_date}T00:00:00Z"
            }
            
            url = f"{self.api_url}/invoices"
            print(f"Récupération de la page {current_page}: {url}")
            
            try:
                response = requests.get(url, headers=headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    page_invoices = data.get("data", [])
                    total_pages = data.get("pagination", {}).get("nbPages", 1)
                    
                    if not page_invoices:
                        print("Page vide reçue, fin de la pagination")
                        break
                        
                    all_invoices.extend(page_invoices)
                    print(f"Page {current_page}/{total_pages}: {len(page_invoices)} factures récupérées")
                    
                    if current_page >= total_pages:
                        print("Dernière page atteinte")
                        has_more_pages = False
                    else:
                        current_page += 1
                        time.sleep(1)  # Pause entre les requêtes
                        
                elif response.status_code == 401:
                    print("Token expiré, renouvellement...")
                    self.token_expires_at = 0
                    token = self.get_access_token()
                    headers["Authorization"] = f"Bearer {token}"
                else:
                    print(f"Erreur lors de la récupération des factures (page {current_page}): {response.text}")
                    has_more_pages = False
            except Exception as e:
                print(f"Exception lors de la récupération de la page {current_page}: {e}")
                has_more_pages = False
        
        print(f"Total des factures récupérées: {len(all_invoices)}")
        return all_invoices

    def get_all_invoices(self):
        """Récupère toutes les factures sans limite"""
        token = self.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        all_invoices = []
        current_page = 1
        has_more_pages = True
        
        print(f"Récupération de toutes les factures...")
        
        while has_more_pages:
            params = {
                "page": current_page,
                "limit": 100  # Taille de page maximale autorisée par l'API
            }
            
            url = f"{self.api_url}/invoices"
            print(f"Récupération de la page {current_page}: {url}")
            
            try:
                response = requests.get(url, headers=headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    page_invoices = data.get("data", [])
                    pagination = data.get("pagination", {})
                    total_pages = pagination.get("nbPages", 1)
                    
                    if not page_invoices:
                        print("Page vide reçue, fin de la pagination")
                        break
                        
                    all_invoices.extend(page_invoices)
                    print(f"Page {current_page}/{total_pages}: {len(page_invoices)} factures récupérées")
                    
                    if current_page >= total_pages:
                        print("Dernière page atteinte")
                        has_more_pages = False
                    else:
                        current_page += 1
                        time.sleep(1)  # Pause entre les requêtes pour éviter la limitation d'API
                        
                elif response.status_code == 401:
                    print("Token expiré, renouvellement...")
                    self.token_expires_at = 0
                    token = self.get_access_token()
                    headers["Authorization"] = f"Bearer {token}"
                else:
                    print(f"Erreur lors de la récupération des factures (page {current_page}): {response.text}")
                    has_more_pages = False
            except Exception as e:
                print(f"Exception lors de la récupération de la page {current_page}: {e}")
                has_more_pages = False
        
        print(f"Total des factures récupérées: {len(all_invoices)}")
        return all_invoices

    def get_invoice_details(self, invoice_id):
        """Récupère les détails d'une facture spécifique"""
        token = self.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        
        url = f"{self.api_url}/invoices/{invoice_id}"
        print(f"Récupération des détails de la facture {invoice_id}: {url}")
        
        try:
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if "data" in data:
                    print(f"Détails de la facture {invoice_id} récupérés avec succès (format avec data)")
                    return data.get("data", {})
                else:
                    print(f"Détails de la facture {invoice_id} récupérés avec succès (format direct)")
                    return data
            else:
                print(f"Erreur lors de la récupération des détails de la facture {invoice_id}: {response.text}")
                return None
        except Exception as e:
            print(f"Exception lors de la récupération des détails de la facture {invoice_id}: {e}")
            return None
    
    def download_invoice_pdf(self, invoice_id):
        """Télécharge le PDF d'une facture et retourne le chemin du fichier"""
        if not invoice_id:
            print("❌ ID de facture invalide pour le téléchargement du PDF")
            return None
        
        invoice_id = str(invoice_id)
        pdf_filename = f"facture_{invoice_id}.pdf"
        pdf_path = os.path.join(PDF_STORAGE_DIR, pdf_filename)
        
        if os.path.exists(pdf_path):
            print(f"PDF déjà existant pour la facture {invoice_id}: {pdf_path}")
            return pdf_path
        
        invoice_details = self.get_invoice_details(invoice_id)
        if not invoice_details:
            print(f"❌ Impossible de récupérer les détails pour télécharger le PDF")
            return None
        
        pdf_link = invoice_details.get("pdf_link")
        if not pdf_link:
            print(f"❌ Lien PDF non trouvé dans les détails de la facture {invoice_id}")
            return None
        
        print(f"Lien PDF trouvé: {pdf_link}")
        
        token = self.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/pdf"
        }
        
        try:
            response = requests.get(pdf_link, headers=headers)
            
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                if 'pdf' not in content_type.lower() and len(response.content) < 1000:
                    print(f"⚠️ Contenu non PDF reçu: {content_type}")
                    print(f"Aperçu du contenu: {response.content[:100]}")
                    return None
                
                with open(pdf_path, 'wb') as f:
                    f.write(response.content)
                
                print(f"✅ PDF de la facture {invoice_id} téléchargé avec succès: {pdf_path}")
                return pdf_path
            else:
                url = f"{self.api_url}/invoices/{invoice_id}/document"
                print(f"Échec du téléchargement direct, tentative avec l'API standard: {url}")
                
                response = requests.get(url, headers=headers)
                
                if response.status_code == 200:
                    with open(pdf_path, 'wb') as f:
                        f.write(response.content)
                    
                    print(f"✅ PDF de la facture {invoice_id} téléchargé avec succès (méthode alternative)")
                    return pdf_path
                else:
                    print(f"❌ Impossible de télécharger le PDF avec les deux méthodes")
                    with open(pdf_path, 'w') as f:
                        f.write("")
                    print(f"Fichier vide créé pour éviter des tentatives répétées: {pdf_path}")
                    return pdf_path
        except Exception as e:
            print(f"❌ Exception lors du téléchargement du PDF: {e}")
            return None
