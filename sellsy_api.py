import requests
import json
import time
from config import SELLSY_CLIENT_ID, SELLSY_CLIENT_SECRET, SELLSY_API_URL

class SellsyAPI:
    def __init__(self):
        self.access_token = None
        self.token_expires_at = 0
        self.api_url = SELLSY_API_URL
        print(f"API URL configurée: {self.api_url}")
        # Vérifier que les identifiants sont bien définis (sans les afficher)
        if not SELLSY_CLIENT_ID or not SELLSY_CLIENT_SECRET:
            print("ERREUR: Identifiants Sellsy manquants dans les variables d'environnement")

    def get_access_token(self):
        """Obtient ou renouvelle le token d'accès Sellsy"""
        current_time = time.time()
        
        # Vérifier si le token est encore valide
        if self.access_token and current_time < self.token_expires_at - 60:
            return self.access_token
        
        # Si non, demander un nouveau token
        url = "https://login.sellsy.com/oauth2/access-tokens"
        
        # Authentification en utilisant l'autorisation basique (Basic Auth)
        auth = (SELLSY_CLIENT_ID, SELLSY_CLIENT_SECRET)
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        
        # Corps de la requête avec seulement grant_type
        data = {
            "grant_type": "client_credentials"
        }
        
        print(f"Tentative d'authentification à l'API Sellsy: {url}")
        try:
            # Utiliser l'authentification Basic avec auth=(client_id, client_secret)
            response = requests.post(url, auth=auth, headers=headers, data=data)
            print(f"Statut de la réponse: {response.status_code}")
            
            # Afficher les en-têtes de la réponse pour le débogage
            print(f"En-têtes de la réponse: {response.headers.get('Content-Type')}")
            
            # Vérifier si la réponse est du JSON valide
            content_type = response.headers.get('Content-Type', '')
            is_json = 'application/json' in content_type
            
            if response.status_code == 200 and is_json:
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
                print(f"Réponse (100 premiers caractères): {response.text[:100]}")
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
        search_params = {
            "pagination": {
                "nbPerPage": 100,
                "pagenum": 1
            },
            "search": {
                "createdAfter": f"{start_date}T00:00:00Z"
            }
        }
        
        url = f"{self.api_url}/invoices/search"
        print(f"Recherche des factures depuis {start_date}: {url}")
        
        try:
            response = requests.post(url, headers=headers, json=search_params)
            print(f"Statut de la réponse: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Nombre de factures trouvées: {len(data.get('data', []))}")
                return data.get("data", [])
            else:
                print(f"Erreur lors de la récupération des factures: {response.text[:100]}")
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
        
        # Paramètres de recherche pour les factures - adaptés à l'API v2
        search_params = {
            "pagination": {
                "nbPerPage": 100,
                "pagenum": 1
            }
        }
        
        all_invoices = []
        current_page = 1
        has_more = True
        
        print(f"Récupération de toutes les factures (limite: {limit})...")
        
        while has_more and len(all_invoices) < limit:
            search_params["pagination"]["pagenum"] = current_page
            url = f"{self.api_url}/invoices/search"
            
            print(f"Récupération de la page {current_page}: {url}")
            
            try:
                response = requests.post(url, headers=headers, json=search_params)
                print(f"Statut de la réponse: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        page_invoices = response_data.get("data", [])
                        all_invoices.extend(page_invoices)
                        print(f"Page {current_page}: {len(page_invoices)} factures récupérées")
                        
                        # Mettre à jour les informations de pagination
                        pagination = response_data.get("pagination", {})
                        current_page += 1
                        has_more = pagination.get("pagenum", 0) < pagination.get("nbPages", 0)
                        print(f"Plus de pages disponibles: {has_more}")
                    except json.JSONDecodeError as e:
                        print(f"Erreur de décodage JSON: {e}")
                        print(f"Aperçu de la réponse: {response.text[:200]}...")
                        break
                else:
                    print(f"Erreur lors de la récupération des factures (page {current_page}): {response.text[:200]}")
                    break
            except Exception as e:
                print(f"Exception lors de la récupération de la page {current_page}: {e}")
                break
        
        print(f"Total des factures récupérées: {len(all_invoices)}")
        return all_invoices[:limit]

    def get_invoice_details(self, invoice_id):
        """Récupère les détails d'une facture spécifique"""
        token = self.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        
        url = f"{self.api_url}/invoices/{invoice_id}"
        
        try:
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                return response.json().get("data", {})
            else:
                print(f"Erreur lors de la récupération des détails de la facture {invoice_id}: {response.text[:200]}")
                return None
        except Exception as e:
            print(f"Exception lors de la récupération des détails de la facture {invoice_id}: {e}")
            return None
