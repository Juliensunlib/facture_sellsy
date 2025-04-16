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
        url = f"{self.api_url}/oauth2/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_id": SELLSY_CLIENT_ID,
            "client_secret": SELLSY_CLIENT_SECRET
        }
        
        print(f"Tentative d'authentification à l'API Sellsy: {url}")
        try:
            response = requests.post(url, headers=headers, data=data)
            print(f"Statut de la réponse: {response.status_code}")
            
            # Afficher les 100 premiers caractères de la réponse (pour le debugging)
            response_preview = response.text[:100] + "..." if len(response.text) > 100 else response.text
            print(f"Aperçu de la réponse: {response_preview}")
            
            if response.status_code == 200:
                try:
                    token_data = response.json()
                    self.access_token = token_data["access_token"]
                    self.token_expires_at = current_time + token_data["expires_in"]
                    print("Token d'accès obtenu avec succès")
                    return self.access_token
                except json.JSONDecodeError as e:
                    print(f"Erreur de décodage JSON: {e}")
                    print(f"Contenu de la réponse: {response.text}")
                    raise Exception("Réponse de l'API Sellsy invalide")
            else:
                print(f"Erreur d'authentification Sellsy: Code {response.status_code}")
                print(f"Réponse: {response.text}")
                raise Exception(f"Échec de l'authentification Sellsy (code {response.status_code})")
        except requests.exceptions.RequestException as e:
            print(f"Erreur de connexion à l'API Sellsy: {e}")
            raise Exception(f"Impossible de se connecter à l'API Sellsy: {e}")

    def get_invoices(self, days=30):
        """Récupère les factures des derniers jours spécifiés"""
        token = self.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Calculer la date de début (il y a X jours)
        start_date = time.strftime("%Y-%m-%d", time.localtime(time.time() - days * 86400))
        
        # Paramètres de recherche pour les factures
        search_params = {
            "pagination": {
                "pageSize": 100,
                "page": 1
            },
            "filters": {
                "createdAfter": f"{start_date}T00:00:00Z"
            }
        }
        
        url = f"{self.api_url}/v1/invoices"
        print(f"Recherche des factures depuis {start_date}: {url}")
        
        try:
            response = requests.post(url, headers=headers, json=search_params)
            print(f"Statut de la réponse: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Nombre de factures trouvées: {len(data.get('data', []))}")
                return data["data"]
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
            "Content-Type": "application/json"
        }
        
        # Paramètres de recherche pour les factures
        search_params = {
            "pagination": {
                "pageSize": 100,
                "page": 1
            }
        }
        
        all_invoices = []
        current_page = 1
        total_pages = 1
        
        print(f"Récupération de toutes les factures (limite: {limit})...")
        
        while current_page <= total_pages and len(all_invoices) < limit:
            search_params["pagination"]["page"] = current_page
            url = f"{self.api_url}/v1/invoices"
            
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
                        total_pages = pagination.get("nbPages", 0)
                        print(f"Total des pages: {total_pages}")
                    except json.JSONDecodeError as e:
                        print(f"Erreur de décodage JSON: {e}")
                        print(f"Aperçu de la réponse: {response.text[:200]}...")
                        break
                else:
                    print(f"Erreur lors de la récupération des factures (page {current_page}): {response.text}")
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
            "Content-Type": "application/json"
        }
        
        url = f"{self.api_url}/v1/invoices/{invoice_id}"
        
        try:
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                return response.json()["data"]
            else:
                print(f"Erreur lors de la récupération des détails de la facture {invoice_id}: {response.text}")
                return None
        except Exception as e:
            print(f"Exception lors de la récupération des détails de la facture {invoice_id}: {e}")
            return None
