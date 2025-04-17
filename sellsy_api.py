import requests
import json
import time
import base64
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
                print(f"Nombre de factures trouvées: {len(data.get('data', []))}")
                return data.get("data", [])
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
        has_more = True
        page_size = 100 if limit > 100 else limit
        
        print(f"Récupération de toutes les factures (limite: {limit})...")
        
        while has_more and len(all_invoices) < limit:
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
                    try:
                        response_data = response.json()
                        page_invoices = response_data.get("data", [])
                        all_invoices.extend(page_invoices)
                        print(f"Page {current_page}: {len(page_invoices)} factures récupérées")
                        
                        # Vérifier s'il y a d'autres pages
                        meta = response_data.get("meta", {})
                        pagination_info = meta.get("pagination", {})
                        total_pages = pagination_info.get("nbPages", 1)  # Défaut à 1 page si non spécifié
                        total_items = pagination_info.get("nbResults", len(page_invoices))  # Utiliser le nombre d'éléments récupérés
                        
                        print(f"Total: {total_items} factures, {total_pages} pages")
                        
                        current_page += 1
                        # Si on a récupéré moins d'éléments que la page_size, c'est qu'il n'y a plus de données
                        has_more = len(page_invoices) == page_size and current_page <= total_pages
                        print(f"Plus de pages disponibles: {has_more}")
                    except json.JSONDecodeError as e:
                        print(f"Erreur de décodage JSON: {e}")
                        print(f"Aperçu de la réponse: {response.text[:200]}...")
                        break
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
        print(f"Récupération des détails de la facture {invoice_id}: {url}")
        
        try:
            response = requests.get(url, headers=headers)
            print(f"Statut: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if "data" in data:
                    print(f"Détails de la facture {invoice_id} récupérés avec succès")
                    return data.get("data", {})
                else:
                    print(f"Données manquantes dans la réponse pour la facture {invoice_id}")
                    print(f"Aperçu de la réponse: {str(data)[:200]}...")
                    return None
            else:
                print(f"Erreur lors de la récupération des détails de la facture {invoice_id}: {response.text}")
                # Si la facture n'existe pas ou si on n'a pas accès, on renvoie None
                return None
        except Exception as e:
            print(f"Exception lors de la récupération des détails de la facture {invoice_id}: {e}")
            return None
