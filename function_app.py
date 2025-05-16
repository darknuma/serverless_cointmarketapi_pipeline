import azure.functions as func
import logging

from coin_api_ingeston import main as coin_gecko_timer_main 

# Create Function App with CORS configuration
app = func.FunctionApp()

# @app.route(route="https://pro-api.coingecko.com/api/v3/coins/market", methods=["GET"])
# def http_trigger(req: func.HttpRequest) -> func.HttpResponse:
#     logging.info('Python HTTP trigger function processed a request.')
#     name = req.params.get('name')
#     if not name:
#         try:
#             req_body = req.get_json()
#         except ValueError:
#             pass
#         else:
#             name = req_body.get('name')
#     if name:
#         return func.HttpResponse(f"Hello, {name}. This HTTP triggered function executed successfully.")
#     else:
#         return func.HttpResponse(
#              "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
#              status_code=200
#         )

# ---- ADD THIS SECTION FOR YOUR TIMER TRIGGER ----
# Schedule: Runs every 30 minutes


@app.function_name(name="mytimer")
@app.timer_trigger(schedule="0 */30 * * * *", arg_name="myTimer", run_on_startup=False,
              use_monitor=False) 
def coingecko_scheduled_ingestion(myTimer: func.TimerRequest) -> None:
    logging.info('Python timer trigger function (coingecko_scheduled_ingestion) is starting.')
    coin_gecko_timer_main() # Call the imported main function
    logging.info('Python timer trigger function (coingecko_scheduled_ingestion) has finished.')

    
    if myTimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function executed.')