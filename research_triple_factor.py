import json
import numpy as np

def load_data(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def test_triple_factor(data, market_name):
    print(f"\n=== Testing (100 - RSI) * VIX * Drawdown% for {market_name} ===")
    
    scores = []
    dates = []
    lows = []
    
    for i in range(120, len(data)):
        date = data[i][0]
        close = data[i][1]
        low = data[i][3]
        vix = data[i][6]
        rsi = data[i][7]
        
        recent_high = max(d[4] for d in data[i-120:i+1])
        drawdown_pct = ((recent_high - close) / recent_high) * 100
        drawdown_pct = max(1, drawdown_pct) # avoid 0 or negative
        
        inv_rsi = 100 - rsi
        score = inv_rsi * vix * drawdown_pct
        
        scores.append(score)
        dates.append(date)
        lows.append(low)
        
    scores = np.array(scores)
    
    p99 = np.percentile(scores, 99)
    p95 = np.percentile(scores, 95)
    p90 = np.percentile(scores, 90)
    
    print(f"Max Score: {np.max(scores):.0f}")
    print(f"Top 1% Threshold: {p99:.0f}")
    print(f"Top 5% Threshold: {p95:.0f}")
    print(f"Top 10% Threshold: {p90:.0f}")
    
    print("\n--- Historic Peaks (> Top 1%) ---")
    peak_events = []
    for i in range(len(scores)):
        if scores[i] > p99:
            if not peak_events or i - peak_events[-1]['idx'] > 20:
                local_max_idx = i
                for j in range(i, min(len(scores), i+20)):
                    if scores[j] > scores[local_max_idx]:
                        local_max_idx = j
                
                peak_events.append({
                    'idx': local_max_idx,
                    'date': dates[local_max_idx],
                    'score': scores[local_max_idx],
                    'low': lows[local_max_idx]
                })
                
    for event in peak_events:
        print(f"Date: {event['date']} | Low: {event['low']:.0f} | Triple Score: {event['score']:.0f}")

def main():
    tw = load_data('twii_data.json')
    test_triple_factor(tw, "TWII")

if __name__ == "__main__":
    main()
