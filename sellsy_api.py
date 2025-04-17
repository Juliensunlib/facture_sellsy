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
