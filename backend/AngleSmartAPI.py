from SmartApi.smartConnect import SmartConnect
import pyotp
from logzero import logger
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time

# For Symbols:-
#url = 'https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json'


class AngleOne_Smart_API():
    def __init__(self,api_key,username,pwd,token):
        self.api_key = api_key  
        self.username = username
        self.pwd = pwd
        self.token = token
        
    def connect(self):
        api_key = self.api_key
        username = self.username
        pwd = self.pwd
        token = self.token
        smartApi = SmartConnect(api_key)
        
        try:
            token = token
            totp = pyotp.TOTP(token).now()
        except Exception as e:
            logger.error("Invalid Token: The provided token is not valid.")
            raise e

        data = smartApi.generateSession(username, pwd, totp)
        self.smartApi = smartApi
        if data['status'] == False:
            return logger.error(data)

        else:
            print("Successfully Connected 🟢") 
            # login api call
            # logger.info(f"You Credentials: {data}")
            authToken = data['data']['jwtToken']
            refreshToken = data['data']['refreshToken']
            # fetch the feedtoken
            feedToken = smartApi.getfeedToken()
            # fetch User Profile
            resources = smartApi.getProfile(refreshToken)
            smartApi.generateToken(refreshToken)
            exchange_available =resources['data']['exchanges']
            print("Got Resources and Exchange Available 🙌🏻")
            return resources,exchange_available
        
    def get_data(self,exchange,symbol,interval,fromDate,toDate):
        try:  
            token_data = self.smartApi.searchScrip(exchange, symbol)
        
            if not token_data or 'symboltoken' not in token_data["data"][0]:
                raise ValueError(f"Symbol token not found for {symbol}")

            symbol_token = token_data["data"][0]["symboltoken"]
        
        
            historicParam={
                "exchange": exchange,
                "symboltoken": symbol_token,
                "interval": interval,
                "fromdate": f"{fromDate} 09:00", 
                "todate": f"{toDate} 09:16"
            }
            hist = self.smartApi.getCandleData(historicParam)

        except Exception as e:
            logger.exception(f"Logout failed: {e}")
        
        data = pd.DataFrame(hist["data"])
        data.columns = ["Date","Open","High","Low","Close","Volume"]
        # data['Date'] = pd.to_datetime(data['Date']).dt.date # this not includes time
        data['Date'] = pd.to_datetime(data['Date']).dt.strftime('%Y-%m-%d %H:%M') # this includes time
        
    
        return data
    
    def get_FullData(self, exchange, symbol, interval, start_date, final_end_date=None):
        final_data = pd.DataFrame()
        current_date = datetime.strptime(start_date, "%Y-%m-%d")
        today_date = datetime.today()

        while current_date < today_date:
            # Calculate end date for the current chunk
            next_date = current_date + relativedelta(months=3)
            # Cap to either user-defined end date or today's date
            endDate = min(next_date, today_date)
            if final_end_date:
                endDate = min(endDate, datetime.strptime(final_end_date, "%Y-%m-%d"))

            # Format dates
            from_date_str = current_date.strftime("%Y-%m-%d")
            to_date_str = endDate.strftime("%Y-%m-%d")

            print(f"Fetching from {from_date_str} to {to_date_str}...")

            # Fetch and append
            data = self.get_data(exchange, symbol, interval, from_date_str, to_date_str)

            if isinstance(data, pd.DataFrame) and not data.empty:
                final_data = pd.concat([final_data, data], ignore_index=True)

            if endDate <= current_date:
                print("Warning: End date did not advance. Breaking loop to avoid infinite run.")
                break
            current_date = endDate
            time.sleep(0.8)

        final_data.reset_index(drop=True, inplace=True)
        return final_data