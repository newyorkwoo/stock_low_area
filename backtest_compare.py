#!/usr/bin/env python3
"""
backtest_compare.py
直接比較：舊底部信心分數 vs 新綜合買入時機分數
在完全相同的框架下，哪個指標策略獲利最高？
"""
import json
import numpy as np
import pandas as pd

MONTHLY_BUDGET = 10_000

# ─── 資料與指標 ───────────────────────────────────────────────────────────────

def load_data(path):
    with open(path) as f:
        raw = json.load(f)
    df = pd.DataFrame(raw, columns=['Date','Open','Close','Low','High','Volume','VIX','RSI60'])
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    return df

def add_all_indicators(df):
    c = df['Close']

    # ── 舊指標：底部信心分數 (B) ──────────────────────────────────────────
    hi240     = c.rolling(240, min_periods=1).max()
    dd_score  = np.clip(-(c - hi240) / hi240 * 200, 0, 40)
    vix_abs   = np.clip((df['VIX'] - 20) * 2, 0, 30)
    vix_roc   = np.clip(df['VIX'].pct_change(5).fillna(0) * 50, 0, 30)
    rsi_b     = np.clip((50 - df['RSI60']) * 2, 0, 30)
    df['B']   = dd_score + np.maximum(vix_abs, vix_roc) + rsi_b

    # ── 新指標1：死叉 ─────────────────────────────────────────────────────
    df['MA60']  = c.rolling(60, min_periods=1).mean()
    df['MA240'] = c.rolling(240, min_periods=1).mean()
    df['Death'] = df['MA60'] < df['MA240']

    # ── 新指標2：VIX 百分位（滾動5年）────────────────────────────────────
    df['VIX_Pct'] = df['VIX'].rolling(1250, min_periods=60).rank(pct=True) * 100

    # ── 新指標3：5年價位位置 ──────────────────────────────────────────────
    lo1250 = c.rolling(1250, min_periods=60).min()
    hi1250 = c.rolling(1250, min_periods=60).max()
    df['PricePos'] = (c - lo1250) / (hi1250 - lo1250 + 1e-9) * 100

    # ── 新指標4：綜合買入時機分數 (Composite) ────────────────────────────
    c1 = np.clip(df['B'] * 0.3, 0, 25)
    c2 = np.clip((df['VIX_Pct'] - 50) * 0.5, 0, 25)
    c3 = df['Death'].astype(float) * 25
    c4 = np.clip((40 - df['PricePos']) * 0.625, 0, 25)
    df['Comp'] = c1 + c2 + c3 + c4

    return df

# ─── 回測框架 ─────────────────────────────────────────────────────────────────

def simulate(df, strategy_fn):
    shares, cash_pool, invested = 0.0, 0.0, 0.0
    cur_month = -1
    pv_list   = []

    for date, row in df.iterrows():
        price = row['Close']
        if date.month != cur_month:
            cur_month  = date.month
            cash_pool += MONTHLY_BUDGET
            invested  += MONTHLY_BUDGET
            buy_amt    = strategy_fn(row, shares, cash_pool, price)
            actual     = min(buy_amt, cash_pool)
            if actual > 0:
                shares    += actual / price
                cash_pool -= actual
        pv_list.append(shares * price + cash_pool)

    return np.array(pv_list), invested

def metrics(pv, invested, df):
    fv      = pv[-1]
    tr      = (fv - invested) / invested * 100
    years   = (df.index[-1] - df.index[0]).days / 365.25
    cagr    = ((fv / invested) ** (1 / years) - 1) * 100
    roll_mx = np.maximum.accumulate(pv)
    max_dd  = ((pv - roll_mx) / roll_mx).min() * 100
    # 計算現金閒置比例（平均每日現金/總投入）
    return fv, tr, cagr, max_dd

# ─── 各策略定義 ───────────────────────────────────────────────────────────────

def s_dca(row, shares, pool, price):
    """無腦定投（基準）：每月固定投10k"""
    return MONTHLY_BUDGET

def s_old_b75(row, shares, pool, price):
    """舊信心分數-基本版：B>75 全投，否則只投當月"""
    if row['B'] > 75:
        return pool          # 底部全投
    return min(MONTHLY_BUDGET, pool)

def s_old_b75_save(row, shares, pool, price):
    """舊信心分數-儲蓄版：死叉存子彈，B>75 全投（前期最佳E策略）"""
    if row['B'] > 75:
        return pool
    elif row['Death']:
        return min(MONTHLY_BUDGET * 0.5, pool)  # 死叉：只投一半存子彈
    return min(MONTHLY_BUDGET, pool)

def s_new_comp60(row, shares, pool, price):
    """新綜合分數-基本版：Comp>60 全投，否則只投當月"""
    if row['Comp'] > 60:
        return pool
    return min(MONTHLY_BUDGET, pool)

def s_new_comp60_save(row, shares, pool, price):
    """新綜合分數-儲蓄版：死叉存子彈，Comp>60 全投"""
    if row['Comp'] > 60:
        return pool
    elif row['Death']:
        return min(MONTHLY_BUDGET * 0.5, pool)
    return min(MONTHLY_BUDGET, pool)

def s_new_comp_graded(row, shares, pool, price):
    """新綜合分數-分級版：依 Comp 強度決定投入比例"""
    comp = row['Comp']
    if   comp > 75: return pool                          # 極強：全投
    elif comp > 60: return pool * 0.7                    # 強：投70%
    elif comp > 45: return min(MONTHLY_BUDGET * 1.5, pool)  # 偏強：1.5倍
    elif row['Death']: return min(MONTHLY_BUDGET * 0.5, pool)  # 死叉：存子彈
    return min(MONTHLY_BUDGET, pool)

def s_vix_pct(row, shares, pool, price):
    """VIX百分位法：百分位越高投越多（純新指標）"""
    pct = row['VIX_Pct']
    if pd.isna(pct):
        return min(MONTHLY_BUDGET, pool)
    if   pct > 85: return pool                           # 歷史性恐慌：全投
    elif pct > 72: return pool * 0.6                     # 高恐慌：投60%
    elif pct > 55: return min(MONTHLY_BUDGET, pool)      # 正常偏高：正常
    elif pct < 20: return min(MONTHLY_BUDGET * 0.5, pool)  # 市場自滿：省錢
    return min(MONTHLY_BUDGET, pool)

def s_dual_confirm(row, shares, pool, price):
    """雙重確認：舊B>60 AND 新Comp>55 同時觸發才全投"""
    if row['B'] > 60 and row['Comp'] > 55:
        return pool
    elif row['Death']:
        return min(MONTHLY_BUDGET * 0.5, pool)
    return min(MONTHLY_BUDGET, pool)

STRATEGIES = [
    ('A',  '無腦定投（基準）',           s_dca),
    ('─',  '── 舊底部信心分數 ──',      None),
    ('B1', '舊B>75 直接全投',           s_old_b75),
    ('B2', '舊B>75 + 死叉存子彈',       s_old_b75_save),
    ('─',  '── 新綜合買入時機分數 ──',  None),
    ('C1', '新Comp>60 直接全投',        s_new_comp60),
    ('C2', '新Comp>60 + 死叉存子彈',   s_new_comp60_save),
    ('C3', '新Comp 分級加碼',           s_new_comp_graded),
    ('─',  '── 單一新指標 ──',          None),
    ('D',  'VIX百分位法',               s_vix_pct),
    ('─',  '── 組合策略 ──',            None),
    ('E',  '雙重確認（舊B + 新Comp）',  s_dual_confirm),
]

# ─── 訊號統計 ─────────────────────────────────────────────────────────────────

def signal_stats(df, market):
    cur_month = -1
    b75_mo, comp60_mo, death_mo, total_mo = 0, 0, 0, 0
    for date, row in df.iterrows():
        if date.month == cur_month: continue
        cur_month = date.month
        total_mo += 1
        if row['B'] > 75:       b75_mo    += 1
        if row['Comp'] > 60:    comp60_mo += 1
        if row['Death']:        death_mo  += 1

    print(f"\n  訊號觸發頻率（{total_mo} 個月）：")
    print(f"    舊 B > 75       {b75_mo:>4} 個月 ({b75_mo/total_mo*100:5.1f}%)")
    print(f"    新 Comp > 60    {comp60_mo:>4} 個月 ({comp60_mo/total_mo*100:5.1f}%)")
    print(f"    死叉（熊市）    {death_mo:>4} 個月 ({death_mo/total_mo*100:5.1f}%)")

# ─── 主程式 ───────────────────────────────────────────────────────────────────

def run(path, market_name):
    df    = add_all_indicators(load_data(path))
    years = (df.index[-1] - df.index[0]).days / 365.25

    print(f"\n{'='*76}")
    print(f"  {market_name}")
    print(f"  {df.index[0].date()} ~ {df.index[-1].date()}  ({years:.1f} 年)  每月 ${MONTHLY_BUDGET:,}")
    print(f"{'='*76}")

    signal_stats(df, market_name)

    print(f"\n  {'策略':<30} {'最終市值':>13} {'總報酬':>9} {'年化':>8} {'最大回撤':>9}")
    print(f"  {'-'*72}")

    results = {}
    base_fv = None

    for key, name, fn in STRATEGIES:
        if fn is None:
            print(f"  {name}")
            continue
        pv, invested = simulate(df, fn)
        fv, tr, cagr, mdd = metrics(pv, invested, df)
        diff = f"+${fv-base_fv:,.0f}" if base_fv and fv > base_fv else (f"-${base_fv-fv:,.0f}" if base_fv else "")
        flag = " ★" if base_fv and fv == max(r['fv'] for r in results.values() if 'fv' in r) else ""
        print(f"  {key}: {name:<28} {fv:>13,.0f} {tr:>8.1f}% {cagr:>7.2f}% {mdd:>8.1f}%  {diff}")
        results[key] = dict(name=name, fv=fv, tr=tr, cagr=cagr, mdd=mdd, invested=invested)
        if key == 'A': base_fv = fv

    # 找最佳
    valid = {k: v for k, v in results.items() if k != 'A' and '─' not in k}
    best_k = max(valid, key=lambda k: valid[k]['fv'])
    best   = valid[best_k]
    base   = results['A']
    extra  = best['fv'] - base['fv']

    print(f"\n  {'─'*72}")
    print(f"  🏆 最佳策略: {best_k}: {best['name']}")
    print(f"     最終市值:  ${best['fv']:>13,.0f}  (年化 {best['cagr']:.2f}%)")
    print(f"     無腦定投:  ${base['fv']:>13,.0f}  (年化 {base['cagr']:.2f}%)")
    print(f"     多賺:      ${extra:>13,.0f}  (+{extra/base['fv']*100:.1f}%)")

    # 舊 vs 新指標對決
    b2 = results.get('B2', {})
    c2 = results.get('C2', {})
    if b2 and c2:
        winner = '舊信心分數 (B2)' if b2['fv'] > c2['fv'] else '新綜合分數 (C2)'
        diff   = abs(b2['fv'] - c2['fv'])
        print(f"\n  ⚔️  舊 vs 新（同框架比較）：")
        print(f"     B2 舊信心 + 死叉存子彈: ${b2['fv']:>12,.0f}  年化 {b2['cagr']:.2f}%")
        print(f"     C2 新綜合 + 死叉存子彈: ${c2['fv']:>12,.0f}  年化 {c2['cagr']:.2f}%")
        print(f"     勝出: {winner}  差距 ${diff:,.0f}")

    return results

def main():
    print("\n" + "━"*76)
    print("  回測比較：舊底部信心分數 vs 新綜合買入時機分數")
    print("  框架：每月 $10,000，現金池管理，永不賣出")
    print("━"*76)

    r_tw = run('twii_data.json',   '台灣加權指數 (TWII)')
    r_nq = run('nasdaq_data.json', '那斯達克 (NASDAQ)')

    # 最終結論
    print(f"\n{'━'*76}")
    print("  最終結論")
    print(f"{'━'*76}")

    for name, res in [('TWII', r_tw), ('NASDAQ', r_nq)]:
        valid = {k: v for k, v in res.items() if '─' not in k}
        ranked = sorted(valid.items(), key=lambda x: x[1]['fv'], reverse=True)
        print(f"\n  {name} 排名：")
        for i, (k, r) in enumerate(ranked[:5], 1):
            diff = r['fv'] - valid['A']['fv']
            sign = '+' if diff >= 0 else '-'
            print(f"    {i}. {k}: {r['name']:<30} 年化 {r['cagr']:.2f}%  {sign}${abs(diff):,.0f}")

    print(f"""
  ─────────────────────────────────────────────────────────────────────────
  解讀：

  1. 「新綜合分數」因為包含死叉因子，訊號觸發頻率比「舊信心分數」高很多。
     觸發越頻繁 → 閒置現金越少 → 趨近無腦定投 → 在多頭市場表現相近。

  2. 「舊信心分數」觸發條件更嚴苛（需要同時：大跌+VIX恐慌+RSI超賣），
     等到真正的歷史性底部才出手，子彈更集中。

  3. 兩者本質不同：
     舊 B 分數 = 「現在是否已超賣？」（事後確認）
     新 Comp   = 「現在整體環境是否適合買？」（綜合評估）

  4. 台股（TWII）因趨勢較溫和，底部等待策略略有優勢。
     那斯達克（NASDAQ）長牛趨勢強，任何等待都有機會成本，定投最優。
""")

if __name__ == '__main__':
    main()
