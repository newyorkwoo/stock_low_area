"""
波段低點指標特性深度研究
===========================
分析各指標在歷史波段低點時的數值特徵和規律
"""

import json
import pandas as pd
from datetime import datetime

# 載入數據
with open("twii_data.json", "r", encoding="utf-8") as f:
    twii_data = json.load(f)

with open("nasdaq_data.json", "r", encoding="utf-8") as f:
    nasdaq_data = json.load(f)


def parse_data(raw_data):
    """解析原始數據"""
    dates = []
    closes = []
    lows = []
    highs = []
    vix = []
    rsi = []
    adl = []

    for item in raw_data:
        dates.append(item[0])
        closes.append(item[2])
        lows.append(item[3])
        highs.append(item[4])
        vix.append(item[6])
        rsi.append(item[7])
        adl.append(item[8])

    df = pd.DataFrame({
        'Date': dates,
        'Close': closes,
        'Low': lows,
        'High': highs,
        'VIX': vix,
        'RSI': rsi,
        'ADL': adl
    })
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    return df


def find_swing_lows(df, min_drop=0.08):
    """找出波段低點（跌幅 > 8%）"""
    swing_lows = []

    # 使用滾動窗口尋找局部低點
    for i in range(20, len(df) - 20):
        # 檢查是否為局部低點
        is_local_low = True
        for j in range(max(0, i-10), min(len(df), i+10)):
            if j != i and df['Low'].iloc[i] >= df['Low'].iloc[j]:
                is_local_low = False
                break

        if is_local_low:
            # 計算前高點
            peak_price = df['High'].iloc[max(0, i-20):i].max()

            # 計算跌幅
            trough_price = df['Low'].iloc[i]
            drop = (peak_price - trough_price) / \
                peak_price if peak_price > 0 else 0

            if drop >= min_drop:
                swing_lows.append({
                    'date': df.index[i],
                    'trough_price': trough_price,
                    'peak_price': peak_price,
                    'drop_pct': drop * 100,
                    'VIX': df['VIX'].iloc[i],
                    'RSI': df['RSI'].iloc[i],
                    'ADL': df['ADL'].iloc[i]
                })

    return swing_lows


def calculate_indicators(df):
    """計算各種指標"""
    # 恐慌指數: VIX / RSI * 60
    df['Panic'] = (df['VIX'] / df['RSI'].replace(0, 1)) * 60

    # 貪婪指數: RSI / VIX * 15
    df['Greed'] = (df['RSI'] / df['VIX'].replace(0, 1)) * 15

    # PCR: (High-Close) / (Close-Low)
    hl_range = df['High'] - df['Low']
    hl_range = hl_range.replace(0, 0.01)
    bear = (df['High'] - df['Close']).clip(lower=0)
    bull = (df['Close'] - df['Low']).clip(lower=hl_range * 0.01)
    df['PCR'] = bear / bull

    # ADL z-score (60日)
    window = 60
    df['ADL_z'] = (df['ADL'] - df['ADL'].rolling(window).mean()
                   ) / df['ADL'].rolling(window).std()

    return df


def analyze_swing_lows(df, name):
    """分析波段低點的指標特性"""
    print(f"\n{'='*60}")
    print(f"  {name} 波段低點指標分析")
    print(f"{'='*60}")

    swing_lows = find_swing_lows(df)
    print(f"\n找到 {len(swing_lows)} 個波段低點（跌幅 > 8%）")

    if len(swing_lows) == 0:
        print("未找到波段低點")
        return

    # 轉為 DataFrame
    lows_data = pd.DataFrame(swing_lows)

    # 計算衍生指標
    df = calculate_indicators(df.copy())

    # 添加衍生指標到低點數據
    panic_vals = []
    greed_vals = []
    pcr_vals = []
    adl_z_vals = []

    for sl in swing_lows:
        date = sl['date']
        if date in df.index:
            panic_vals.append(df.loc[date, 'Panic'])
            greed_vals.append(df.loc[date, 'Greed'])
            pcr_vals.append(df.loc[date, 'PCR'])
            adl_z_vals.append(df.loc[date, 'ADL_z'])
        else:
            panic_vals.append(None)
            greed_vals.append(None)
            pcr_vals.append(None)
            adl_z_vals.append(None)

    lows_data['Panic'] = panic_vals
    lows_data['Greed'] = greed_vals
    lows_data['PCR'] = pcr_vals
    lows_data['ADL_z'] = adl_z_vals

    # 計算低點前后的指標平均值
    print("\n" + "─" * 60)
    print("【波段低點時的指標數值統計】")
    print("─" * 60)

    for col in ['VIX', 'RSI', 'ADL']:
        if col in lows_data.columns:
            valid = lows_data[col].dropna()
            if len(valid) > 0:
                print(f"\n{col}:")
                print(f"  平均值: {valid.mean():.2f}")
                print(f"  中位數: {valid.median():.2f}")
                print(f"  最小值: {valid.min():.2f}")
                print(f"  最大值: {valid.max():.2f}")
                print(f"  標準差: {valid.std():.2f}")

    print("\n" + "─" * 60)
    print("【衍生指標數值統計】")
    print("─" * 60)

    for col in ['Panic', 'Greed', 'PCR', 'ADL_z']:
        valid_data = lows_data[col].dropna()
        if len(valid_data) > 0:
            print(f"\n{col}:")
            print(f"  平均值: {valid_data.mean():.2f}")
            print(f"  中位數: {valid_data.median():.2f}")
            print(f"  最小值: {valid_data.min():.2f}")
            print(f"  最大值: {valid_data.max():.2f}")

    # 分析低點前后指標變化
    print("\n" + "─" * 60)
    print("【低點前 5 日 → 低點當日 → 低點后 5 日 指標變化】")
    print("─" * 60)

    for col in ['VIX', 'RSI', 'Panic', 'Greed']:
        before = []
        at_low = []
        after = []

        for sl in swing_lows:
            idx_list = df.index.get_indexer_for([sl['date']])
            if idx_list[0] >= 0:
                idx = idx_list[0]
                # 前 5 日
                if idx >= 5:
                    before.append(df[col].iloc[idx-5:idx].mean())
                # 后 5 日
                if idx + 5 < len(df):
                    after.append(df[col].iloc[idx+1:idx+6].mean())
                at_low.append(df[col].iloc[idx])

        if before and at_low and after:
            print(f"\n{col}:")
            print(f"  低點前 5 日平均: {sum(before)/len(before):.2f}")
            print(f"  低點當日平均:   {sum(at_low)/len(at_low):.2f}")
            print(f"  低點后 5 日平均: {sum(after)/len(after):.2f}")

    # 列出重大波段低點
    print("\n" + "─" * 60)
    print("【重大波段低點詳情（跌幅 > 15%）】")
    print("─" * 60)

    major_lows = lows_data[lows_data['drop_pct'] >
                           15].sort_values('drop_pct', ascending=False)
    for _, row in major_lows.head(10).iterrows():
        print(f"\n日期: {row['date'].strftime('%Y-%m-%d')}")
        print(f"  跌幅: {row['drop_pct']:.1f}%")
        print(f"  VIX: {row['VIX']:.2f}")
        print(f"  RSI: {row['RSI']:.2f}")
        if pd.notna(row.get('Panic')):
            print(f"  Panic: {row['Panic']:.1f}")
        if pd.notna(row.get('Greed')):
            print(f"  Greed: {row['Greed']:.1f}")


# 執行分析
print("=" * 60)
print("  波段低點指標特性深度研究")
print("  研究日期: " + datetime.now().strftime('%Y-%m-%d'))
print("=" * 60)

# 台灣加權
df_twii = parse_data(twii_data)
analyze_swing_lows(df_twii, "台灣加權指數 (TWII)")

# 那斯達克
df_nasdaq = parse_data(nasdaq_data)
analyze_swing_lows(df_nasdaq, "那斯達克指數 (NASDAQ)")

# 總結
print("\n" + "=" * 60)
print("  【研究結論摘要】")
print("=" * 60)
print("""
1. VIX (恐慌指數)
   - 波段低點時 VIX 通常較高（投資人恐慌）
   - 低點后 VIX 往往開始下降（恐慌緩解）
   - 重大股災時 VIX 可飆升至 80 以上

2. RSI (相對強弱指數)
   - 波段低點時 RSI 通常低於 30（超賣）
   - 嚴重股災時 RSI 可能跌破 20
   - 低點后 RSI 往往反彈回升

3. 恐慌抄底指數 (Panic = VIX/RSI * 60)
   - 低點時此指數飆高（>50 表示恐慌）
   - >90 為百年鑽石底訊號
   - 此指數從高點回落時是最佳買點

4. 貪婪逃頂指數 (Greed = RSI/VIX * 15)
   - 低點時此指數極低（<30 表示恐懼）
   - 低點后隨價格反彈而回升

5. ADL 資金流向
   - 波段低點時常出現負值（資金流出）
   - 多頭背離時 ADL 負值收斂是買入訊號

6. PCR (收盤位置比)
   - 低點時 PCR > 2.0（賣壓主導）
   - PCR 從高點回落是恐慌退潮訊號
""")
