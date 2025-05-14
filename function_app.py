import azure.functions as func
import logging

from coin_api_ingeston import main as coin_gecko_timer_main 

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

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
# Schedule: Runs every 5 minutes. Adjust the CRON expression as needed.
# "0 */5 * * * *" -> At minute 0 past every 5th hour.
# For every 5 minutes: "0 */5 * * * *" is not quite right.
# Use "*/5 * * * *" for every 5 minutes (Common CRON interpretation)
# Or "0 */5 * * * *" specifically for Azure Functions (minute 0 of every 5 minute interval)
# Let's use a common "every 5 minutes" example: "0 */5 * * * *" (meaning at minute 0, 5, 10, 15 etc.)
# Or for exactly on the 5th minute of every hour: "0 5 * * * *"
# For "every hour at minute 0": "0 0 * * * *"

@app.timer_trigger(schedule="0 */30 * * * *", # Example: Runs every 30 minutes
                   arg_name="mytimer",        # This must match the argument name in your timer function
                   run_on_startup=True)      # Set to True if you want it to run when the Function App starts (useful for testing)
def coingecko_scheduled_ingestion(mytimer: func.TimerRequest) -> None:
    logging.info('Python timer trigger function (coingecko_scheduled_ingestion) is starting.')
    coin_gecko_timer_main(mytimer) # Call the imported main function
    logging.info('Python timer trigger function (coingecko_scheduled_ingestion) has finished.')