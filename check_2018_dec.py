import json

def load_data(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def check_date(data, target_date, market):
    print(f"=== {market} data for {target_date} ===")
    for i in range(120, len(data)):
        if target_date in data[i][0]:
            close = data[i][2]
            low = data[i][3]
            open_p = data[i][1]
            prev_low = data[i-1][3]
            prev_close = data[i-1][2]
            
            recent_high = max(d[4] for d in data[i-120:i+1])
            ma240 = sum(d[2] for d in data[i-239:i+1]) / 240
            
            supp_high = recent_high * 0.88
            supp_ma = ma240 * 0.88
            
            is_below_high = low < supp_high
            is_below_ma = low < supp_ma
            
            rsi = data[i][7]
            vix = data[i][6]
            prev_vix = data[i-1][6]
            
            is_gap_down = open_p < prev_low
            is_vix_early = vix > 25 and vix < prev_vix and close < prev_close
            
            print(f"Low: {low:.0f}")
            print(f"Recent High: {recent_high:.0f} (Support: {supp_high:.0f}) -> isBelowHigh: {is_below_high}")
            print(f"MA240: {ma240:.0f} (Support: {supp_ma:.0f}) -> isBelowMA: {is_below_ma}")
            print(f"RSI: {rsi:.1f} (Needs < 40)")
            print(f"VIX: {vix:.1f} (Needs > 35 or Low < {ma240*0.8:.0f})")
            print(f"Prev VIX: {prev_vix:.1f}")
            print(f"Gap Down: {is_gap_down}")
            print(f"Vix Peaked Early: {is_vix_early}")
            
            is_diamond = is_below_high and is_below_ma and rsi < 40 and (vix > 35 or low < ma240*0.8) and (is_gap_down or is_vix_early)
            print(f"TRIGGER DIAMOND: {is_diamond}")

def main():
    tw = load_data('twii_data.json')
    check_date(tw, '2018-12-24', 'TWII')
    check_date(tw, '2018-12-25', 'TWII')
    
    nq = load_data('nasdaq_data.json')
    check_date(nq, '2018-12-24', 'NASDAQ')

if __name__ == "__main__":
    main()
