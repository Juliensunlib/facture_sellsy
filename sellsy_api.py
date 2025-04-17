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
        print(f"API URL configurée: {self.api_url}")import requests
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
        # Vérifier que les identifiants sont bien définis (sans les afficher)
        if not SELLSY_CLIENT_ID or not SELLSY_CLIENT_SECRET:
            print("ERREUR: Identifiants Sellsy manquants dans les variables d'environnement")
        
        # Créer le répertoire de stockage des PDF s'il n'existe pas
        if not os.path.exists(PDF_STORAGE_DIR):
            os.makedirs(PDF_STORAGE_DIR)
            print(f"Répertoire de stockage des PDF créé: {PDF_STORAGE_DIR}")

    def get_access_token(self):
        """Obtient ou renouvelle le token d'accès Sellsy selon la documentation v2"""
        current_time = time.time()
        
        # Vérifier si le token est encore valide
        if self.access_token and current_time < self.token_expires_at - 60:
            return self.access_token
        
        # Si non, demander un nouveau token
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
        
        print(f"Tentative d'authentification à l'API Sellsy: {url}")
        
        try:
            response = requests.post(url, headers=headers, data=data)
            print(f"Statut de la réponse: {response.status_code}")
            print(f"En-têtes de la réponse: {response.headers.get('Content-Type')}")
            
            if response.status_code == 200:
                try:
                    token_data = response.json()
                    self.access_token = token_data["access_token"]
                    self.token_expires_at = current_time + token_data["expires_in"]
                    print("Token d'accès obtenu avec succès")
                    return self.access_token
                except json.JSONDecodeError as e:
                    print(f"Erreur de décodage JSON: {e}")
                    print(f"Contenu de la réponse (100 premiers caractères): {response.text[:100]}")
                    raise Exception("Réponse de l'API Sellsy invalide")
            else:
                print(f"Erreur d'authentification Sellsy: Code {response.status_code}")
                print(f"Réponse complète: {response.text}")
                raise Exception(f"Échec de l'authentification Sellsy (code {response.status_code})")
        except requests.exceptions.RequestException as e:
            print(f"Erreur de connexion à l'API Sellsy: {e}")
            raise Exception(f"Impossible de se connecter à l'API Sellsy: {e}")

    def get_invoices(self, days=30):
        """Récupère les factures des derniers jours spécifiés"""
        token = self.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Calculer la date de début (il y a X jours)
        start_date = time.strftime("%Y-%m-%d", time.localtime(time.time() - days * 86400))
        
        # Paramètres de recherche pour les factures - adaptés à l'API v2
        params = {
            "page": 1,
            "limit": 100,
            "created_after": f"{start_date}T00:00:00Z"
        }
        
        url = f"{self.api_url}/invoices"
        print(f"Recherche des factures depuis {start_date}: {url}")
        
        try:
            response = requests.get(url, headers=headers, params=params)
            print(f"Statut de la réponse: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                invoices = data.get("data", [])
                print(f"Nombre de factures trouvées: {len(invoices)}")
                return invoices
            else:
                print(f"Erreur lors de la récupération des factures: {response.text}")
                return []
        except Exception as e:
            print(f"Exception lors de la récupération des factures: {e}")
            return []

    def get_all_invoices(self, limit=1000):
    """Récupère toutes les factures (avec une limite)"""
    token = self.get_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    all_invoices = []
    current_page = 1
    page_size = 100  # Taille maximale de page supportée par l'API Sellsy
    
    print(f"Récupération de toutes les factures (limite: {limit})...")
    
    while len(all_invoices) < limit:
        params = {
            "page": current_page,
            "limit": page_size
        }
        
        url = f"{self.api_url}/invoices"
        
        print(f"Récupération de la page {current_page}: {url}")
        
        try:
            response = requests.get(url, headers=headers, params=params)
            print(f"Statut de la réponse: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                page_invoices = response_data.get("data", [])
                
                if not page_invoices:
                    print("Aucune facture sur cette page, fin de la pagination")
                    break
                    
                all_invoices.extend(page_invoices)
                print(f"Page {current_page}: {len(page_invoices)} factures récupérées. Total: {len(all_invoices)}")
                
                # Continuer à la page suivante si nous avons reçu le nombre maximum de résultats par page
                # Ne pas se fier aux métadonnées de pagination qui semblent incorrectes
                if len(page_invoices) < page_size:
                    print("Moins de résultats que la taille de page, fin de la pagination")
                    break
                
                current_page += 1
                
                # Pause pour éviter de surcharger l'API
                print("Pause de 1 seconde pour éviter les limitations d'API...")
                time.sleep(1)
                    
            elif response.status_code == 401:
                print("Token expiré, renouvellement...")
                # Forcer le renouvellement du token
                self.token_expires_at = 0
                token = self.get_access_token()
                headers["Authorization"] = f"Bearer {token}"
                # Ne pas incrémenter la page pour réessayer
            else:
                print(f"Erreur lors de la récupération des factures (page {current_page}): {response.text}")
                break
        except Exception as e:
            print(f"Exception lors de la récupération de la page {current_page}: {e}")
            break
    
    # Limiter le nombre de factures retournées à la limite spécifiée
    result = all_invoices[:limit]
    print(f"Total des factures récupérées: {len(result)} (sur {len(all_invoices)} disponibles)")
    return result
                        

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
            print(f"Statut: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                # Vérifier si les données sont directement dans la réponse ou dans un champ "data"
                if "data" in data:
                    print(f"Détails de la facture {invoice_id} récupérés avec succès (format avec data)")
                    return data.get("data", {})
                else:
                    # Les données sont directement dans la réponse
                    print(f"Détails de la facture {invoice_id} récupérés avec succès (format direct)")
                    return data
            else:
                print(f"Erreur lors de la récupération des détails de la facture {invoice_id}: {response.text}")
                # Si la facture n'existe pas ou si on n'a pas accès, on renvoie None
                return None
        except Exception as e:
            print(f"Exception lors de la récupération des détails de la facture {invoice_id}: {e}")
            return None
    
    def download_invoice_pdf(self, invoice_id):
        """Télécharge le PDF d'une facture et retourne le chemin du fichier"""
        if not invoice_id:
            print("❌ ID de facture invalide pour le téléchargement du PDF")
            return None
        
        # Conversion explicite en string
        invoice_id = str(invoice_id)
        
        # Définir le chemin du fichier PDF
        pdf_filename = f"facture_{invoice_id}.pdf"
        pdf_path = os.path.join(PDF_STORAGE_DIR, pdf_filename)
        
        # Vérifier si le fichier existe déjà
        if os.path.exists(pdf_path):
            print(f"PDF déjà existant pour la facture {invoice_id}: {pdf_path}")
            return pdf_path
        
        # Si non, d'abord récupérer les détails de la facture pour obtenir le lien PDF direct
        invoice_details = self.get_invoice_details(invoice_id)
        if not invoice_details:
            print(f"❌ Impossible de récupérer les détails pour télécharger le PDF")
            return None
        
        # Vérifier si le lien PDF est disponible directement dans les détails de la facture
        pdf_link = invoice_details.get("pdf_link")
        if not pdf_link:
            print(f"❌ Lien PDF non trouvé dans les détails de la facture {invoice_id}")
            return None
        
        print(f"Lien PDF trouvé: {pdf_link}")
        
        # Si le lien est disponible, télécharger directement depuis ce lien
        token = self.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/pdf"
        }
        
        try:
            response = requests.get(pdf_link, headers=headers)
            print(f"Statut du téléchargement (lien direct): {response.status_code}")
            
            if response.status_code == 200:
                # Vérifier que c'est bien un PDF
                content_type = response.headers.get('Content-Type', '')
                if 'pdf' not in content_type.lower() and len(response.content) < 1000:
                    print(f"⚠️ Contenu non PDF reçu: {content_type}")
                    print(f"Aperçu du contenu: {response.content[:100]}")
                    return None
                
                # Sauvegarder le PDF
                with open(pdf_path, 'wb') as f:
                    f.write(response.content)
                
                print(f"✅ PDF de la facture {invoice_id} téléchargé avec succès: {pdf_path}")
                return pdf_path
            else:
                # Fallback: essayer l'URL standard de l'API
                url = f"{self.api_url}/invoices/{invoice_id}/document"
                print(f"Échec du téléchargement direct, tentative avec l'API standard: {url}")
                
                response = requests.get(url, headers=headers)
                print(f"Statut du téléchargement (API standard): {response.status_code}")
                
                if response.status_code == 200:
                    # Sauvegarder le PDF
                    with open(pdf_path, 'wb') as f:
                        f.write(response.content)
                    
                    print(f"✅ PDF de la facture {invoice_id} téléchargé avec succès (méthode alternative)")
                    return pdf_path
                else:
                    print(f"❌ Impossible de télécharger le PDF avec les deux méthodes")
                    # Créer un fichier vide pour éviter de réessayer à chaque fois
                    with open(pdf_path, 'w') as f:
                        f.write("")
                    print(f"Fichier vide créé pour éviter des tentatives répétées: {pdf_path}")
                    return pdf_path
        except Exception as e:
            print(f"❌ Exception lors du téléchargement du PDF: {e}")
            return None

        # Vérifier que les identifiants sont bien définis (sans les afficher)
        if not SELLSY_CLIENT_ID or not SELLSY_CLIENT_SECRET:
            print("ERREUR: Identifiants Sellsy manquants dans les variables d'environnement")
        
        # Créer le répertoire de stockage des PDF s'il n'existe pas
        if not os.path.exists(PDF_STORAGE_DIR):
            os.makedirs(PDF_STORAGE_DIR)
            print(f"Répertoire de stockage des PDF créé: {PDF_STORAGE_DIR}")

    def get_access_token(self):
        """Obtient ou renouvelle le token d'accès Sellsy selon la documentation v2"""
        current_time = time.time()
        
        # Vérifier si le token est encore valide
        if self.access_token and current_time < self.token_expires_at - 60:
            return self.access_token
        
        # Si non, demander un nouveau token
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
        
        print(f"Tentative d'authentification à l'API Sellsy: {url}")
        
        try:
            response = requests.post(url, headers=headers, data=data)
            print(f"Statut de la réponse: {response.status_code}")
            print(f"En-têtes de la réponse: {response.headers.get('Content-Type')}")
            
            if response.status_code == 200:
                try:
                    token_data = response.json()
                    self.access_token = token_data["access_token"]
                    self.token_expires_at = current_time + token_data["expires_in"]
                    print("Token d'accès obtenu avec succès")
                    return self.access_token
                except json.JSONDecodeError as e:
                    print(f"Erreur de décodage JSON: {e}")
                    print(f"Contenu de la réponse (100 premiers caractères): {response.text[:100]}")
                    raise Exception("Réponse de l'API Sellsy invalide")
            else:
                print(f"Erreur d'authentification Sellsy: Code {response.status_code}")
                print(f"Réponse complète: {response.text}")
                raise Exception(f"Échec de l'authentification Sellsy (code {response.status_code})")
        except requests.exceptions.RequestException as e:
            print(f"Erreur de connexion à l'API Sellsy: {e}")
            raise Exception(f"Impossible de se connecter à l'API Sellsy: {e}")

    def get_invoices(self, days=30):
        """Récupère les factures des derniers jours spécifiés"""
        token = self.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Calculer la date de début (il y a X jours)
        start_date = time.strftime("%Y-%m-%d", time.localtime(time.time() - days * 86400))
        
        # Paramètres de recherche pour les factures - adaptés à l'API v2
        params = {
            "page": 1,
            "limit": 100,
            "created_after": f"{start_date}T00:00:00Z"
        }
        
        url = f"{self.api_url}/invoices"
        print(f"Recherche des factures depuis {start_date}: {url}")
        
        try:
            response = requests.get(url, headers=headers, params=params)
            print(f"Statut de la réponse: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                invoices = data.get("data", [])
                print(f"Nombre de factures trouvées: {len(invoices)}")
                return invoices
            else:
                print(f"Erreur lors de la récupération des factures: {response.text}")
                return []
        except Exception as e:
            print(f"Exception lors de la récupération des factures: {e}")
            return []

    def get_all_invoices(self, limit=1000):
        """Récupère toutes les factures (avec une limite)"""
        token = self.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        all_invoices = []
        current_page = 1
        page_size = 100  # Taille maximale de page supportée par l'API Sellsy
        
        print(f"Récupération de toutes les factures (limite: {limit})...")
        
        while len(all_invoices) < limit:
            params = {
                "page": current_page,
                "limit": page_size
            }
            
            url = f"{self.api_url}/invoices"
            
            print(f"Récupération de la page {current_page}: {url}")
            
            try:
                response = requests.get(url, headers=headers, params=params)
                print(f"Statut de la réponse: {response.status_code}")
                
                if response.status_code == 200:
                    response_data = response.json()
                    page_invoices = response_data.get("data", [])
                    
                    if not page_invoices:
                        print("Aucune facture sur cette page, fin de la pagination")
                        break
                        
                    all_invoices.extend(page_invoices)
                    print(f"Page {current_page}: {len(page_invoices)} factures récupérées. Total: {len(all_invoices)}")
                    
                    # Vérifier s'il y a d'autres pages
                    meta = response_data.get("meta", {})
                    pagination = meta.get("pagination", {})
                    current_page_from_api = pagination.get("current", 1)
                    total_pages = pagination.get("nbPages", 1)
                    
                    print(f"Pagination: Page {current_page_from_api}/{total_pages}")
                    
                    # Si nous sommes à la dernière page ou si nous avons moins de résultats que la taille de page
                    if current_page_from_api >= total_pages or len(page_invoices) < page_size:
                        print("Dernière page atteinte")
                        break
                    
                    current_page += 1
                    
                    # Pause pour éviter de surcharger l'API
                    if current_page > 1:
                        print("Pause de 1 seconde pour éviter les limitations d'API...")
                        time.sleep(1)
                        
                elif response.status_code == 401:
                    print("Token expiré, renouvellement...")
                    # Forcer le renouvellement du token
                    self.token_expires_at = 0
                    token = self.get_access_token()
                    headers["Authorization"] = f"Bearer {token}"
                    # Ne pas incrémenter la page pour réessayer
                else:
                    print(f"Erreur lors de la récupération des factures (page {current_page}): {response.text}")
                    break
            except Exception as e:
                print(f"Exception lors de la récupération de la page {current_page}: {e}")
                break
        
        # Limiter le nombre de factures retournées à la limite spécifiée
        result = all_invoices[:limit]
        print(f"Total des factures récupérées: {len(result)} (sur {len(all_invoices)} disponibles)")
        return result

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
            print(f"Statut: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                # Vérifier si les données sont directement dans la réponse ou dans un champ "data"
                if "data" in data:
                    print(f"Détails de la facture {invoice_id} récupérés avec succès (format avec data)")
                    return data.get("data", {})
                else:
                    # Les données sont directement dans la réponse
                    print(f"Détails de la facture {invoice_id} récupérés avec succès (format direct)")
                    return data
            else:
                print(f"Erreur lors de la récupération des détails de la facture {invoice_id}: {response.text}")
                # Si la facture n'existe pas ou si on n'a pas accès, on renvoie None
                return None
        except Exception as e:
            print(f"Exception lors de la récupération des détails de la facture {invoice_id}: {e}")
            return None
    
    def download_invoice_pdf(self, invoice_id):
        """Télécharge le PDF d'une facture et retourne le chemin du fichier"""
        if not invoice_id:
            print("❌ ID de facture invalide pour le téléchargement du PDF")
            return None
        
        # Conversion explicite en string
        invoice_id = str(invoice_id)
        
        # Définir le chemin du fichier PDF
        pdf_filename = f"facture_{invoice_id}.pdf"
        pdf_path = os.path.join(PDF_STORAGE_DIR, pdf_filename)
        
        # Vérifier si le fichier existe déjà
        if os.path.exists(pdf_path):
            print(f"PDF déjà existant pour la facture {invoice_id}: {pdf_path}")
            return pdf_path
        
        # Si non, d'abord récupérer les détails de la facture pour obtenir le lien PDF direct
        invoice_details = self.get_invoice_details(invoice_id)
        if not invoice_details:
            print(f"❌ Impossible de récupérer les détails pour télécharger le PDF")
            return None
        
        # Vérifier si le lien PDF est disponible directement dans les détails de la facture
        pdf_link = invoice_details.get("pdf_link")
        if not pdf_link:
            print(f"❌ Lien PDF non trouvé dans les détails de la facture {invoice_id}")
            return None
        
        print(f"Lien PDF trouvé: {pdf_link}")
        
        # Si le lien est disponible, télécharger directement depuis ce lien
        token = self.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/pdf"
        }
        
        try:
            response = requests.get(pdf_link, headers=headers)
            print(f"Statut du téléchargement (lien direct): {response.status_code}")
            
            if response.status_code == 200:
                # Vérifier que c'est bien un PDF
                content_type = response.headers.get('Content-Type', '')
                if 'pdf' not in content_type.lower() and len(response.content) < 1000:
                    print(f"⚠️ Contenu non PDF reçu: {content_type}")
                    print(f"Aperçu du contenu: {response.content[:100]}")
                    return None
                
                # Sauvegarder le PDF
                with open(pdf_path, 'wb') as f:
                    f.write(response.content)
                
                print(f"✅ PDF de la facture {invoice_id} téléchargé avec succès: {pdf_path}")
                return pdf_path
            else:
                # Fallback: essayer l'URL standard de l'API
                url = f"{self.api_url}/invoices/{invoice_id}/document"
                print(f"Échec du téléchargement direct, tentative avec l'API standard: {url}")
                
                response = requests.get(url, headers=headers)
                print(f"Statut du téléchargement (API standard): {response.status_code}")
                
                if response.status_code == 200:
                    # Sauvegarder le PDF
                    with open(pdf_path, 'wb') as f:
                        f.write(response.content)
                    
                    print(f"✅ PDF de la facture {invoice_id} téléchargé avec succès (méthode alternative)")
                    return pdf_path
                else:
                    print(f"❌ Impossible de télécharger le PDF avec les deux méthodes")
                    # Créer un fichier vide pour éviter de réessayer à chaque fois
                    with open(pdf_path, 'w') as f:
                        f.write("")
                    print(f"Fichier vide créé pour éviter des tentatives répétées: {pdf_path}")
                    return pdf_path
        except Exception as e:
            print(f"❌ Exception lors du téléchargement du PDF: {e}")
            return None
