import json
import numpy as np

def load_data(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def get_swing_regions(data, reversal=0.05, drop_threshold=0.08):
    peaks = []
    troughs = []
    state = 1
    peak_idx = 0
    trough_idx = 0
    for i in range(len(data)):
        high = data[i][4]
        low = data[i][3]
        close = data[i][2]
        if state == 1:
            if high > data[peak_idx][4]:
                peak_idx = i
            if (data[peak_idx][4] - close) / data[peak_idx][4] >= reversal:
                state = -1
                trough_idx = i
        else:
            if low < data[trough_idx][3]:
                trough_idx = i
            if (close - data[trough_idx][3]) / data[trough_idx][3] >= reversal:
                drop = (data[peak_idx][4] - data[trough_idx][3]) / data[peak_idx][4]
                if drop >= drop_threshold:
                    peaks.append(peak_idx)
                    troughs.append(trough_idx)
                state = 1
                peak_idx = i
    if state == -1:
        drop = (data[peak_idx][4] - data[trough_idx][3]) / data[peak_idx][4]
        if drop >= drop_threshold:
            peaks.append(peak_idx)
            troughs.append(trough_idx)
    return peaks, troughs

def calc_composite_score(data, index):
    close = data[index][2]
    
    # 1. Price deviation from MA60 and MA240
    ma60 = sum(d[2] for d in data[index-59:index+1]) / 60
    ma240 = sum(d[2] for d in data[index-239:index+1]) / 240
    dist_ma60 = (close - ma60) / ma60
    dist_ma240 = (close - ma240) / ma240
    
    # Score MA: combined deviation. 
    # If dist_ma240 is -20% -> 100 points. If 0% -> 0 points.
    score_ma240 = np.clip((dist_ma240 * -1) / 0.20 * 100, 0, 100)
    score_ma60 = np.clip((dist_ma60 * -1) / 0.15 * 100, 0, 100)
    score_ma = (score_ma240 * 0.6) + (score_ma60 * 0.4)
    
    # 2. RSI Score
    rsi = data[index][7]
    # RSI from 50 down to 30 => 0 to 100
    score_rsi = np.clip((50 - rsi) / 20 * 100, 0, 100)
    
    # 3. VIX Score
    vix = data[index][6]
    # VIX from 15 to 45 => 0 to 100
    score_vix = np.clip((vix - 15) / 30 * 100, 0, 100)
    
    # Total composite Score
    total_score = (score_ma * 0.4) + (score_rsi * 0.3) + (score_vix * 0.3)
    return total_score

def analyze_composite(data, troughs, market_name):
    print(f"\n=== Analyzing Composite Score for {market_name} ===")
    
    scores_at_bottom = []
    for t in troughs:
        if t < 240: continue
        score = calc_composite_score(data, t)
        scores_at_bottom.append(score)
        
    print(f"Average Score at Bottom: {np.mean(scores_at_bottom):.1f}")
    print(f"Median Score at Bottom: {np.median(scores_at_bottom):.1f}")
    print(f"Max Score at Bottom (e.g. 2008/2020): {np.max(scores_at_bottom):.1f}")
    
    # Calculate scores for all days to find thresholds
    all_scores = [calc_composite_score(data, i) for i in range(240, len(data))]
    
    print("\nScore Distribution (All Days):")
    print(f"Days with score > 80: {sum(1 for s in all_scores if s > 80)}")
    print(f"Days with score > 60: {sum(1 for s in all_scores if s > 60)}")
    print(f"Days with score > 40: {sum(1 for s in all_scores if s > 40)}")

def analyze_2008_trend(data, market_name):
    print(f"\n=== 2008 Mega Bear Market Trace for {market_name} ===")
    for i in range(240, len(data)):
        date = data[i][0]
        if '2008-07' <= date <= '2009-04':
            score = calc_composite_score(data, i)
            close = data[i][2]
            vix = data[i][6]
            rsi = data[i][7]
            if score > 50:
                print(f"Date: {date} | Close: {close:.0f} | Panic Score: {score:.1f} (VIX: {vix:.1f}, RSI: {rsi:.1f})")

def main():
    tw_data = load_data('twii_data.json')
    analyze_2008_trend(tw_data, "TWII")

if __name__ == "__main__":
    main()
