#!/usr/bin/env python3
"""
research_strategy.py
每月 10,000 元，測試 5 種不同買賣策略，找出最大化獲利的方式。
"""
import json
import numpy as np
import pandas as pd

MONTHLY_BUDGET = 10_000

# ─── 資料載入 ────────────────────────────────────────────────────────────────

def load_data(path):
    with open(path) as f:
        raw = json.load(f)
    df = pd.DataFrame(raw, columns=['Date','Open','Close','Low','High','Volume','VIX','RSI60'])
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    return df

# ─── 評分 (與 index.html 一致) ───────────────────────────────────────────────

def add_scores(df):
    # --- 底部分數 ---
    hi240    = df['Close'].rolling(240, min_periods=1).max()
    dd_score = np.clip(-(df['Close'] - hi240) / hi240 * 200, 0, 40)
    vix_abs  = np.clip((df['VIX'] - 20) * 2, 0, 30)
    vix_roc  = np.clip(df['VIX'].pct_change(5).fillna(0) * 50, 0, 30)
    rsi_b    = np.clip((50 - df['RSI60']) * 2, 0, 30)
    df['B']  = dd_score + np.maximum(vix_abs, vix_roc) + rsi_b

    # --- 頂部分數 ---
    ma240      = df['Close'].rolling(240, min_periods=1).mean()
    dist240    = (df['Close'] - ma240) / ma240
    ma_score   = np.clip(dist240 * 200, 0, 40)
    vix_low    = np.clip((20 - df['VIX']) * 3, 0, 30)
    rsi_t      = np.clip((df['RSI60'] - 50) * 2, 0, 30)
    base_top   = ma_score + vix_low + rsi_t
    roc5       = df['Close'].pct_change(5).fillna(0)
    roc20      = df['Close'].pct_change(20).fillna(0)
    strong_mom = (roc5 > roc20 / 3) & (roc5 > 0.01)
    df['T']    = np.where(strong_mom, base_top * 0.7, base_top)
    return df

# ─── 通用模擬框架 ─────────────────────────────────────────────────────────────

def simulate(df, strategy_fn):
    """
    strategy_fn(b_score, t_score, shares, cash_pool, price)
        -> (buy_amount, sell_ratio)
    每月第一個交易日執行。cash 不計息。
    """
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

            buy_amt, sell_ratio = strategy_fn(
                row['B'], row['T'], shares, cash_pool, price
            )

            if sell_ratio > 0 and shares > 0:
                sold = shares * sell_ratio
                shares    -= sold
                cash_pool += sold * price
                trades.append(('S', date, price, sold * price))

            actual_buy = min(buy_amt, cash_pool)
            if actual_buy > 0:
                shares    += actual_buy / price
                cash_pool -= actual_buy
                trades.append(('B', date, price, actual_buy))

        pv_series.append(shares * price + cash_pool)

    return np.array(pv_series), invested, trades, cash_pool

def calc_metrics(pv, invested, df):
    fv       = pv[-1]
    total_r  = (fv - invested) / invested * 100
    years    = (df.index[-1] - df.index[0]).days / 365.25
    cagr     = ((fv / invested) ** (1 / years) - 1) * 100
    roll_max = np.maximum.accumulate(pv)
    max_dd   = ((pv - roll_max) / roll_max).min() * 100
    return fv, total_r, cagr, max_dd

# ─── 五種策略定義 ─────────────────────────────────────────────────────────────

def strat_a(b, t, shares, pool, price):
    """A: 無腦定投 ─ 每月固定投入，從不賣出"""
    return MONTHLY_BUDGET, 0.0

def strat_b(b, t, shares, pool, price):
    """B: 停買攻底 ─ 頂部不買存現金；底部把所有存款一次投入"""
    if t > 75:              return 0, 0.0         # 頂部：停買，現金積累
    elif b > 75:            return pool, 0.0       # 底部：全力一擊
    else:                   return MONTHLY_BUDGET, 0.0

def strat_c(b, t, shares, pool, price):
    """C: 高賣低買 ─ 頂部賣股累積現金；底部全力買回"""
    if t > 85:              return 0, 0.30         # 極端頂部：賣30% + 停買
    elif t > 75:            return 0, 0.20         # 頂部：賣20% + 停買
    elif b > 75:            return pool, 0.0       # 底部：全投
    else:                   return MONTHLY_BUDGET, 0.0

def strat_d(b, t, shares, pool, price):
    """D: 評分分級 ─ 依底部/頂部分數強度決定買賣力道"""
    if   t > 85:            return 0, 0.25         # 極端頂：賣25%
    elif t > 75:            return 0, 0.15         # 頂：賣15%
    elif b > 85:            return pool, 0.0       # 重大底：全投
    elif b > 75:            return pool * 0.60, 0.0  # 底：投60%現金池
    elif b > 60:            return MONTHLY_BUDGET * 1.5, 0.0  # 偏底：1.5倍
    else:                   return MONTHLY_BUDGET, 0.0

def strat_e(b, t, shares, pool, price):
    """E: 細水長流 ─ 平時只投一半蓄力；底部全力；頂部完全停買"""
    if t > 75:              return 0, 0.0          # 頂部：完全停買
    elif b > 75:            return pool, 0.0       # 底部：全力
    else:                   return MONTHLY_BUDGET * 0.5, 0.0  # 平時：存一半

# ─── 主分析流程 ───────────────────────────────────────────────────────────────

STRATS = [
    ('A', '無腦定投',     strat_a),
    ('B', '停買攻底',     strat_b),
    ('C', '高賣低買',     strat_c),
    ('D', '評分分級',     strat_d),
    ('E', '細水長流攻底', strat_e),
]

def zone_history(df, market_name):
    """印出歷史上各訊號區間"""
    in_bottom = in_top = False
    b_start = t_start = None
    b_periods, t_periods = [], []
    cur_month = -1

    for date, row in df.iterrows():
        if date.month == cur_month:
            continue
        cur_month = date.month

        if row['B'] > 75 and not in_bottom:
            in_bottom = True; b_start = date
        elif row['B'] <= 75 and in_bottom:
            in_bottom = False
            b_periods.append((b_start, date))

        if row['T'] > 75 and not in_top:
            in_top = True; t_start = date
        elif row['T'] <= 75 and in_top:
            in_top = False
            t_periods.append((t_start, date))

    if in_bottom: b_periods.append((b_start, df.index[-1]))
    if in_top:    t_periods.append((t_start, df.index[-1]))

    print(f"\n  📍 歷史底部區 (B>75) 共 {len(b_periods)} 次：")
    for s, e in b_periods:
        dur = (e - s).days
        print(f"     {s.strftime('%Y-%m')} ~ {e.strftime('%Y-%m')}  ({dur}天)")

    print(f"\n  📍 歷史頂部區 (T>75) 共 {len(t_periods)} 次：")
    for s, e in t_periods:
        dur = (e - s).days
        print(f"     {s.strftime('%Y-%m')} ~ {e.strftime('%Y-%m')}  ({dur}天)")

def run_all(path, market_name):
    df = add_scores(load_data(path))
    years = (df.index[-1] - df.index[0]).days / 365.25

    print(f"\n{'='*80}")
    print(f"  {market_name}")
    print(f"  回測期間: {df.index[0].date()} ~ {df.index[-1].date()}  ({years:.1f} 年)")
    print(f"{'='*80}")

    # 訊號分布
    bottom_m = top_m = neutral_m = 0
    cur_month = -1
    for date, row in df.iterrows():
        if date.month == cur_month: continue
        cur_month = date.month
        if   row['T'] > 75: top_m    += 1
        elif row['B'] > 75: bottom_m += 1
        else:               neutral_m += 1
    total_m = bottom_m + top_m + neutral_m
    print(f"\n  訊號分布 (共 {total_m} 個月):")
    print(f"    底部訊號月 {bottom_m:>3} 個 ({bottom_m/total_m*100:.0f}%)")
    print(f"    頂部訊號月 {top_m:>3} 個 ({top_m/total_m*100:.0f}%)")
    print(f"    平時月     {neutral_m:>3} 個 ({neutral_m/total_m*100:.0f}%)")

    zone_history(df, market_name)

    # 策略比較表
    print(f"\n  {'策略':<22} {'總投入':>10} {'最終市值':>13} {'總報酬':>9} {'年化報酬':>9} {'最大回撤':>9}  {'買/賣次數'}")
    print(f"  {'-'*82}")

    all_res = {}
    for key, name, fn in STRATS:
        pv, invested, trades, final_cash = simulate(df, fn)
        fv, tr, cagr, mdd = calc_metrics(pv, invested, df)
        n_b = sum(1 for t in trades if t[0] == 'B')
        n_s = sum(1 for t in trades if t[0] == 'S')
        label = f"{key}: {name}"
        print(f"  {label:<22} {invested:>10,.0f} {fv:>13,.0f} {tr:>8.1f}% {cagr:>8.1f}% {mdd:>8.1f}%  {n_b}買/{n_s}賣")
        all_res[key] = dict(name=name, fv=fv, invested=invested, tr=tr, cagr=cagr, mdd=mdd,
                            trades=trades, final_cash=final_cash)

    best_k  = max(all_res, key=lambda k: all_res[k]['fv'])
    best    = all_res[best_k]
    base    = all_res['A']
    extra   = best['fv'] - base['fv']

    print(f"\n  🏆 最佳策略: {best_k}: {best['name']}")
    print(f"     最終市值 ${best['fv']:,.0f}  vs 無腦定投 ${base['fv']:,.0f}")
    print(f"     多賺 ${extra:,.0f}  (+{extra/base['fv']*100:.1f}%)")
    print(f"     年化報酬 {best['cagr']:.2f}%  vs 無腦定投 {base['cagr']:.2f}%")

    # 最佳策略最近交易記錄
    buys  = [t for t in best['trades'] if t[0] == 'B']
    sells = [t for t in best['trades'] if t[0] == 'S']
    if buys:
        print(f"\n  📋 最近 5 次買入 ({best_k}):")
        for t in buys[-5:]:
            print(f"     {t[1].date()}  買入 ${t[3]:>10,.0f}")
    if sells:
        print(f"\n  📋 最近 5 次賣出 ({best_k}):")
        for t in sells[-5:]:
            print(f"     {t[1].date()}  賣出市值 ${t[3]:>10,.0f}")

    # 策略解析：各策略差距
    print(f"\n  📊 各策略 vs 無腦定投：")
    for k, r in all_res.items():
        diff = r['fv'] - base['fv']
        bar  = '█' * int(abs(diff) / max(abs(all_res[kk]['fv'] - base['fv']) for kk in all_res if kk != 'A') * 20 + 0.5) if diff != 0 else ''
        sign = '+' if diff >= 0 else '-'
        print(f"    {k}: {r['name']:<18} {sign}${abs(diff):>10,.0f}  {bar}")

    return all_res

def main():
    print("\n" + "━"*80)
    print("  每月 $10,000 最優買賣策略研究")
    print("━"*80)
    print("""
  策略說明：
  A: 無腦定投     — 每月固定買，從不賣出 (基準)
  B: 停買攻底     — 頂部(T>75)停買存錢；底部(B>75)把所有存款全投
  C: 高賣低買     — 頂部賣20-30%持股+停買；底部把全部現金押進去
  D: 評分分級     — 依分數強度分級操作：頂部賣15-25%；底部投60-100%現金
  E: 細水長流攻底 — 平時只投月預算的一半慢慢蓄力；底部全投；頂部停買
""")

    r_tw = run_all('twii_data.json',   '台灣加權指數 (TWII)')
    r_nq = run_all('nasdaq_data.json', '那斯達克 (NASDAQ)')

    # 綜合建議
    print(f"\n{'━'*80}")
    print("  綜合建議")
    print("━"*80)
    best_tw = max(r_tw, key=lambda k: r_tw[k]['fv'])
    best_nq = max(r_nq, key=lambda k: r_nq[k]['fv'])
    print(f"""
  TWII   最佳策略: {best_tw}: {r_tw[best_tw]['name']}  (年化 {r_tw[best_tw]['cagr']:.2f}%)
  NASDAQ 最佳策略: {best_nq}: {r_nq[best_nq]['name']}  (年化 {r_nq[best_nq]['cagr']:.2f}%)

  注意事項：
  · 現金持有期間不計息 (實際可放貨幣基金/高利活存 ~4%)
  · 頂部訊號不精確，過早賣出會錯失末升段漲幅
  · 底部訊號也有誤差，加碼後市場可能繼續跌
  · 建議：底部分批建倉（3~5次），頂部漸進減倉（每月賣一點）
""")

if __name__ == '__main__':
    main()
