import json
import numpy as np

def load_data(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def get_swing_regions(data, reversal=0.05, drop_threshold=0.08):
    # data item: [Date, Open, Close, Low, High, Volume, VIX, RSI60]
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

def analyze_bottom_levels(data, peaks, troughs, market_name):
    print(f"\n=== Analyzing Bottom Levels for {market_name} ({len(troughs)} major bottoms) ===")
    
    drawdowns = []
    ma240_distances = []
    rsi_levels = []
    vix_levels = []
    
    for p, t in zip(peaks, troughs):
        if t < 240: continue
        
        peak_price = data[p][4]
        bottom_price = data[t][3]
        
        # 1. Drawdown
        drawdown = (peak_price - bottom_price) / peak_price
        drawdowns.append(drawdown)
        
        # 2. Distance from MA240
        # Calculate MA240 at trough
        ma240 = sum(d[2] for d in data[t-239:t+1]) / 240
        dist_ma240 = (bottom_price - ma240) / ma240
        ma240_distances.append(dist_ma240)
        
        # 3. RSI Level
        rsi_levels.append(data[t][7])
        
        # 4. VIX Peak Level near bottom
        vix_slice = [data[i][6] for i in range(t-10, t+1)]
        vix_levels.append(max(vix_slice))
        
    print(f"1. 波段跌幅 (Drawdown Depth):")
    print(f"   - 平均跌幅: {np.mean(drawdowns)*100:.1f}%")
    print(f"   - 中位數跌幅: {np.median(drawdowns)*100:.1f}%")
    print(f"   - 前 25% 輕微回檔: {np.percentile(drawdowns, 25)*100:.1f}%")
    print(f"   - 前 75% 嚴重股災: {np.percentile(drawdowns, 75)*100:.1f}%")
    print(f"   - 極端最大跌幅: {np.max(drawdowns)*100:.1f}%")
    
    print(f"\n2. 距離年線位置 (Distance from MA240):")
    print(f"   - 平均在年線之下: {np.mean(ma240_distances)*100:.1f}%")
    print(f"   - 只有 {sum(1 for d in ma240_distances if d > 0)}/{len(ma240_distances)} 次大底在年線之上 (代表大底通常在跌破年線後發生)")
    print(f"   - 嚴重的底部通常落在年線之下: {np.percentile(ma240_distances, 25)*100:.1f}% 左右")
    
    print(f"\n3. 底部特徵指標 (RSI & VIX):")
    print(f"   - 平均底部 RSI(60): {np.mean(rsi_levels):.1f}")
    print(f"   - 有 {sum(1 for r in rsi_levels if r < 45)}/{len(rsi_levels)} 次底部的 RSI < 45")
    print(f"   - 底部附近出現的最大 VIX 平均為: {np.mean(vix_levels):.1f} (中位數: {np.median(vix_levels):.1f})")

def main():
    tw_data = load_data('twii_data.json')
    tw_peaks, tw_troughs = get_swing_regions(tw_data)
    analyze_bottom_levels(tw_data, tw_peaks, tw_troughs, "TWII")

    nq_data = load_data('nasdaq_data.json')
    nq_peaks, nq_troughs = get_swing_regions(nq_data)
    analyze_bottom_levels(nq_data, nq_peaks, nq_troughs, "NASDAQ")

if __name__ == "__main__":
    main()
