import json

def load_data(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def analyze_recent(data, market_name):
    print(f"\n=== Recent Month Analysis (2026-03 to 2026-04) for {market_name} ===")
    print(f"{'Date':<12} | {'Close':<6} | {'High':<6} | {'Low':<6} | {'VIX':<5} | {'RSI':<5} | {'Panic Score':<11} | {'Greed Score'}")
    print("-" * 80)
    
    max_high = 0
    min_low = float('inf')
    max_high_date = ""
    min_low_date = ""
    
    max_panic = 0
    max_panic_date = ""
    max_greed = 0
    max_greed_date = ""
    
    for i in range(120, len(data)):
        date = data[i][0]
        if '2026-03' <= date <= '2026-04-30':
            close = data[i][1]
            high = data[i][3]
            low = data[i][2]
            vix = data[i][6]
            rsi = data[i][7]
            if rsi == 0: rsi = 1
            if vix == 0: vix = 1
            
            panic_score = (vix / rsi) * 60
            greed_score = (rsi / vix) * 15
            
            if high > max_high:
                max_high = high
                max_high_date = date
            if low < min_low:
                min_low = low
                min_low_date = date
                
            if panic_score > max_panic:
                max_panic = panic_score
                max_panic_date = date
            if greed_score > max_greed:
                max_greed = greed_score
                max_greed_date = date
                
            print(f"{date:<12} | {close:<6.0f} | {high:<6.0f} | {low:<6.0f} | {vix:<5.1f} | {rsi:<5.1f} | {panic_score:<11.1f} | {greed_score:.1f}")
            
    print("-" * 80)
    print(f"Swing High: {max_high_date} ({max_high:.0f})")
    print(f"Swing Low: {min_low_date} ({min_low:.0f})")
    print(f"Max Greed Score: {max_greed_date} ({max_greed:.1f}) -> Predicted Top")
    print(f"Max Panic Score: {max_panic_date} ({max_panic:.1f}) -> Predicted Bottom")

def main():
    tw = load_data('twii_data.json')
    analyze_recent(tw, "TWII")
    
    nq = load_data('nasdaq_data.json')
    analyze_recent(nq, "NASDAQ")

if __name__ == "__main__":
    main()
