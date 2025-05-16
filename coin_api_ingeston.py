import datetime
import logging
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

import azure.functions as func 
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

app = func.FunctionApp()

@app.function_name(name="mytimer")
@app.timer_trigger(schedule="0 */30 * * * *", arg_name="mytimer", run_on_startup=False,
              use_monitor=False) 
def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S")

    if mytimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function for CoinGecko started execution at %s', utc_timestamp)

    # --- Configuration (from Function App Application Settings) ---
    key_vault_url = os.environ.get("KEY_VAULT_URL") # e.g., https://Coingecko.vault.azure.net/
    coingecko_api_key_secret_name = os.environ.get("COINGECKO_API_KEY_SECRET_NAME") # The name of the secret in your "Coingecko" Key Vault
    storage_account_url = os.environ.get("STORAGE_ACCOUNT_URL") # e.g., https://yourstorageaccount.blob.core.windows.net
    container_name = os.environ.get("RAW_DATA_CONTAINER_NAME", "raw-data") # Your ADLS raw container

    # Debug output to verify environment variables
    logging.info(f"Environment variables loaded: KEY_VAULT_URL={key_vault_url}, SECRET_NAME={coingecko_api_key_secret_name}, STORAGE_URL={storage_account_url}, CONTAINER={container_name}")

    # --- Validate Configuration ---
    if not all([key_vault_url, coingecko_api_key_secret_name, storage_account_url]):
        logging.error("Missing one or more required environment variables: KEY_VAULT_URL, COINGECKO_API_KEY_SECRET_NAME, STORAGE_ACCOUNT_URL")
        return

    # --- Get API Key from Key Vault ---
    api_key = None
    credential = None # Define credential here to use it for both Key Vault and Storage
    try:
        logging.info("Attempting to obtain DefaultAzureCredential...")
        credential = DefaultAzureCredential() 
        logging.info("Successfully obtained DefaultAzureCredential, connecting to Key Vault...")
        kv_client = SecretClient(vault_url=key_vault_url, credential=credential)
        logging.info(f"Connected to Key Vault, retrieving secret: {coingecko_api_key_secret_name}")
        api_key = kv_client.get_secret(coingecko_api_key_secret_name).value
        logging.info('Successfully retrieved API key from Key Vault.')
    except Exception as e:
        logging.error(f"Error retrieving secret from Key Vault: {str(e)}")
        # Print more detailed error info
        import traceback
        logging.error(f"Detailed error: {traceback.format_exc()}")
        return # Exit if key cannot be retrieved

    # --- Call CoinGecko API ---
    base_url = "https://api.coingecko.com/api/v3"
    endpoint = "/coins/markets"
    
    # First try a simple ping to see if API is responsive
    try:
        ping_url = f"{base_url}/ping"
        logging.info(f"Testing CoinGecko API availability with ping: {ping_url}")
        ping_response = requests.get(ping_url)
        ping_response.raise_for_status()
        logging.info(f"CoinGecko API ping successful: {ping_response.text}")
    except Exception as e:
        logging.error(f"CoinGecko API ping failed: {str(e)}")
    

    parameters = {
        'vs_currency': 'usd',  # Target currency
        'order': 'market_cap_desc', # Sort by market cap
        'per_page': '100',      # Number of results per page
        'page': '1',            # Page number
        'sparkline': 'false'
    }
    
    headers = {
        'x-cg-demo-api-key': api_key  # Try API key in header
    }
    
    url = f"{base_url}{endpoint}"
    
    logging.info(f"Calling CoinGecko API endpoint: {url}")
    
    try:
        # Try both methods: API key as query param and as header
        # Method 1: API key as query param (as in your original code)
        params_with_key = parameters.copy()
        params_with_key['x-cg-demo-api-key'] = api_key
        
        logging.info("Attempting CoinGecko API call with key as query parameter...")
        response = requests.get(url, params=params_with_key)
        
        # If that fails, try API key in header
        if response.status_code >= 400:
            logging.info(f"Query parameter approach failed with status {response.status_code}, trying header approach...")
            response = requests.get(url, params=parameters, headers=headers)
        
        response.raise_for_status()
        data = response.json()
        logging.info(f'Successfully fetched data from CoinGecko API endpoint: {endpoint}. Sample: {str(data[0]) if data and len(data) > 0 else "No data returned"}')

    except requests.exceptions.RequestException as e:
        logging.error(f"Error calling CoinGecko API: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            logging.error(f"Response status: {e.response.status_code}")
            logging.error(f"Response text: {e.response.text}")
        return
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON response from CoinGecko: {str(e)}")
        logging.error(f"Response text: {response.text if 'response' in locals() else 'No response object'}")
        return

    # --- Store Raw Data in ADLS Gen2 ---
    try:
        # Ensure DefaultAzureCredential was obtained successfully earlier
        if not credential:
            logging.error("Cannot proceed to store data: Azure credential not available.")
            return

        logging.info(f"Connecting to Storage Account: {storage_account_url}")
        blob_service_client = BlobServiceClient(account_url=storage_account_url, credential=credential)

        # Create a unique blob name with timestamp/structure reflecting CoinGecko
        now = datetime.datetime.now(datetime.UTC)
        blob_name = f"coingecko/markets/{now.strftime('%Y/%m/%d/%H%M%S')}_markets.json"

        logging.info(f"Preparing to upload to container '{container_name}', blob path: {blob_name}")
        
        # Check if container exists
        try:
            container_client = blob_service_client.get_container_client(container_name)
            container_exists = container_client.exists()
            if not container_exists:
                logging.warning(f"Container '{container_name}' does not exist, attempting to create it...")
                container_client.create_container()
                logging.info(f"Container '{container_name}' created successfully")
        except Exception as e:
            logging.error(f"Error checking/creating container: {str(e)}")
            # Continue to try upload anyway

        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

        # Upload data
        logging.info("Uploading data to blob storage...")
        blob_client.upload_blob(json.dumps(data, indent=4), overwrite=True)
        logging.info(f"Successfully uploaded raw data to ADLS Gen2: {container_name}/{blob_name}")

    except Exception as e:
        logging.error(f"Error uploading data to ADLS Gen2: {str(e)}")
        import traceback
        logging.error(f"Detailed error: {traceback.format_exc()}")

    logging.info('Python timer trigger function for CoinGecko finished execution at %s', datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S"))

if __name__ == "__main__":
    class DummyTimer:
        past_due = False
    main(DummyTimer())