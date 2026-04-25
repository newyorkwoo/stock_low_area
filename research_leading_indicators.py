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
                
    # Check pending
    if state == -1:
        drop = (data[peak_idx][4] - data[trough_idx][3]) / data[peak_idx][4]
        if drop >= drop_threshold:
            peaks.append(peak_idx)
            troughs.append(trough_idx)
            
    return peaks, troughs

def analyze_peaks(data, peaks):
    print(f"\n--- Analyzing {len(peaks)} Swing Peaks ---")
    rsi_divergence_count = 0
    vol_exhaustion_count = 0
    momentum_decay_count = 0
    vix_divergence_count = 0
    
    for p in peaks:
        if p < 20: continue
        
        # Leading days: T-5 to T
        date = data[p][0]
        peak_price = data[p][4]
        
        # 1. Momentum Decay (ROC5 decreasing)
        roc5_t0 = (data[p][2] - data[p-5][2]) / data[p-5][2]
        roc5_t3 = (data[p-3][2] - data[p-8][2]) / data[p-8][2]
        if roc5_t0 < roc5_t3:
            momentum_decay_count += 1
            
        # 2. RSI Divergence (Price making new high, RSI dropping or flat)
        rsi_t0 = data[p][7]
        rsi_t3 = data[p-3][7]
        if rsi_t0 < rsi_t3 and rsi_t0 > 60:
            rsi_divergence_count += 1
            
        # 3. Volume Exhaustion (Volume shrinking as price peaks)
        vol_t0 = data[p][5]
        vol_ma10 = sum(d[5] for d in data[p-10:p]) / 10
        if vol_t0 < vol_ma10 * 0.9:
            vol_exhaustion_count += 1
            
        # 4. VIX Divergence (VIX starting to rise before price peaks)
        vix_t0 = data[p][6]
        vix_t3 = data[p-3][6]
        vix_t5 = data[p-5][6]
        if vix_t0 > min(vix_t3, vix_t5) and vix_t0 < 20:
            vix_divergence_count += 1

    print(f"1. Momentum Decay (Growth slowing down): {momentum_decay_count}/{len(peaks)} ({(momentum_decay_count/len(peaks))*100:.1f}%)")
    print(f"2. RSI Divergence (Price up, RSI down): {rsi_divergence_count}/{len(peaks)} ({(rsi_divergence_count/len(peaks))*100:.1f}%)")
    print(f"3. Volume Exhaustion (Low volume at peak): {vol_exhaustion_count}/{len(peaks)} ({(vol_exhaustion_count/len(peaks))*100:.1f}%)")
    print(f"4. VIX Divergence (Fear slowly rising early): {vix_divergence_count}/{len(peaks)} ({(vix_divergence_count/len(peaks))*100:.1f}%)")


def analyze_troughs(data, troughs):
    print(f"\n--- Analyzing {len(troughs)} Swing Troughs ---")
    capitulation_vol_count = 0
    rsi_divergence_count = 0
    vix_peak_early_count = 0
    gap_down_count = 0
    
    for t in troughs:
        if t < 20: continue
        
        # 1. Capitulation Volume (Volume spikes in days leading to bottom)
        # Check if any day from T-3 to T had volume > 1.3x MA20
        vol_ma20 = sum(d[5] for d in data[t-20:t]) / 20
        has_spike = any(data[i][5] > vol_ma20 * 1.3 for i in range(t-3, t+1))
        if has_spike:
            capitulation_vol_count += 1
            
        # 2. VIX Peaked Early (VIX highest point was 1-3 days BEFORE the actual price low)
        vix_slice = [data[i][6] for i in range(t-5, t+1)]
        max_vix_idx = vix_slice.index(max(vix_slice))
        # max_vix_idx == 5 is T0. If it's < 5, it means VIX peaked before price bottomed.
        if max_vix_idx < 5:
            vix_peak_early_count += 1
            
        # 3. RSI Divergence (Price lower, but RSI higher than previous low)
        # We check T0 RSI vs T-3 RSI
        rsi_t0 = data[t][7]
        rsi_t3 = data[t-3][7]
        if rsi_t0 > rsi_t3 and rsi_t0 < 45:
            rsi_divergence_count += 1
            
        # 4. Gap Down near bottom (Panic selling)
        has_gap = False
        for i in range(t-2, t+1):
            if data[i][1] < data[i-1][3]: # Open < Prev Low
                has_gap = True
                break
        if has_gap:
            gap_down_count += 1
            

    print(f"1. Volume Capitulation (Panic spike): {capitulation_vol_count}/{len(troughs)} ({(capitulation_vol_count/len(troughs))*100:.1f}%)")
    print(f"2. VIX Peaked Early (Fear topped before price): {vix_peak_early_count}/{len(troughs)} ({(vix_peak_early_count/len(troughs))*100:.1f}%)")
    print(f"3. RSI Divergence (Price down, RSI stops falling): {rsi_divergence_count}/{len(troughs)} ({(rsi_divergence_count/len(troughs))*100:.1f}%)")
    print(f"4. Panic Gap Down (Exhaustion gap): {gap_down_count}/{len(troughs)} ({(gap_down_count/len(troughs))*100:.1f}%)")

def main():
    print("=== Analyzing TWII Data ===")
    tw_data = load_data('twii_data.json')
    tw_peaks, tw_troughs = get_swing_regions(tw_data)
    analyze_peaks(tw_data, tw_peaks)
    analyze_troughs(tw_data, tw_troughs)

    print("\n=== Analyzing NASDAQ Data ===")
    nq_data = load_data('nasdaq_data.json')
    nq_peaks, nq_troughs = get_swing_regions(nq_data)
    analyze_peaks(nq_data, nq_peaks)
    analyze_troughs(nq_data, nq_troughs)

if __name__ == "__main__":
    main()
