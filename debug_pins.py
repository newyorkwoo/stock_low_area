import json

with open('twii_data.json', 'r') as f:
    data = json.load(f)

for i in range(120, len(data)):
    date = data[i][0]
    if '2020-03' in date or '2022-10' in date:
        open_price = data[i][1]
        close = data[i][2]
        low = data[i][3]
        high = data[i][4]
        
        prev_low = data[i-1][3]
        prev_close = data[i-1][2]
        
        recent_high = max(d[4] for d in data[i-120:i+1])
        drop = (recent_high - low) / recent_high
        
        is_gap_down = open_price < prev_low
        vix = data[i][6]
        prev_vix = data[i-1][6]
        is_vix_early = vix > 25 and vix < prev_vix and close < prev_close
        rsi = data[i][7]
        is_rsi = rsi < 45
        is_rsi_strict = rsi < 42
        
        if drop > 0.10 and (is_gap_down or is_vix_early):
            print(f"{date}: Drop={drop:.2f}, GapDown={is_gap_down}, VixEarly={is_vix_early}, RSI={rsi:.1f}, StrictRSI={is_rsi_strict}")
