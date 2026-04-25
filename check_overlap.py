import json

with open('twii_data.json', 'r') as f:
    data = json.load(f)

print("Checking Oct 2022 values:")
for i in range(120, len(data)):
    date = data[i][0]
    if '2022-10' in date:
        close = data[i][2]
        low = data[i][3]
        recent_high = max(d[4] for d in data[i-120:i+1])
        ma240 = sum(d[2] for d in data[i-239:i+1]) / 240
        
        support_high = recent_high * 0.88
        support_ma = ma240 * 0.88
        
        print(f"{date}: Low={low:.0f}, High120={recent_high:.0f}, MA240={ma240:.0f} | SuppHigh(-12%)={support_high:.0f}, SuppMA(-12%)={support_ma:.0f} | Diff={abs(support_high - support_ma):.0f}")
