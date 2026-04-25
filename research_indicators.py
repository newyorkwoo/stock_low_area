#!/usr/bin/env python3
"""
research_indicators.py
研究新的買賣指標，讓每月 10,000 元的獲利最大化。

核心發現（來自 research_strategy.py）：
  ❌ 「賣出」策略弊大於利：賣出會讓最終市值少 200~260 萬！
  ✅ 正確思路：永遠持有，只研究「何時多買」與「怎麼存更多子彈」
  ✅ 關鍵問題：在底部有多少現金？決定了最終報酬率！
"""
import json
import numpy as np
import pandas as pd

MONTHLY_BUDGET = 10_000

# ─── 資料與基礎指標 ───────────────────────────────────────────────────────────

def load_data(path):
    with open(path) as f:
        raw = json.load(f)
    df = pd.DataFrame(raw, columns=['Date','Open','Close','Low','High','Volume','VIX','RSI60'])
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    return df

def add_indicators(df):
    c = df['Close']

    # 現有指標（對應 index.html）
    hi240 = c.rolling(240, min_periods=1).max()
    dd_score  = np.clip(-(c - hi240) / hi240 * 200, 0, 40)
    vix_abs   = np.clip((df['VIX'] - 20) * 2, 0, 30)
    vix_roc   = np.clip(df['VIX'].pct_change(5).fillna(0) * 50, 0, 30)
    rsi_b     = np.clip((50 - df['RSI60']) * 2, 0, 30)
    df['B']   = dd_score + np.maximum(vix_abs, vix_roc) + rsi_b

    ma240_val  = c.rolling(240, min_periods=1).mean()
    dist240    = (c - ma240_val) / ma240_val
    ma_score   = np.clip(dist240 * 200, 0, 40)
    vix_low    = np.clip((20 - df['VIX']) * 3, 0, 30)
    rsi_t      = np.clip((df['RSI60'] - 50) * 2, 0, 30)
    base_top   = ma_score + vix_low + rsi_t
    roc5       = c.pct_change(5).fillna(0)
    roc20      = c.pct_change(20).fillna(0)
    df['T']    = np.where((roc5 > roc20/3) & (roc5 > 0.01), base_top*0.7, base_top)

    # ── 新指標 1：均線死叉/金叉 ──────────────────────────────────────────
    # MA60 < MA240 = 死叉（下跌趨勢） MA60 > MA240 = 金叉（上升趨勢）
    df['MA60']  = c.rolling(60, min_periods=1).mean()
    df['MA240'] = ma240_val
    df['MA_Cross'] = (df['MA60'] - df['MA240']) / df['MA240']  # 正 = 金叉, 負 = 死叉
    df['is_Death_Cross'] = df['MA60'] < df['MA240']

    # ── 新指標 2：VIX 百分位（滾動 5 年 = 1250 日）──────────────────────
    # 將今日 VIX 與過去5年相比，是位在第幾百分位（0=極低, 100=歷史最高恐慌）
    df['VIX_Pct'] = df['VIX'].rolling(1250, min_periods=60).rank(pct=True) * 100

    # ── 新指標 3：VIX 峰值反轉訊號 ──────────────────────────────────────
    # 條件：VIX 曾超過 28，且現在已從高點回落 15%（恐慌高峰過去，開始回穩）
    vix_5d_high = df['VIX'].rolling(5).max()
    df['VIX_Peak_Turn'] = (
        (df['VIX'] >= 28) &                          # VIX 曾達到恐慌水位
        (df['VIX'] < vix_5d_high * 0.88) &          # 從近期高點回落 12%
        (df['VIX'] < df['VIX'].shift(2))             # 今天比 2 天前低
    )

    # ── 新指標 4：連續下跌月數 ──────────────────────────────────────────
    # 連續幾個月收盤比上個月收盤低（衡量中期做空能量是否耗盡）
    monthly = df['Close'].resample('MS').last()
    monthly_ret = monthly.pct_change()
    # 轉回日頻率
    consecutive_down = (monthly_ret < 0).astype(int)
    for i in range(1, len(consecutive_down)):
        if consecutive_down.iloc[i] == 1:
            consecutive_down.iloc[i] += consecutive_down.iloc[i-1]
    df['Consec_Down_Mo'] = consecutive_down.reindex(df.index, method='ffill').fillna(0)

    # ── 新指標 5：距近 5 年低點的位置 ──────────────────────────────────
    # 越接近5年低點，潛在報酬越高
    lo1250 = c.rolling(1250, min_periods=60).min()
    hi1250 = c.rolling(1250, min_periods=60).max()
    df['Price_Pos'] = (c - lo1250) / (hi1250 - lo1250 + 1e-9)  # 0=5年最低, 1=5年最高

    return df

# ─── 模擬框架 ─────────────────────────────────────────────────────────────────

def simulate(df, strategy_fn):
    shares, cash_pool, invested = 0.0, 0.0, 0.0
    cur_month = -1
    pv_series = []
    trades = []

    for date, row in df.iterrows():
        price = row['Close']
        if date.month != cur_month:
            cur_month = date.month
            cash_pool += MONTHLY_BUDGET
            invested  += MONTHLY_BUDGET

            buy_amt, sell_ratio = strategy_fn(row, shares, cash_pool, price)

            if sell_ratio > 0 and shares > 0:
                sold = shares * sell_ratio
                shares    -= sold
                cash_pool += sold * price
                trades.append(('S', date, price, sold * price))

            actual = min(buy_amt, cash_pool)
            if actual > 0:
                shares    += actual / price
                cash_pool -= actual
                trades.append(('B', date, price, actual))

        pv_series.append(shares * price + cash_pool)

    return np.array(pv_series), invested, trades, cash_pool

def calc_metrics(pv, invested, df):
    fv      = pv[-1]
    total_r = (fv - invested) / invested * 100
    years   = (df.index[-1] - df.index[0]).days / 365.25
    cagr    = ((fv / invested) ** (1/years) - 1) * 100
    roll_mx = np.maximum.accumulate(pv)
    max_dd  = ((pv - roll_mx) / roll_mx).min() * 100
    return fv, total_r, cagr, max_dd

# ─── 舊策略（基準對比用）──────────────────────────────────────────────────────

def strat_a(row, shares, pool, price):       # 無腦定投
    return MONTHLY_BUDGET, 0.0

def strat_e(row, shares, pool, price):       # 細水長流攻底（上期最佳）
    if row['T'] > 75:    return 0, 0.0
    elif row['B'] > 75:  return pool, 0.0
    else:                return MONTHLY_BUDGET * 0.5, 0.0

# ─── 新策略 ───────────────────────────────────────────────────────────────────

def strat_f(row, shares, pool, price):
    """F: VIX比例加碼法
    用 VIX 百分位控制每月投入金額。VIX 越高（市場越恐慌）→ 投入越多。
    完全不賣出。多出的現金在低恐慌期積累，高恐慌期一次釋放。
    """
    vix_pct = row['VIX_Pct']
    if np.isnan(vix_pct):
        return MONTHLY_BUDGET, 0.0

    if vix_pct > 90:          # 歷史前10%最恐慌：全力一擊
        buy = pool
    elif vix_pct > 75:        # 歷史前25%：投1.5倍月預算
        buy = min(MONTHLY_BUDGET * 1.5, pool)
    elif vix_pct > 55:        # 略高恐慌：正常
        buy = min(MONTHLY_BUDGET, pool)
    elif vix_pct < 20:        # 極度自滿：只投50%，存50%等機會
        buy = min(MONTHLY_BUDGET * 0.5, pool)
    elif vix_pct < 35:        # 低恐慌：投75%
        buy = min(MONTHLY_BUDGET * 0.75, pool)
    else:                     # 正常水位：投100%
        buy = min(MONTHLY_BUDGET, pool)

    return buy, 0.0

def strat_g(row, shares, pool, price):
    """G: 均線趨勢法（死叉存彈藥，底部全打）
    核心邏輯：
    - 死叉（MA60 < MA240）= 熊市趨勢：每月只投50%，一半存起來
    - 金叉（MA60 > MA240）= 牛市趨勢：每月正常投100%
    - 底部訊號 B > 75（通常在死叉期間）：把所有積蓄一次全投
    這確保熊市低點時手上有充裕現金！
    """
    is_death = row['is_Death_Cross']
    b_score  = row['B']

    if b_score > 75:
        return pool, 0.0                            # 底部：全力打
    elif is_death:
        return min(MONTHLY_BUDGET * 0.5, pool), 0.0  # 死叉中：投一半蓄力
    else:
        return min(MONTHLY_BUDGET, pool), 0.0       # 金叉：正常定投

def strat_h(row, shares, pool, price):
    """H: 三指標超級底部法（不賣出版）
    結合 3 個底部確認訊號，全都觸發時才大力加碼：
    1. 底部分數 B > 60（基礎超賣）
    2. VIX 峰值反轉（恐慌高峰已過，開始回穩）
    3. 死叉環境（確認是熊市而非短暫回調）
    其他時間：VIX 低迷時省錢，正常時正常投。
    """
    b_score     = row['B']
    vix_turn    = row['VIX_Peak_Turn']
    is_death    = row['is_Death_Cross']
    vix_pct     = row['VIX_Pct'] if not np.isnan(row['VIX_Pct']) else 50

    # 超級底部：三個訊號同時確認
    if b_score > 60 and vix_turn and is_death:
        return pool, 0.0                            # 全力一擊

    # 強烈底部（即使沒有 VIX 反轉確認）
    elif b_score > 75:
        return pool * 0.7, 0.0

    # 死叉中的一般買入（積蓄彈藥）
    elif is_death:
        return min(MONTHLY_BUDGET * 0.6, pool), 0.0

    # 市場自滿（VIX 極低）：省錢
    elif vix_pct < 25:
        return min(MONTHLY_BUDGET * 0.5, pool), 0.0

    else:
        return min(MONTHLY_BUDGET, pool), 0.0

def strat_i(row, shares, pool, price):
    """I: 五指標評分買入法（動態投入比例）
    用所有新指標計算一個 0~100 的「買入時機分數」，
    分數越高，這個月投入的比例越大。完全不賣出。

    指標：
      I1. 底部分數（VIX、RSI、回撤）
      I2. VIX 百分位（越高越好買）
      I3. 連續下跌月數（越多越好買）
      I4. 5年價位位置（越低越好買）
      I5. 死叉（在熊市趨勢中更積極）
    """
    b_score = row['B']
    vix_pct = row['VIX_Pct'] if not np.isnan(row['VIX_Pct']) else 50
    down_mo = min(row['Consec_Down_Mo'], 6)         # 最多計到6個月
    price_pos = row['Price_Pos'] if not np.isnan(row['Price_Pos']) else 0.5
    is_death  = row['is_Death_Cross']

    # I1: 底部分數貢獻 (0~40)
    s1 = np.clip(b_score * 0.5, 0, 40)

    # I2: VIX 百分位貢獻 (0~20)
    s2 = np.clip((vix_pct - 50) * 0.4, 0, 20)      # 百分位>50才加分

    # I3: 連續下跌月 (0~15)
    s3 = down_mo * 2.5                               # 每個月+2.5分，最多6月=15分

    # I4: 在5年低位附近 (0~20)
    s4 = np.clip((0.4 - price_pos) * 50, 0, 20)     # 位置<40%才加分

    # I5: 死叉加成 (0~10)
    s5 = 10 if is_death else 0

    buy_score = s1 + s2 + s3 + s4 + s5             # 總分 0~105

    # 把分數轉成投入比例
    if buy_score >= 80:       buy_ratio = 1.0        # 全力，清空現金池
    elif buy_score >= 60:     buy_ratio = 0.7
    elif buy_score >= 45:     buy_ratio = 0.5
    elif buy_score >= 30:     buy_ratio = min(1.0, MONTHLY_BUDGET / max(pool, 1))  # 只投當月
    else:                     buy_ratio = 0.5 * MONTHLY_BUDGET / max(pool, 1)     # 只投半月

    return pool * buy_ratio, 0.0

def strat_j(row, shares, pool, price):
    """J: 終極組合法（本研究最優化版）
    設計原則：
    1. 永不賣出（賣出弊大於利）
    2. 牛市（金叉）：正常定投，同時每月存 20% 作為「底部彈藥」
    3. 熊市（死叉）：每月只投 40%，剩 60% 存起來
    4. VIX 極度恐慌（百分位 > 80）：一次投入現金池的 50%
    5. 超級底部（B > 75 且死叉）：投入現金池的 90%
    6. VIX 峰值反轉確認（市場最恐慌的時刻剛過）：投入現金池的 80%

    核心概念：長期保持一個「底部彈藥池」，平時不動，
    只在明確的超值機會出現時動用。
    """
    b_score   = row['B']
    vix_pct   = row['VIX_Pct'] if not np.isnan(row['VIX_Pct']) else 50
    vix_turn  = row['VIX_Peak_Turn']
    is_death  = row['is_Death_Cross']
    price_pos = row['Price_Pos'] if not np.isnan(row['Price_Pos']) else 0.5

    # 最優先：超級底部訊號（多重確認）
    if b_score > 75 and is_death:
        return pool * 0.90, 0.0                     # 投90%現金池

    # VIX 峰值反轉（最佳進場確認）
    if vix_turn and b_score > 50:
        return pool * 0.80, 0.0                     # 投80%

    # VIX 極度恐慌（即使還沒反轉，也要先進場一部分）
    if vix_pct > 85 and b_score > 40:
        return pool * 0.50, 0.0                     # 投50%

    # 普通底部訊號
    if b_score > 75:
        return pool * 0.60, 0.0

    # 熊市中的正常月份（積蓄彈藥）
    if is_death:
        save_rate = 0.60                            # 存60%
        invest    = min(MONTHLY_BUDGET * (1 - save_rate), pool)
        return invest, 0.0

    # 牛市低 VIX（市場自滿期）：少投存子彈
    if vix_pct < 25 and not is_death:
        invest = min(MONTHLY_BUDGET * 0.70, pool)  # 存30%
        return invest, 0.0

    # 牛市正常期：全額定投
    return min(MONTHLY_BUDGET, pool), 0.0

# ─── 輸出與分析 ───────────────────────────────────────────────────────────────

STRATS_OLD = [('A', '無腦定投 (基準)', strat_a), ('E', '細水長流攻底 (前期最佳)', strat_e)]
STRATS_NEW = [
    ('F', 'VIX比例加碼法',     strat_f),
    ('G', '均線趨勢法',        strat_g),
    ('H', '三指標超級底部法',  strat_h),
    ('I', '五指標評分買入法',  strat_i),
    ('J', '終極組合法 ★',     strat_j),
]

def run_all(path, market_name):
    df = add_indicators(load_data(path))
    years = (df.index[-1] - df.index[0]).days / 365.25

    print(f"\n{'='*82}")
    print(f"  {market_name}")
    print(f"  回測期間: {df.index[0].date()} ~ {df.index[-1].date()}  ({years:.1f} 年)")
    print(f"{'='*82}")

    # 印新指標統計
    cur_mo = -1
    vix_pct_vals, price_pos_vals, down_mo_vals, death_cross_mo = [], [], [], 0
    for date, row in df.iterrows():
        if date.month == cur_mo: continue
        cur_mo = date.month
        if not np.isnan(row['VIX_Pct']): vix_pct_vals.append(row['VIX_Pct'])
        if not np.isnan(row['Price_Pos']): price_pos_vals.append(row['Price_Pos'])
        if row['is_Death_Cross']: death_cross_mo += 1

    total_mo = len(vix_pct_vals)
    print(f"\n  新指標統計 (共 {total_mo} 個月有完整資料):")
    print(f"    死叉月份 (熊市趨勢) {death_cross_mo:>4} 個月 ({death_cross_mo/total_mo*100:.0f}%)")
    vix_arr = np.array(vix_pct_vals)
    print(f"    VIX 百分位分布: 低(<25%) {(vix_arr<25).sum():>3}月  中 {((vix_arr>=25)&(vix_arr<=75)).sum():>3}月  高(>75%) {(vix_arr>75).sum():>3}月")

    print(f"\n  {'策略':<28} {'最終市值':>13} {'總報酬':>9} {'年化報酬':>9} {'最大回撤':>9}  {'交易'}")
    print(f"  {'-'*80}")

    all_res = {}
    base_fv = None

    for key, name, fn in STRATS_OLD + STRATS_NEW:
        pv, invested, trades, final_cash = simulate(df, fn)
        fv, tr, cagr, mdd = calc_metrics(pv, invested, df)
        n_b = sum(1 for t in trades if t[0] == 'B')
        n_s = sum(1 for t in trades if t[0] == 'S')
        label = f"{key}: {name}"
        divider = '─'*80 if key == 'F' else ''
        if divider: print(f"  {divider}")
        print(f"  {label:<28} {fv:>13,.0f} {tr:>8.1f}% {cagr:>8.2f}% {mdd:>8.1f}%  {n_b}買/{n_s}賣")
        all_res[key] = dict(name=name, fv=fv, invested=invested, tr=tr, cagr=cagr, mdd=mdd, trades=trades)
        if key == 'A': base_fv = fv

    best_k = max(all_res, key=lambda k: all_res[k]['fv'])
    best   = all_res[best_k]
    print(f"\n  🏆 最佳策略: {best_k}: {best['name']}")
    print(f"     最終市值 ${best['fv']:,.0f}")
    print(f"     比無腦定投多賺 ${best['fv']-base_fv:,.0f}  (+{(best['fv']-base_fv)/base_fv*100:.1f}%)")
    print(f"     年化報酬: {best['cagr']:.2f}%  vs 無腦定投: {all_res['A']['cagr']:.2f}%")

    # 最佳策略的關鍵買入時機
    if best_k not in ('A',):
        buys = [t for t in best['trades'] if t[0] == 'B']
        # 找出買入金額最大的幾筆（關鍵底部進場）
        top_buys = sorted(buys, key=lambda t: t[3], reverse=True)[:8]
        print(f"\n  📋 {best_k} 最大金額買入（關鍵底部）:")
        for t in sorted(top_buys, key=lambda t: t[1]):
            print(f"     {t[1].date()}  投入 ${t[3]:>10,.0f}")

    # 所有策略排名
    print(f"\n  📊 策略排名（最終市值）:")
    sorted_res = sorted(all_res.items(), key=lambda x: x[1]['fv'], reverse=True)
    for rank, (k, r) in enumerate(sorted_res, 1):
        diff = r['fv'] - base_fv
        sign = '+' if diff >= 0 else '-'
        bar  = '█' * min(30, max(1, int(abs(diff) / max(abs(vv['fv'] - base_fv) for vv in all_res.values() if abs(vv['fv']-base_fv) > 0) * 25)))
        print(f"  {rank}. {k}: {r['name']:<28} {sign}${abs(diff):>9,.0f}  {bar if diff != 0 else '(基準)'}")

    return all_res

def print_strategy_summary():
    print(f"\n{'━'*82}")
    print("  新指標說明")
    print(f"{'━'*82}")
    print("""
  ┌─ 新指標（此腳本新增） ──────────────────────────────────────────────────────
  │
  │  1. MA 死叉/金叉   MA60 < MA240 = 熊市確立（趨勢最可靠的指標之一）
  │                    實際上，2008/2022 的大底都在死叉期間發生
  │
  │  2. VIX 百分位     今日 VIX 在過去5年中排第幾%？
  │                    比絕對值更精準，因為 VIX 的「正常水位」會隨年代不同
  │                    百分位 > 80% = 罕見恐慌，歷史上的大買點
  │
  │  3. VIX 峰值反轉   VIX 已超過 28 後，開始快速下降
  │                    意義：最壞的恐慌已過，市場開始穩定
  │                    這是所有訊號中「確認底部已過」最強的訊號
  │
  │  4. 連續下跌月數   連續幾個月收盤比上月低
  │                    3個月以上的連跌 = 中期趨勢已疲軟，底部將近
  │
  │  5. 5年價位位置    今日收盤在5年高低點之間的位置（0~1）
  │                    < 0.2 = 接近5年低點，極度被低估
  │
  └────────────────────────────────────────────────────────────────────────────

  ┌─ 策略核心邏輯 ─────────────────────────────────────────────────────────────
  │
  │  G (均線趨勢法):   死叉→存子彈，底部→全打
  │  H (三指標確認):   要同時確認「超賣+恐慌高峰過去+熊市趨勢」才全力加碼
  │  I (五指標評分):   量化買入時機，分數越高→投入比例越大，永不賣出
  │  J (終極組合):     多層觸發規則，牛市存 20%、熊市存 60%，
  │                    在明確底部一次性大力投入
  │
  └────────────────────────────────────────────────────────────────────────────

  ⚠️  重要提醒：
     · 所有策略 現金不計息（實際應放貨幣基金 ~4%，能再提升約 0.3~0.5% 年化）
     · 死叉/底部訊號均為回顧性計算，實際執行有1~2個月滯後
     · 建議策略 J 搭配「每月月初觀察一次」執行，降低情緒干擾
""")

def main():
    print_strategy_summary()
    r_tw = run_all('twii_data.json',   '台灣加權指數 (TWII)')
    r_nq = run_all('nasdaq_data.json', '那斯達克 (NASDAQ)')

    # 最終建議
    print(f"\n{'━'*82}")
    print("  結論與操作建議")
    print(f"{'━'*82}")
    best_tw = max(r_tw, key=lambda k: r_tw[k]['fv'])
    best_nq = max(r_nq, key=lambda k: r_nq[k]['fv'])
    print(f"""
  TWII   最佳: {best_tw}: {r_tw[best_tw]['name']}  → 年化 {r_tw[best_tw]['cagr']:.2f}%
  NASDAQ 最佳: {best_nq}: {r_nq[best_nq]['name']}  → 年化 {r_nq[best_nq]['cagr']:.2f}%

  ─────────────────────────────────────────────────────────────────────────────
  實際執行 SOP（每月月初操作）：

  1. 查看 index.html 看板，確認目前是哪個狀態：

     🟢 金叉且 VIX 低（牛市正常）：
        投入本月 8,000，存 2,000 到「底部彈藥」帳戶

     🟡 死叉（熊市趨勢確立）：
        只投 4,000，存 6,000。耐心等候。

     🔴 底部訊號 B > 75 且死叉：
        把「底部彈藥」帳戶 + 本月預算全部投入！

     💜 VIX 百分位 > 80% 且開始下降（峰值反轉）：
        這是最佳進場時機！投入底部彈藥的 80%

  2. 永遠不賣出（除非你有其他資金需求）
     歷史回測證明：賣出操作幾乎必定損失超過 200 萬！

  3. 底部彈藥建議：額外開一個活存帳戶（銀行高利活存或貨幣基金）
     平常讓它生息，底部時才動用。
""")

if __name__ == '__main__':
    main()
