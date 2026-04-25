import json
import numpy as np

def load_data(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def test_rsi_div_vix(data, market_name):
    print(f"\n=== Testing RSI / VIX for {market_name} (Top Hunting) ===")
    
    scores = []
    dates = []
    highs = []
    
    for i in range(120, len(data)):
        date = data[i][0]
        high = data[i][3] # Using high price
        vix = data[i][6]
        rsi = data[i][7]
        
        # Calculate RSI / VIX
        if vix == 0: vix = 1 # prevent division by zero
        score = rsi / vix
        
        scores.append(score)
        dates.append(date)
        highs.append(high)
        
    scores = np.array(scores)
    
    p99 = np.percentile(scores, 99)
    p95 = np.percentile(scores, 95)
    p90 = np.percentile(scores, 90)
    
    print(f"Max Score: {np.max(scores):.2f}")
    print(f"Top 1% Threshold (Extreme Euphoria): {p99:.2f}")
    print(f"Top 5% Threshold (Strong Bull): {p95:.2f}")
    print(f"Top 10% Threshold: {p90:.2f}")
    
    print("\n--- Historic Peaks (> Top 1%) ---")
    peak_events = []
    for i in range(len(scores)):
        if scores[i] > p99:
            # We want to find local MAX of the Greedy score
            if not peak_events or i - peak_events[-1]['idx'] > 20:
                local_max_idx = i
                for j in range(i, min(len(scores), i+20)):
                    if scores[j] > scores[local_max_idx]:
                        local_max_idx = j
                
                peak_events.append({
                    'idx': local_max_idx,
                    'date': dates[local_max_idx],
                    'score': scores[local_max_idx],
                    'high': highs[local_max_idx]
                })
                
    for event in peak_events:
        print(f"Date: {event['date']} | High: {event['high']:.0f} | Ratio: {event['score']:.2f}")

def main():
    tw = load_data('twii_data.json')
    test_rsi_div_vix(tw, "TWII")
    
    nq = load_data('nasdaq_data.json')
    test_rsi_div_vix(nq, "NASDAQ")

if __name__ == "__main__":
    main()
