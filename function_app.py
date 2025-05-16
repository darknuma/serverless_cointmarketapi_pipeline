import azure.functions as func
import logging

from coin_api_ingeston import main as coin_gecko_timer_main 

# Create Function App with CORS configuration
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION, 
                       cors=func.CorsSettings(allowed_origins=["https://portal.azure.com"]))

@app.route(route="http_trigger")
def http_trigger(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')
    if name:
        return func.HttpResponse(f"Hello, {name}. This HTTP triggered function executed successfully.")
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )

# ---- ADD THIS SECTION FOR YOUR TIMER TRIGGER ----
# Schedule: Runs every 30 minutes
@app.timer_trigger(schedule="0 */30 * * * *", # Example: Runs every 30 minutes
                   arg_name="mytimer",        # This must match the argument name in your timer function
                   run_on_startup=True)      # Set to True if you want it to run when the Function App starts (useful for testing)
def coingecko_scheduled_ingestion(mytimer: func.TimerRequest) -> None:
    logging.info('Python timer trigger function (coingecko_scheduled_ingestion) is starting.')
    coin_gecko_timer_main(mytimer) # Call the imported main function
    logging.info('Python timer trigger function (coingecko_scheduled_ingestion) has finished.')
