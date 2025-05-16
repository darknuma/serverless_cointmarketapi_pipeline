import datetime
import logging
import os
import requests
import json
import sys
from dotenv import load_dotenv

load_dotenv()

# Configure basic logging for standalone testing
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Import the necessary Azure packages
try:
    from azure.keyvault.secrets import SecretClient
    from azure.identity import DefaultAzureCredential, ClientSecretCredential
    from azure.storage.blob import BlobServiceClient
except ImportError:
    logging.error("Azure SDK packages not installed. Run: pip install azure-keyvault-secrets azure-identity azure-storage-blob")
    sys.exit(1)

# Mock TimerRequest for standalone testing
class MockTimerRequest:
    def __init__(self, past_due=False):
        self.past_due = past_due

def test_coin_api_ingestion():
    """Test function to verify CoinGecko API connectivity and data pipeline"""
    logging.info("Starting test of CoinGecko API ingestion")
    
    # --- Check if environment variables are set ---
    required_vars = ["KEY_VAULT_URL", "COINGECKO_API_KEY_SECRET_NAME", "STORAGE_ACCOUNT_URL"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        logging.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logging.info("Please set these environment variables before running the test:")
        for var in missing_vars:
            logging.info(f"  - {var}")
        return False
    
    # --- Try to connect to Key Vault ---
    key_vault_url = os.environ.get("KEY_VAULT_URL")
    coingecko_api_key_secret_name = os.environ.get("COINGECKO_API_KEY_SECRET_NAME")
    
    logging.info(f"Attempting to connect to Key Vault: {key_vault_url}")
    try:
        # Try DefaultAzureCredential first (works in Azure and with developer credentials)
        credential = DefaultAzureCredential()
        kv_client = SecretClient(vault_url=key_vault_url, credential=credential)
        api_key = kv_client.get_secret(coingecko_api_key_secret_name).value
        print(f"API KEY VALUE IS {api_key}")
        logging.info("✅ Successfully retrieved API key from Key Vault")
    except Exception as e:
        logging.error(f"❌ Error retrieving secret from Key Vault: {e}")
        logging.info("Make sure your Azure credentials are properly configured")
        return False
    
    # --- Test CoinGecko API ---
    base_url = "https://api.coingecko.com/api/v3"
    # url = "/api.coingecko.com

    headers = {"accept": "application/json",
               "x-cg-demo-api-key": api_key 
            }

    # First, test API status (doesn't require authentication)
    try:
        ping_response = requests.get(f"{base_url}/ping", headers=headers)
        # response = requests.get(url, headers=headers)
        print(ping_response.text)
        logging.info(f"✅ CoinGecko API is online. Status: {ping_response.text}")
    except Exception as e:
        # logging.error(f"❌ CoinGecko API ping failed: {e}")
        logging.info("The CoinGecko API may be down or unreachable")
        return False
    
    # Now test authenticated endpoint
    endpoint = "/coins/markets"
    parameters = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': '5',  # Reduced for testing
        'page': '1',
        'sparkline': 'false',
        'x-cg-demo-api-key': api_key
    }
    
    url = f"{base_url}{endpoint}"
    
    try:
        logging.info(f"Testing authenticated CoinGecko endpoint: {endpoint}")
        response = requests.get(url, headers=headers, params=parameters)
        response.raise_for_status()
        data = response.json()
        coin_count = len(data)
        if coin_count > 0:
            coin_names = ", ".join([coin["name"] for coin in data[:3]])
            logging.info(f"✅ Successfully fetched data for {coin_count} coins including: {coin_names}...")
        else:
            logging.warning("⚠️ API returned 0 coins. Check response format and parameters")
        
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Error calling CoinGecko API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logging.error(f"Response status: {e.response.status_code}")
            logging.error(f"Response text: {e.response.text}")
        return False
    
    # --- Test Storage Account connection ---
    storage_account_url = os.environ.get("STORAGE_ACCOUNT_URL")
    container_name = os.environ.get("RAW_DATA_CONTAINER_NAME", "raw-data")
    
    try:
        logging.info(f"Testing connection to Storage Account: {storage_account_url}")
        blob_service_client = BlobServiceClient(account_url=storage_account_url, credential=credential)

        # List containers
        containers = list(blob_service_client.list_containers())[:5]
        container_names = [container.name for container in containers]

        if container_name in container_names:
            logging.info(f"✅ Successfully connected to Storage Account and found container '{container_name}'")
        else:
            logging.warning(f"⚠️ Connected to Storage Account but container '{container_name}' was not found")
            logging.info(f"Available containers: {', '.join(container_names)}")

    except Exception as e:
        logging.error(f"❌ Error connecting to Storage Account: {e}")
        return False
    
    logging.info("✅ All connection tests passed! The code should work when deployed to Azure Functions.")
    return True

if __name__ == "__main__":
    test_coin_api_ingestion()