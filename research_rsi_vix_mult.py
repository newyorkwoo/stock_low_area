import json
import numpy as np

def load_data(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def test_rsi_vix_multiplier(data, market_name):
    print(f"\n=== Testing (100 - RSI) * VIX for {market_name} ===")
    
    scores = []
    dates = []
    lows = []
    
    for i in range(120, len(data)):
        date = data[i][0]
        low = data[i][3]
        vix = data[i][6]
        rsi = data[i][7]
        
        # Calculate the user's formula
        inv_rsi = 100 - rsi
        score = inv_rsi * vix
        
        scores.append(score)
        dates.append(date)
        lows.append(low)
        
    scores = np.array(scores)
    
    # Let's find the top 1% and 5% thresholds
    p99 = np.percentile(scores, 99)
    p95 = np.percentile(scores, 95)
    p90 = np.percentile(scores, 90)
    
    print(f"Top 1% Threshold: {p99:.0f}")
    print(f"Top 5% Threshold: {p95:.0f}")
    print(f"Top 10% Threshold: {p90:.0f}")
    
    # Print the dates where score > Top 1% to see if they are true bottoms
    print("\n--- Historic Peaks of this Indicator (> Top 1%) ---")
    peak_events = []
    for i in range(len(scores)):
        if scores[i] > p99:
            if not peak_events or i - peak_events[-1]['idx'] > 20:
                # Find the max score in the local 20-day window
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
        print(f"Date: {event['date']} | Low: {event['low']:.0f} | Mult Score: {event['score']:.0f}")

def main():
    tw = load_data('twii_data.json')
    test_rsi_vix_multiplier(tw, "TWII")
    
    nq = load_data('nasdaq_data.json')
    test_rsi_vix_multiplier(nq, "NASDAQ")

if __name__ == "__main__":
    main()
