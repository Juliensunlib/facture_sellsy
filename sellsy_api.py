import requests
import json
import time
from config import SELLSY_CLIENT_ID, SELLSY_CLIENT_SECRET, SELLSY_API_URL

class SellsyAPI:
    def __init__(self):
        self.access_token = None
        self.token_expires_at = 0
        self.api_url = SELLSY_API_URL

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
        
        response = requests.post(url, headers=headers, data=data)
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data["access_token"]
            self.token_expires_at = current_time + token_data["expires_in"]
            return self.access_token
        else:
            print(f"Erreur d'authentification Sellsy: {response.text}")
            raise Exception("Échec de l'authentification Sellsy")

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
        response = requests.post(url, headers=headers, json=search_params)
        
        if response.status_code == 200:
            return response.json()["data"]
        else:
            print(f"Erreur lors de la récupération des factures: {response.text}")
            return []

    def get_invoice_details(self, invoice_id):
        """Récupère les détails d'une facture spécifique"""
        token = self.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.api_url}/v1/invoices/{invoice_id}"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()["data"]
        else:
            print(f"Erreur lors de la récupération des détails de la facture: {response.text}")
            return None