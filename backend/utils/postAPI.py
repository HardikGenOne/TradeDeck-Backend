from fastapi.responses import JSONResponse
from pydantic import BaseModel
from backend.AngleSmartAPI import AngleOne_Smart_API
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.StrategyTesting.Strategies import Strategy
import backend.StrategyTesting.main
from fastapi import WebSocket

import time
import httpx
import datetime
from datetime import datetime,timedelta
import yfinance as yf
from fastapi import FastAPI

import pandas as pd
import os 
import requests
app = FastAPI()

current_stock = ""
interval = ""
start_date = ""
processed_data = {}

# # Allow requests from any frontend (you can restrict later)
# app.add_middleware(
#     CORSMiddleware,
#     # allow_origins=["*"],  # or ["http://127.0.0.1:5500"] for more security
#     allow_origins=["http://localhost:5173"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/")
def root():
    try:
        return {"message": "Hello from root"}
    except Exception as e:
        return {"error": str(e), "detail": "Unexpected error occurred in root"}

@app.get("/data")
def postData():
    global current_stock,interval,start_date
    try:
        if not current_stock or not interval or not start_date:
            return {"error": "No stock symbol set yet. or provide the required details correctly"}

        # use your API to fetch data
        api_key = "vhAupRK9"
        token  = "J4DWDXYMDAKVV6VFJW6RHMS3RI"
        pwd = "7990"
        username = "L52128673"

        instance = AngleOne_Smart_API(api_key, username, pwd, token)
        instance.connect()

        exchange = "NSE"
        # interval = "FIFTEEN_MINUTE"
        # start_date = "2024-01-01"

        data = instance.get_FullData(exchange, current_stock, interval, start_date)
        print("Data Full Downloaded !!")
        data['Date'] = pd.to_datetime(data['Date']).dt.strftime('%Y-%m-%d %H:%M')
        data = data.drop(columns=['Unnamed: 0'], errors='ignore')
        data.rename(columns={'Date':'date','Open': 'open', 'High': 'high',"Low":"low","Close":'close','volume':'volume'}, inplace=True)

        return {"symbol": current_stock, "dataFrame": data.to_dict(orient="records")}
    except Exception as e:
        return {"error": "Data fetch failed", "detail": str(e)}

class StockRequest(BaseModel):
    symbol: str
    interval: str
    start_date: str

@app.post("/stock_symbol")
async def get_stock_symbol(req: StockRequest):
    global current_stock,interval,start_date,processed_data
    try:
        current_stock = req.symbol
        interval = req.interval
        start_date = req.start_date
        return {"message": f"Received: {req.symbol}, interval: {interval}, start_date: {start_date}"}
    except Exception as e:
        return {"error": str(e), "detail": "Unexpected error occurred in stock_symbol"}

@app.get("/ping")
def ping():
    try:
        return {"status":"alive"}
    except Exception as e:
        return {"error": str(e), "detail": "Unexpected error occurred in ping"}

@app.get("/stock/{symbol}/info")
def get_ltp_info(symbol: str):
    try:
        symbol = symbol.upper() + ".NS"
        ticker = yf.Ticker(symbol)

        today = datetime.now().date()
        one_day_ago = today - timedelta(days=1)
        one_week_ago = today - timedelta(days=7)
        one_month_ago = today - timedelta(days=30)

        hist = ticker.history(start=one_month_ago, interval="1d")

        if hist.empty:
            return {"error": "No data found for symbol"}

        hist = hist.dropna(subset=["Close"])

        latest_price = hist["Close"].iloc[-1]
        close_day = hist["Close"].iloc[-2] if len(hist) >= 2 else latest_price
        close_week = hist.loc[hist.index >= str(one_week_ago), "Close"].iloc[0] if len(hist.loc[hist.index >= str(one_week_ago)]) > 0 else latest_price
        close_month = hist["Close"].iloc[0]

        def calc_change(current, previous):
            change = current - previous
            percent = (change / previous) * 100 if previous != 0 else 0
            return round(change, 2), round(percent, 2)

        day_change, day_percent = calc_change(latest_price, close_day)
        week_change, week_percent = calc_change(latest_price, close_week)
        month_change, month_percent = calc_change(latest_price, close_month)

        return {
            "symbol": symbol.replace(".NS", ""),
            "ltp": round(latest_price, 2),
            "day": {"change": day_change, "percent": day_percent},
            "week": {"change": week_change, "percent": week_percent},
            "month": {"change": month_change, "percent": month_percent}
        }

    except Exception as e:
        return {"error": str(e), "detail": "Unexpected error occurred in stock_info"}
        
    
    
@app.get("/major_indices")
async def get_majorIndices_price():
    try:
        symbols = {
            "NIFTY50": "^NSEI",
            "BANKNIFTY": "^NSEBANK",
            "SENSEX": "^BSESN"
        }

        results = []

        for name, yf_symbol in symbols.items():
            ticker = yf.Ticker(yf_symbol)

            today = datetime.now().date()
            one_day_ago = today - timedelta(days=1)
            one_week_ago = today - timedelta(days=7)
            one_month_ago = today - timedelta(days=30)

            hist = ticker.history(start=one_month_ago, interval="1d")

            if hist.empty:
                results.append({"symbol": name, "error": "No data found"})
                continue

            hist = hist.dropna(subset=["Close"])

            latest_price = hist["Close"].iloc[-1]
            close_day = hist["Close"].iloc[-2] if len(hist) >= 2 else latest_price
            close_week = hist.loc[hist.index >= str(one_week_ago), "Close"].iloc[0] if len(hist.loc[hist.index >= str(one_week_ago)]) > 0 else latest_price
            close_month = hist["Close"].iloc[0]

            def calc_change(current, previous):
                change = current - previous
                percent = (change / previous) * 100 if previous != 0 else 0
                return round(change, 2), round(percent, 2)

            day_change, day_percent = calc_change(latest_price, close_day)
            week_change, week_percent = calc_change(latest_price, close_week)
            month_change, month_percent = calc_change(latest_price, close_month)

            results.append({
                "ticker": name,
                "symbol": yf_symbol,
                "ltp": round(latest_price, 2),
                "day": {"change": day_change, "percent": day_percent},
                "week": {"change": week_change, "percent": week_percent},
                "month": {"change": month_change, "percent": month_percent}
            })

        return {"data": results}

    except Exception as e:
        return {"error": str(e), "detail": "Unexpected error occurred in major_indices"}
    
VALID_INDICES = [
    "NIFTY 50",
    "NIFTY BANK",
    "NIFTY IT",
    "NIFTY FMCG",
    "NIFTY MIDCAP 50",
    "NIFTY MIDCAP 100",
    "NIFTY NEXT 50",
    "NIFTY 100",
    "NIFTY 200",
    "NIFTY 500"
]

@app.get("/heatmap/{index}")
async def getHeatMap(index: str):
    try:
        index = index.replace('_',"%20")
        url = f"https://www.nseindia.com/api/equity-stockIndices?index={index}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "application/json",
            "Referer": "https://www.nseindia.com/",
            "Connection": "keep-alive"
        }

        max_retries = 15
        retry_delay = 3  # seconds

        session = requests.Session()
        session.headers.update(headers)

        # Hit base page to set cookies properly
        session.get("https://www.nseindia.com", timeout=5)
        time.sleep(1.5)

        retries = 0
        while retries < max_retries:
            response = session.get(url, timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                retries += 1
                time.sleep(retry_delay)

        return {"error": "Failed after retries", "status_code": response.status_code, "text": response.text}

    except Exception as e:
        return {"error": str(e), "detail": "Unexpected error occurred in heatmap"}

@app.get("/strategies/functions")
async def getStrategiesFunction():
    import inspect

    functions_info = []
    for name in dir(Strategy):
        if callable(getattr(Strategy, name)) and not name.startswith("__"):
            func = getattr(Strategy, name)
            sig = inspect.signature(func)
            # Exclude 'self' and count only positional or keyword arguments
            params = [p for p in sig.parameters.values() if p.name != 'self']
            functions_info.append({
                "name": name,
                "num_args": len(params),
                "args": [p.name for p in params]
            })

    return functions_info

stored_inputs = []

# --- WebSocket connection handler ---
websocket_clients = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    websocket_clients.append(websocket)

    # Set log sender in main.py
    import backend.StrategyTesting.main as main_module
    async def send_log_to_client(msg):
        try:
            await websocket.send_text(msg)
        except:
            pass  # Handle failed sends if needed
    main_module.set_log_sender(send_log_to_client)

    try:
        while True:
            await websocket.receive_text()  # Keep alive
    except:
        websocket_clients.remove(websocket)
        main_module.set_log_sender(None)

class BacktestInput(BaseModel):
    strategy: str
    strategy_args: dict
    stocks: str
    timeframes: list[str]
    startingDate: str
    endingDate:str

@app.post("/strategies/functions/input")
async def receive_backtest_input(input_data: BacktestInput):
    stored_inputs.clear()
    stored_inputs.append(input_data)
    # Return something so client knows it worked
    return JSONResponse(content={"message": "Input received", "received": input_data.dict()})

@app.get("/strategies/functions/input")
async def get_all_inputs():
    if not stored_inputs:
        return JSONResponse(status_code=404, content={"error": "No input data found"})
    return stored_inputs

@app.get("/strategies/functions/run")
async def run_backtest():
    try:
        if not stored_inputs:
            return JSONResponse(status_code=400, content={"error": "No input data available"})

        # Convert BacktestInput Pydantic model to dict and then to list of values for get_inputs
        checkLoad = list(stored_inputs[0].dict().values())
        print("CheckLoad being passed to get_inputs:", checkLoad)
       
        output = await backend.StrategyTesting.main.process_inputs(checkLoad)
        # Removed sending backtest completed message
        # await backend.StrategyTesting.main.send_log("🔚 Backtest completed successfully.")
        # output = backend.StrategyTesting.main.showOutput()
        print("Output Recieved .. from PostAPI")
        print(output,"Here is the OUTPUT")
        
        return JSONResponse(content={"message": "Backtest run successfully", "output": output})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e), "detail": "Error during backtest run"})