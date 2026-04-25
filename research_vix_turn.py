import json

def load_data(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def analyze_vix_turn(data, market_name):
    print(f"\n=== VIX Turnaround vs Price Bottom ({market_name}) ===")
    
    # Let's find local VIX peaks > 35
    vix_peaks = []
    for i in range(10, len(data)-10):
        vix = data[i][6]
        if vix > 35:
            # Check if it's a local maximum in a 20-day window
            is_peak = True
            for j in range(i-10, i+10):
                if data[j][6] > vix:
                    is_peak = False
                    break
            if is_peak and (not vix_peaks or i - vix_peaks[-1] > 20):
                vix_peaks.append(i)
                
    # For each VIX peak, find the lowest price in the surrounding window (-5 to +15 days)
    total_delay = 0
    count = 0
    
    for p_idx in vix_peaks:
        vix_peak_date = data[p_idx][0]
        vix_peak_val = data[p_idx][6]
        
        # Find price bottom in [-5, +15] days
        lowest_price = float('inf')
        bottom_idx = p_idx
        
        start_idx = max(0, p_idx - 5)
        end_idx = min(len(data)-1, p_idx + 15)
        
        for j in range(start_idx, end_idx + 1):
            if data[j][3] < lowest_price:
                lowest_price = data[j][3]
                bottom_idx = j
                
        bottom_date = data[bottom_idx][0]
        delay_days = bottom_idx - p_idx
        
        print(f"VIX Peak: {vix_peak_date} (VIX: {vix_peak_val:.1f}) | Price Bottom: {bottom_date} (Low: {lowest_price:.0f}) | Delay: {delay_days} days")
        total_delay += delay_days
        count += 1
        
    if count > 0:
        print(f"\nAverage Delay: {total_delay/count:.1f} days")

def main():
    tw = load_data('twii_data.json')
    analyze_vix_turn(tw, "TWII")

if __name__ == "__main__":
    main()
