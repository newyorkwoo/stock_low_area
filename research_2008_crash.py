import json

def load_data(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def analyze_2008(data, market_name):
    print(f"\n=== Analyzing 2008 Crash for {market_name} ===")
    for i in range(240, len(data)):
        date = data[i][0]
        if '2008-07' <= date <= '2009-04':
            close = data[i][2]
            low = data[i][3]
            open_price = data[i][1]
            prev_low = data[i-1][3]
            prev_close = data[i-1][2]
            
            recent_high = max(d[4] for d in data[i-120:i+1])
            ma240 = sum(d[2] for d in data[i-239:i+1]) / 240
            
            support_high = recent_high * 0.88
            support_ma = ma240 * 0.88
            
            is_below_high = low < support_high
            is_below_ma = low < support_ma
            
            is_gap_down = open_price < prev_low
            vix = data[i][6]
            prev_vix = data[i-1][6]
            is_vix_early = vix > 25 and vix < prev_vix and close < prev_close
            
            rsi = data[i][7]
            is_rsi_oversold = rsi < 45
            
            if (is_below_high and is_below_ma) and (is_gap_down or is_vix_early) and is_rsi_oversold:
                # Calculate additional metrics to see what differentiates the real bottom
                dist_ma240 = (low - ma240) / ma240
                dist_high = (low - recent_high) / recent_high
                
                # Volume spike
                vol = data[i][5]
                vol_ma20 = sum(d[5] for d in data[i-20:i]) / 20
                vol_ratio = vol / vol_ma20 if vol_ma20 > 0 else 1
                
                # VIX Max in last 10 days
                max_vix_10 = max(d[6] for d in data[i-10:i+1])
                
                print(f"Signal Date: {date} | Low: {low:.0f} | DistMA240: {dist_ma240*100:.1f}% | RSI: {rsi:.1f} | VIX: {vix:.1f} (Max10: {max_vix_10:.1f}) | VolRatio: {vol_ratio:.1f}x")

def main():
    tw_data = load_data('twii_data.json')
    analyze_2008(tw_data, "TWII")

if __name__ == "__main__":
    main()
