# -*- coding: utf-8 -*-
"""
Compute daily spreads from raw data.
Run: python scripts/compute_spreads.py
Input:  data/raw/reits_daily.csv, data/raw/bond_yields_daily.csv
Output: data/processed/spreads_daily.csv, data/processed/spread_B_daily.csv
"""
import pandas as pd
import numpy as np
import os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(REPO, 'data', 'raw')
PROC = os.path.join(REPO, 'data', 'processed')
os.makedirs(PROC, exist_ok=True)

# ============================================================
# Per-share distributable amounts (fixed numerator, from prospectus)
# These change only when iFinD updates predictions. Update manually when needed.
# ============================================================
PER_SHARE = {
    '180501.SZ': 0.0953,  '180502.SZ': 0.1134, '180503.SZ': 0.0858,
    '508031.SH': 0.1280,  '508055.SH': 0.1020, '508058.SH': 0.1190,
    '508068.SH': 0.1496,  '508077.SH': 0.1011, '508085.SH': 0.0758,
}
SHARES_WAN = {
    '180501.SZ': 50000, '180502.SZ': 50000, '180503.SZ': 40000,
    '508031.SH': 100000, '508055.SH': 50000, '508058.SH': 50000,
    '508068.SH': 50000, '508077.SH': 50000, '508085.SH': 50000,
}

# ============================================================
# Load raw data
# ============================================================
reits = pd.read_csv(os.path.join(RAW, 'reits_daily.csv'), parse_dates=['date'])
bonds = pd.read_csv(os.path.join(RAW, 'bond_yields_daily.csv'), parse_dates=['date'])

# ============================================================
# Compute daily yield and spread A
# ============================================================
reits['per_share_amount'] = reits['code'].map(PER_SHARE)
reits['daily_yield'] = reits['per_share_amount'] / reits['close']
reits['market_cap'] = reits['close'] * reits['code'].map(SHARES_WAN) * 10000

# Merge bond yields
result = []
for code in reits['code'].unique():
    sub = reits[reits['code'] == code].copy()
    sub = sub.merge(bonds[['date', 'yield_10y', 'yield_30y']], on='date', how='left')
    sub['yield_10y'] = sub['yield_10y'].ffill()
    sub['yield_30y'] = sub['yield_30y'].ffill()
    result.append(sub)

full = pd.concat(result, ignore_index=True)

# Spread A = daily_yield (%) - bond yield (%)
full['spread_A_10y'] = full['daily_yield'] * 100 - full['yield_10y']
full['spread_A_30y'] = full['daily_yield'] * 100 - full['yield_30y']

# Phase labels
def assign_phase(d):
    if d <= pd.Timestamp('2022-09-30'):
        return 'phase1_warming'
    elif d <= pd.Timestamp('2024-01-31'):
        return 'phase2_correction'
    else:
        return 'phase3_rational'
full['phase'] = full['date'].apply(assign_phase)

# Save
cols = ['date', 'code', 'name', 'group', 'close', 'volume',
        'per_share_amount', 'daily_yield', 'yield_10y', 'yield_30y',
        'spread_A_10y', 'spread_A_30y', 'market_cap', 'phase']
full[cols].to_csv(os.path.join(PROC, 'spreads_daily.csv'), index=False, encoding='utf-8-sig')
print(f'spreads_daily.csv: {len(full)} rows, {full["date"].min().date()} ~ {full["date"].max().date()}')

# ============================================================
# Compute spread B (A组 - B组 weighted average yield)
# ============================================================
A_codes = ['508031.SH', '508077.SH', '508055.SH', '180502.SZ']
B_codes = ['508068.SH', '180501.SZ', '508058.SH', '508085.SH', '180503.SZ']

mv_A = full[full['code'].isin(A_codes)].groupby('date').apply(
    lambda g: np.average(g['daily_yield'], weights=g['market_cap']), include_groups=False)
mv_B = full[full['code'].isin(B_codes)].groupby('date').apply(
    lambda g: np.average(g['daily_yield'], weights=g['market_cap']), include_groups=False)

sb = pd.DataFrame({'A': mv_A, 'B': mv_B})
sb['spread_B'] = sb['A'] - sb['B']
sb.to_csv(os.path.join(PROC, 'spread_B_daily.csv'), encoding='utf-8-sig')
print(f'spread_B_daily.csv: {len(sb)} rows')

# ============================================================
# Quick summary
# ============================================================
latest = full[full['date'] == full['date'].max()]
print(f'\nLatest spreads ({full["date"].max().date()}):')
for _, r in latest.iterrows():
    pct = (full[full['code'] == r['code']]['spread_A_10y'] < r['spread_A_10y']).mean() * 100
    print(f'  {r["code"]} {r["name"][:15]:15s} {r["group"]}  spread={r["spread_A_10y"]:.2f}pp  pct={pct:.0f}%')
print(f'  10Y bond: {latest["yield_10y"].iloc[0]:.2f}%')
