import pandas as pd
import numpy as np
import os
import math

class Backtest:
    def __init__(self,df, risk_free_rate=0.05, trading_days_per_year=252):
        self.df = df
        self.risk_free_rate = risk_free_rate
        self.trading_days_per_year = trading_days_per_year
        self.metrics = []  # Stores metrics for each ticker

    def run(self):
        df= self.df
        
        trades = []
        inPosition = False
        entry_date = ""
        entry_price = 0
        for i in range(len(df)):
            row = df.iloc[i]
            if not inPosition and df.at[i,"entry"] == 1:
                inPosition = True
                entry_price=row["Open"]
                entry_date = row["Date"]
                
            elif inPosition and df.at[i,"exit"] == 1:
                

                trades.append({
                        'Entry Date': entry_date,
                        'Entry Price': round(entry_price, 2),
                        'Exit Date': row["Date"],
                        'Exit Price': round(row["Open"], 2),
                        'pnl': round(row["Open"] - entry_price, 2),
                        'Change (%)': round(((row["Open"] - entry_price) / entry_price) * 100, 2),
                    })
                inPosition = False
                
        return trades
                
            
        
    
    
    
    def analyze_ticker(self):
        
        result = self.run()
        result_df = pd.DataFrame(result)

        # Return as decimal
        returns = result_df["Change (%)"] / 100

        # Entry and Exit Dates
        entry_dates = pd.to_datetime(result_df["Entry Date"])
        exit_dates = pd.to_datetime(result_df["Exit Date"])
        holding_days = (exit_dates - entry_dates).dt.days
        avg_holding_days = holding_days.mean()

        # Time span
        start_date = entry_dates.min()
        end_date = exit_dates.max()
        total_days = (end_date - start_date).days
        years = total_days / 365.25

        # Equity curve
        equity_curve = (1 + returns).cumprod()

        # Daily returns (simulated)
        daily_returns = equity_curve.pct_change().dropna()
        sharpe_annualized = (daily_returns.mean() / daily_returns.std()) * np.sqrt(self.trading_days_per_year)

        # Max drawdown
        rolling_max = equity_curve.cummax()
        drawdown = (equity_curve - rolling_max) / rolling_max
        max_drawdown = drawdown.min()

        # Expectancy
        win_rate = len(returns[returns > 0]) / len(returns)
        loss_rate = 1 - win_rate
        avg_win = returns[returns > 0].mean()
        avg_loss = returns[returns < 0].mean()
        expectancy = (avg_win * win_rate) + (avg_loss * loss_rate)

        # CAGR
        final_equity = equity_curve.iloc[-1]
        cagr = final_equity**(1 / years) - 1 if final_equity > 0 else -1
        def safe_float(val):
            if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                return 0.0
            return round(float(val),2)
        # Store metrics
        metrics = {
            "Total Trades": len(result_df),
            "Mean Return (%)": safe_float(returns.mean() * 100),
            "Average Loss (%)": safe_float(avg_loss * 100),
            "Average Holding Days": safe_float(avg_holding_days),
            "Win Rate (%)": safe_float(win_rate * 100),
            "Expectancy (%)": safe_float(expectancy * 100),
            "Sharpe Ratio (Annualized)": safe_float(sharpe_annualized),
            "Max Drawdown (%)": safe_float(max_drawdown * 100),
            "CAGR (%)": safe_float(cagr * 100),
        }
        # metrics = {"Hardik"}

        # self.metrics.append(metrics)

        # Print summary
        # for k, v in metrics.items():
        #     print(f"{k}: {v}")

        return metrics

    # def analyze_all(self, ticker_list):
    #     mean_returns = []
    #     for ticker in ticker_list:
    #         metrics = self.analyze_ticker(ticker)
    #         if metrics:
    #             mean_returns.append(metrics["Mean Return (%)"])

    #     if mean_returns:
    #         avg_mean_return = sum(mean_returns) / len(mean_returns)
    #         print("\nAverage Mean Return Across All Tickers (%):", avg_mean_return)
    #     else:
    #         print("No valid tickers processed.")

    #     return self.metrics
