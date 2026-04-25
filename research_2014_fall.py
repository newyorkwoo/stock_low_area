import json

def load_data(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def analyze_2014(data):
    print("=== 2014 Fall Analysis (Aug to Nov) ===")
    print(f"{'Date':<12} | {'Close':<6} | {'High':<6} | {'Low':<6} | {'VIX':<5} | {'RSI':<5} | {'Panic Score(VIX/RSI)':<22} | {'Greed Score(RSI/VIX)':<20}")
    print("-" * 100)
    
    for i in range(120, len(data)):
        date = data[i][0]
                
        if '2014-08-20' <= date <= '2014-10-31':
            low = data[i][2]
            high = data[i][3]
            close = data[i][1]
            vix = data[i][6]
            rsi = data[i][7]
            if rsi == 0: rsi = 1
            if vix == 0: vix = 1
            
            panic_score = (vix / rsi) * 60
            greed_score = (rsi / vix) * 15
            
            print(f"{date:<12} | {close:<6.0f} | {high:<6.0f} | {low:<6.0f} | {vix:<5.1f} | {rsi:<5.1f} | {panic_score:<22.1f} | {greed_score:.1f}")

def main():
    tw = load_data('twii_data.json')
    analyze_2014(tw)

if __name__ == "__main__":
    main()
