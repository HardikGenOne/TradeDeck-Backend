import pandas as pd
import numpy as np
from .Backtest import Backtest
# import pandas_ta as ta

class Strategy:
    def __init__(self,df):
        self.df = df
        
    def SMA_CROSSOVER_results(self,shortPeriod,longPeriod=None):
        sPeriod = str(shortPeriod['shortPeriod']).replace(","," ").split()
        lPeriod = str(shortPeriod['longPeriod']).replace(","," ").split()
        # sPeriod = str(sPeriod).replace(",", " ").split()
        # lPeriod = str(lPeriod).replace(",", " ").split()
        result_list = []
        for sMA in sPeriod:
            for lMA in lPeriod:
                if int(sMA) < int(lMA):
                    min_len = int(sMA)
                    max_len = int(lMA)

                    if len(self.df) < max_len:
                        print(f"Skipping combo {sMA}_{lMA} because data length {len(self.df)} < {max_len}")
              
                        continue  # avoid crash on short dataset

                    df_copy = self.df.copy()

                    df_copy["SMA_Min"] = df_copy["Close"].rolling(window=min_len).mean()
                    df_copy["SMA_Max"] = df_copy["Close"].rolling(window=max_len).mean()
                    df_copy.dropna(inplace=True)
                    df_copy.reset_index(drop=True, inplace=True)

                    df_copy["signal"] = np.where(df_copy["SMA_Min"] > df_copy["SMA_Max"], 1, 0)

                    bt = Backtest(df_copy)
                    result = bt.summary()
                    result_list.append({f"{sMA}_{lMA}": result})
        # print("Results from Strategies.py :",result_list)
        print("result_list loaded" if result_list else "result list is empty") 
        if not result_list:
            return [{"message": "No valid period combinations for data length"}]
        return result_list
    
    def TURTLE_TRADING_results(self, EntryWindow, ExitWindow=None, ATR_LENGTH=None):


        HIGH_WINDOW = int(EntryWindow["EntryWindow"])
        LOW_WINDOW = int(EntryWindow["ExitWindow"])
        ATR_LENGTH = int(EntryWindow["ATR_LENGTH"])

        result_list = []
        df = self.df.copy()
        df[f"Entry_{HIGH_WINDOW}"] = df["High"].rolling(window=HIGH_WINDOW).max().shift(1)
        df[f"Exit_{LOW_WINDOW}"] = df["High"].rolling(window=LOW_WINDOW).min().shift(1)

        in_trades = False
        entry_price = 0
        entry_date = ""
        trades = []

        for i in range(len(df)):
            row = df.iloc[i]
            if not in_trades:
                if row["Close"] > row[f"Entry_{HIGH_WINDOW}"]:
                    in_trades = True
                    entry_price = row["Close"]
                    entry_date = row["Date"]
            else:
                if row["Close"] < row[f"Exit_{LOW_WINDOW}"]:
                    exit_price = row["Close"]
                    pnl = (exit_price - entry_price) / entry_price * 100
                    exit_date = row["Date"]
                    trades.append({
                        "entryDate": entry_date,
                        "exit_date": exit_date,
                        "entry_prices": entry_price,
                        "exitPrice": exit_price,
                        "pnl": pnl
                    })
                    in_trades = False

        trades_df = pd.DataFrame(trades)
        if trades_df.empty:
            return [{"message": "No trades found"}]

        trades_df["Win"] = trades_df["pnl"] > 0
        trades_df["entryDate"] = pd.to_datetime(trades_df["entryDate"])
        trades_df["exit_date"] = pd.to_datetime(trades_df["exit_date"])
        trades_df["HoldingDays"] = (trades_df["exit_date"] - trades_df["entryDate"]).dt.days
        trades_df["HoldingDays"].replace(0, 1, inplace=True)  # Avoid divide-by-zero

        # Approximate Daily Return for Sharpe (in decimals, not percent)
        trades_df["daily_return"] = (trades_df["pnl"] / 100) / trades_df["HoldingDays"]

        # Sharpe Calculation (Assume 252 trading days/year)
        avg_daily_return = trades_df["daily_return"].mean()
        std_daily_return = trades_df["daily_return"].std()
        sharpe_ratio = (avg_daily_return / std_daily_return) * np.sqrt(252) if std_daily_return != 0 else 0

        # For profitable trades
        profitable_trades = trades_df[trades_df["pnl"] > 0]["pnl"]
        filtered_days = trades_df.loc[trades_df["pnl"] > 0, "HoldingDays"]
        win_rate = trades_df["Win"].mean()

        result_list.append({
            ATR_LENGTH: {
                "Win Rate (%)": round(win_rate * 100, 2),
                "Average pnl": round(trades_df["pnl"].mean(), 2),
                "Total Trades": len(trades),
                "Profit Average (%)": round(profitable_trades.mean(), 2),
                "Average Profits Holding Days": int(filtered_days.mean()) if not filtered_days.empty else 0,
                "Sharpe Ratio": round(sharpe_ratio, 3)
            }
        })

        print("result_list loaded" if result_list else "result list is empty")
        return result_list
    
    def HeikinAshiCandle_results(self,greenConsecutive,redConsecutive = None,SMA_length = None):
        
        def heikin_ashi(df):
            ha_df = pd.DataFrame()
            ha_df["Date"] = df["Date"]
            # Calculate HA_Close
            ha_df['Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4

            # Calculate HA_Open
            ha_open = [(df['Open'].iloc[0] + df['Close'].iloc[0]) / 2]
            for i in range(1, len(df)):
                ha_open.append((ha_open[i - 1] + ha_df['Close'].iloc[i - 1]) / 2)
            ha_df['Open'] = ha_open

            # Calculate HA_High and HA_Low
            ha_df['High'] = pd.concat([ha_df['Open'], ha_df['Close'], df['High']], axis=1).max(axis=1)
            ha_df['Low'] = pd.concat([ha_df['Open'], ha_df['Close'], df['Low']], axis=1).min(axis=1)
            
            ha_df['Color'] = np.where(ha_df['Close'] > ha_df['Open'], 'green', 'red')


            return ha_df
        
        result_list = []
        print("in Strategies Heikin Ashi")
        
        
        green_consecutive = str(greenConsecutive['greenConsecutive']).replace(","," ").split() if greenConsecutive["greenConsecutive"] else ['3']
        red_consecutive = str(greenConsecutive['redConsecutive']).replace(","," ").split() if greenConsecutive["redConsecutive"] else ['2']
        SMA_len= str(greenConsecutive['SMA_length']).replace(","," ").split() if greenConsecutive["SMA_length"] else ['50']
    
        # df[f'SMA_{SMA_len}'] = df['Low'].rolling(window=SMA_len).mean()

        # --- Create Heikin Ashi Data ---
        
        for gC in green_consecutive:
            gC = int(gC)
            for rC in red_consecutive:
                rC = int(rC)
                for sL in SMA_len:
                    sL = int(sL)
                    
                    df = self.df.copy()
                    ha_df = heikin_ashi(df)
                    ha_df[f'SMA_{sL}'] = ha_df['Low'].rolling(window=sL).mean()
                    ha_df['entry'] = 0
                    ha_df['exit'] = 0
                    in_trade = False
                    green_count = 0
                    consecutive_reds = 0
                    exit_pending = False
                    

                    # --- Apply strategy logic ---
                    for i in range(1, len(ha_df)):
                        row = ha_df.iloc[i]
                        
                        if not in_trade:
                            if row["Color"] == "green":
                                green_count += 1
                                if green_count >= gC and row["Close"] > row[f'SMA_{sL}']:
                                    ha_df.at[i, 'entry'] = 1
                                    in_trade = True 
                                    green_count = 0
                            else:
                                green_count = 0

                        elif in_trade:
                            if exit_pending:
                                ha_df.at[i, 'exit'] = 1
                            
                                in_trade = False
                                exit_pending = False
                                consecutive_reds = 0
                                continue

                            if row["Color"] == "red":
                                consecutive_reds += 1
                                if consecutive_reds == rC:
                                    exit_pending = True
                            else:
                                consecutive_reds = 0

                    bt = Backtest(ha_df)
                    result = bt.analyze_ticker()
                    
                    result_list.append({f"{sL}_green: {gC}_red: {rC}":result})
        print("result list is ready to go ... from Strategies")
        return (result_list)