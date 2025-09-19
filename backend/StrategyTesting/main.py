from .Strategies import Strategy
import pandas as pd
from backend.AngleSmartAPI import AngleOne_Smart_API
import asyncio

log_sender = None

async def send_log(msg):
    if log_sender:
        await log_sender(msg)
    else:
        print(msg)

API_KEY = "vhAupRK9"
CLIENT_ID = "AAAJ289396"
PIN = "5689"
TOTP = "IV7PPFHDE4RAWYS7OOXQIBLKTI"

try:
    instance = AngleOne_Smart_API(api_key=API_KEY, username=CLIENT_ID, pwd=PIN, token=TOTP)
    instance.connect()
except Exception as e:
    print("Failed to initialize or connect API instance:", str(e))
    instance = None

start_date = "2020-07-01"
results = []

async def get_inputs(checkLoad):
    data = checkLoad  # first (and only) dict in the list
    strategy = data[0] if isinstance(data[0], list) else [data[0]]

    strategy_args = data[1]
    strategy_args = [int(x) for x in strategy_args] if all(str(x).isdigit() for x in strategy_args) else strategy_args
    stocks_list = str(data[2]).split()

    timeFrame = data[3] if isinstance(data[3], list) else data[3].split(",")
    startingDate = data[4]
    endingDate = data[5]
    
    return (strategy, stocks_list, strategy_args, timeFrame,startingDate,endingDate)

async def fetch_data_with_progress(symbol, interval, start, end):
    loop = asyncio.get_event_loop()
    is_done = False
    start_time = loop.time()

    async def send_progress():
        while not is_done:
            elapsed = loop.time() - start_time
            if elapsed < 5:
                msg = f"⏳ Fetching data for {symbol} ({interval})..."
            elif elapsed < 15:
                msg = f"⌛ Still fetching data for {symbol}, please have patience..."
            elif elapsed < 30:
                msg = f"🕐 Taking longer than usual to fetch data for {symbol}..."
            else:
                msg = f"⏳ Hang tight! Data is still coming for {symbol}..."

            await send_log(msg)
            await asyncio.sleep(3)

    progress_task = asyncio.create_task(send_progress())
    try:
        # Run the blocking function in a thread to not block event loop
        df = await loop.run_in_executor(None, lambda: instance.get_FullData("NSE", symbol, interval, start, end))
    finally:
        is_done = True
        await progress_task
    return df

async def process_inputs(checkLoad):
    global results
    results = []

    strategy, stocks_list, strategy_args, timeFrame,startingDate,endingDate = await get_inputs(checkLoad)

    if not all([strategy, stocks_list, strategy_args, timeFrame]):
        raise ValueError("One or more input variables are empty.")

    if not instance:
        raise RuntimeError("API instance not initialized")

    try:
        for symbol in stocks_list:
            for interval in timeFrame:
                try:
                    df = await fetch_data_with_progress(symbol, interval, startingDate, endingDate)
                    strat = Strategy(df)
                    
                    strategy_method = getattr(strat, strategy[0], None)
                    if strategy_method:
                        result = strategy_method(strategy_args)
                        results.append({symbol:{interval:result}})
                    else:
                        pass
                except Exception as e:
                    await send_log(f"❌ Failed to process {symbol} ({interval}): {str(e)}")
        return results
    except Exception as e:
        raise
# def process_inputs(checkLoad):
#     global results
#     results = []

#     strategy, stocks_list, period_length, timeFrame = get_inputs(checkLoad)

#     if not all([strategy, stocks_list, period_length, timeFrame]):
#         raise ValueError("One or more input variables are empty.")

#     if not instance:
#         raise RuntimeError("API instance not initialized")

#     params = list(map(int, period_length))  # convert period_length strings to ints

#     for symbol in stocks_list:
#         symbol_result = {}
#         for interval in timeFrame:
#             try:
#                 df = instance.get_FullData("NSE", symbol, interval, start_date)
#                 strat = Strategy(df)

#                 strategy_method = getattr(strat, strategy[0], None)
#                 if strategy_method:
#                     temp = strategy_method(params)
#                     symbol_result[interval] = temp
#                 else:
#                     print(f"Method {strategy[0]} not found in Strategy.")
#             except Exception as e:
#                 print(f"Failed for {symbol} - {interval}: {str(e)}")
#         # After all intervals for one symbol, append each interval as separate dict in results
#         for interval_key, interval_val in symbol_result.items():
#             results.append({interval_key: interval_val})

#     final_output = {
#         "message": "Backtest run successfully",
#         "output": results
#     }

#     print(final_output)  
#     return final_output

def showOutput():
    # if results:
    #     return results
    # else:
    #     return "results are empty"
    return "Hello i am from main.py"


# Export log_sender setter so it can be set externally
def set_log_sender(sender_func):
    global log_sender
    log_sender = sender_func