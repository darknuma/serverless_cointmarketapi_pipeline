import datetime
import logging
import os
import requests
import json

import azure.functions as func
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential # Uses Managed Identity for Azure resources
from azure.storage.blob import BlobServiceClient

def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    if mytimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function for CoinGecko started execution at %s', utc_timestamp)

    # --- Configuration (from Function App Application Settings) ---
    key_vault_url = os.environ.get("KEY_VAULT_URL") # e.g., https://Coingecko.vault.azure.net/
    coingecko_api_key_secret_name = os.environ.get("COINGECKO_API_KEY_SECRET_NAME") # The name of the secret in your "Coingecko" Key Vault
    storage_account_url = os.environ.get("STORAGE_ACCOUNT_URL") # e.g., https://yourstorageaccount.blob.core.windows.net
    container_name = os.environ.get("RAW_DATA_CONTAINER_NAME", "raw-data") # Your ADLS raw container

    # --- Validate Configuration ---
    if not all([key_vault_url, coingecko_api_key_secret_name, storage_account_url]):
        logging.error("Missing one or more required environment variables: KEY_VAULT_URL, COINGECKO_API_KEY_SECRET_NAME, STORAGE_ACCOUNT_URL")
        return

    # --- Get API Key from Key Vault ---
    api_key = None
    credential = None # Define credential here to use it for both Key Vault and Storage
    try:
        credential = DefaultAzureCredential() # Assumes Managed Identity is enabled for the Function App
        kv_client = SecretClient(vault_url=key_vault_url, credential=credential)
        api_key = kv_client.get_secret(coingecko_api_key_secret_name).value
        logging.info('Successfully retrieved API key from Key Vault.')
    except Exception as e:
        logging.error(f"Error retrieving secret from Key Vault: {e}")
        return # Exit if key cannot be retrieved

    # --- Call CoinGecko API ---
    # Example: Get market data for top N coins
    # Refer to CoinGecko API documentation for more endpoints: https://www.coingecko.com/en/api/documentation
    # The Pro API base URL is typically: https://pro-api.coingecko.com/api/v3/
    # Example endpoint: /coins/markets
    
    # Construct the URL with the API key as a query parameter
    # IMPORTANT: Check CoinGecko Pro API documentation for exact parameter naming for API key.
    # It's often 'x_cg_pro_api_key' for Pro.
    base_url = "https://pro-api.coingecko.com/api/v3"
    endpoint = "/coins/markets"
    
    parameters = {
        'vs_currency': 'usd',  # Target currency
        'order': 'market_cap_desc', # Sort by market cap
        'per_page': '100',      # Number of results per page (adjust as needed, check API limits)
        'page': '1',            # Page number
        'sparkline': 'false',
        'x_cg_pro_api_key': api_key # API key as a query parameter
    }
    
    url = f"{base_url}{endpoint}"

    try:
        # CoinGecko API key is usually passed as a query parameter, not a header.
        # Some APIs might accept it in headers, but query parameter is common for CoinGecko.
        response = requests.get(url, params=parameters) # Pass API key via params
        response.raise_for_status() # Raises HTTPError for bad responses (4XX or 5XX)
        data = response.json()
        logging.info(f'Successfully fetched data from CoinGecko API endpoint: {endpoint}')

    except requests.exceptions.RequestException as e:
        logging.error(f"Error calling CoinGecko API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logging.error(f"Response status: {e.response.status_code}")
            logging.error(f"Response text: {e.response.text}")
        return
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON response from CoinGecko: {e}")
        logging.error(f"Response text: {response.text if 'response' in locals() else 'No response object'}")
        return

    # --- Store Raw Data in ADLS Gen2 ---
    try:
        # Ensure DefaultAzureCredential was obtained successfully earlier
        if not credential:
            logging.error("Cannot proceed to store data: Azure credential not available.")
            return

        blob_service_client = BlobServiceClient(account_url=storage_account_url, credential=credential)

        # Create a unique blob name with timestamp/structure reflecting CoinGecko
        now = datetime.datetime.utcnow()
        # Example: coingecko/markets/2023/05/15/143000_markets.json
        blob_name = f"coingecko/markets/{now.strftime('%Y/%m/%d/%H%M%S')}_markets.json"

        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

        # Upload data
        blob_client.upload_blob(json.dumps(data, indent=4), overwrite=True)
        logging.info(f"Successfully uploaded raw data to ADLS Gen2: {container_name}/{blob_name}")

    except Exception as e:
        logging.error(f"Error uploading data to ADLS Gen2: {e}")

    logging.info('Python timer trigger function for CoinGecko finished execution at %s', datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))