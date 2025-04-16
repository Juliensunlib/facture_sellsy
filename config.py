import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration Sellsy
SELLSY_CLIENT_ID = os.getenv("SELLSY_CLIENT_ID")
SELLSY_CLIENT_SECRET = os.getenv("SELLSY_CLIENT_SECRET")
SELLSY_API_URL = "https://api.sellsy.fr"

# Configuration Airtable
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME")

# Configuration du webhook
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "votre_secret_webhook")