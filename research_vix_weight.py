import json
import numpy as np

def load_data(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def calc_score(data, index, w_ma, w_rsi, w_vix):
    close = data[index][2]
    ma60 = sum(d[2] for d in data[index-59:index+1]) / 60
    ma240 = sum(d[2] for d in data[index-239:index+1]) / 240
    dist_ma60 = (close - ma60) / ma60
    dist_ma240 = (close - ma240) / ma240
    
    score_ma240 = np.clip((dist_ma240 * -1) / 0.20 * 100, 0, 100)
    score_ma60 = np.clip((dist_ma60 * -1) / 0.15 * 100, 0, 100)
    score_ma = (score_ma240 * 0.6) + (score_ma60 * 0.4)
    
    rsi = data[index][7]
    score_rsi = np.clip((50 - rsi) / 20 * 100, 0, 100)
    
    vix = data[index][6]
    score_vix = np.clip((vix - 15) / 30 * 100, 0, 100)
    
    return (score_ma * w_ma) + (score_rsi * w_rsi) + (score_vix * w_vix)

def analyze_weights(data, market_name):
    # Current: 0.4 MA, 0.3 RSI, 0.3 VIX
    # Proposed: 0.2 MA, 0.3 RSI, 0.5 VIX (VIX Heavy)
    
    current_80s = []
    proposed_80s = []
    
    # Track discrete "events" (separated by at least 20 days)
    curr_events = []
    prop_events = []
    
    for i in range(240, len(data)):
        date = data[i][0]
        s_curr = calc_score(data, i, 0.4, 0.3, 0.3)
        s_prop = calc_score(data, i, 0.2, 0.3, 0.5)
        
        if s_curr > 80:
            if not curr_events or i - curr_events[-1]['idx'] > 20:
                curr_events.append({'date': date, 'idx': i})
                
        if s_prop > 80:
            if not prop_events or i - prop_events[-1]['idx'] > 20:
                prop_events.append({'date': date, 'idx': i})

    print(f"\n=== {market_name} Analysis ===")
    print(f"Current Weights (MA40/RSI30/VIX30) > 80 Events: {len(curr_events)}")
    for e in curr_events:
        print(f"  - {e['date']}")
        
    print(f"\nVIX Heavy Weights (MA20/RSI30/VIX50) > 80 Events: {len(prop_events)}")
    for e in prop_events:
        print(f"  - {e['date']}")

def main():
    tw_data = load_data('twii_data.json')
    analyze_weights(tw_data, "TWII")
    nq_data = load_data('nasdaq_data.json')
    analyze_weights(nq_data, "NASDAQ")

if __name__ == "__main__":
    main()
