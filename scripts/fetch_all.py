# -*- coding: utf-8 -*-
"""
Fetch all raw data for 保障房REITs analysis.
Sources: Sina Finance, ChinaBond, AKShare.
Run: python scripts/fetch_all.py
Output: data/raw/*.csv (overwritten with latest full history)
"""
import requests, time, os, sys
import numpy as np
import pandas as pd
from io import StringIO

# ============================================================
# Setup
# ============================================================
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, 'data', 'raw')
os.makedirs(DATA, exist_ok=True)

if not hasattr(requests.Session, '_patched'):
    _orig = requests.Session.send
    def _patched(self, req, **kw):
        self.trust_env = False
        return _orig(self, req, **kw)
    requests.Session.send = _patched
    requests.Session._patched = True

SINA = 'https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData'
TODAY = pd.Timestamp.now().strftime('%Y%m%d')

# ============================================================
# 1. REITs Daily Prices (9 REITs)
# ============================================================
print(f'[{pd.Timestamp.now():%Y-%m-%d %H:%M}] Fetching REITs daily prices...')

REITS = [
    ('sh508031','508031.SH','国泰海通城投宽庭保租房REIT','A'),
    ('sh508077','508077.SH','华夏基金华润有巢REIT','A'),
    ('sh508055','508055.SH','汇添富上海地产租赁住房REIT','A'),
    ('sz180502','180502.SZ','招商基金蛇口租赁住房REIT','A'),
    ('sh508068','508068.SH','华夏北京保障房REIT','B'),
    ('sz180501','180501.SZ','红土创新深圳安居REIT','B'),
    ('sh508058','508058.SH','中金厦门安居REIT','B'),
    ('sh508085','508085.SH','华泰苏州恒泰租赁住房REIT','B'),
    ('sz180503','180503.SZ','中航北京昌保租赁住房REIT','B'),
]

all_reits = []
errors = []
for sina, code, name, group in REITS:
    try:
        r = requests.get(SINA, params={'symbol': sina, 'scale': '240', 'ma': 'no', 'datalen': '2000'}, timeout=15)
        data = r.json()
        if not data:
            errors.append(f'{code}: empty response')
            continue
        df = pd.DataFrame(data)
        df = df.rename(columns={'day': 'date', 'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close', 'volume': 'volume'})
        df['date'] = pd.to_datetime(df['date'])
        for c in ['open', 'high', 'low', 'close']:
            df[c] = pd.to_numeric(df[c], errors='coerce')
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
        df['amount'] = pd.NA
        df['code'] = code
        df['name'] = name
        df['group'] = group
        all_reits.append(df.sort_values('date'))
        print(f'  {code} {name[:12]:12s} {len(df):5d} rows  {df["date"].min().date()} ~ {df["date"].max().date()}')
    except Exception as e:
        errors.append(f'{code}: {e}')
    time.sleep(1.5)

if all_reits:
    out = pd.concat(all_reits, ignore_index=True)
    out = out[['date', 'code', 'name', 'group', 'open', 'high', 'low', 'close', 'volume', 'amount']]
    out = out.sort_values(['code', 'date']).reset_index(drop=True)
    out.to_csv(os.path.join(DATA, 'reits_daily.csv'), index=False, encoding='utf-8-sig')
    print(f'  Saved reits_daily.csv ({len(out)} rows, {out["code"].nunique()} REITs)')
else:
    errors.append('ALL REITs failed')

# ============================================================
# 2-4. Stock Indexes (CSI 300/500/1000)
# ============================================================
for name, symbol in [('沪深300', 'sh000300'), ('中证500', 'sh000905'), ('中证1000', 'sh000852')]:
    print(f'\n[{pd.Timestamp.now():%H:%M}] Fetching {name}...')
    time.sleep(1)
    try:
        r = requests.get(SINA, params={'symbol': symbol, 'scale': '240', 'ma': 'no', 'datalen': '3100'}, timeout=15)
        df = pd.DataFrame(r.json())
        df = df.rename(columns={'day': 'date', 'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close', 'volume': 'volume'})
        df['date'] = pd.to_datetime(df['date'])
        for c in ['open', 'high', 'low', 'close', 'volume']:
            df[c] = pd.to_numeric(df[c], errors='coerce')
        df['amount'] = pd.NA
        df = df.sort_values('date').reset_index(drop=True)
        idx = symbol.replace('sh000', '')
        fname = f'csi{idx}_daily.csv'
        df.to_csv(os.path.join(DATA, fname), index=False, encoding='utf-8-sig')
        print(f'  {fname}: {len(df)} rows, {df["date"].min().date()} ~ {df["date"].max().date()}')
    except Exception as e:
        errors.append(f'{name}: {e}')

# ============================================================
# 5. REITs Total Return Index (932047)
# ============================================================
print(f'\n[{pd.Timestamp.now():%H:%M}] Fetching REITs total return index...')
try:
    import akshare as ak
    df = ak.stock_zh_index_hist_csindex(symbol='932047', start_date='20210930', end_date=TODAY)
    df = df.rename(columns={'日期': 'date', '收盘': 'close'})
    df['date'] = pd.to_datetime(df['date'])
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    df = df[['date', 'close']].sort_values('date').reset_index(drop=True)
    df.to_csv(os.path.join(DATA, 'reits_index_932047.csv'), index=False, encoding='utf-8-sig')
    print(f'  reits_index_932047.csv: {len(df)} rows, {df["date"].min().date()} ~ {df["date"].max().date()}')
except Exception as e:
    errors.append(f'REITs index: {e}')

# ============================================================
# 6. ChinaBond Composite Wealth Index
# ============================================================
print(f'\n[{pd.Timestamp.now():%H:%M}] Fetching bond composite index...')
try:
    import akshare as ak
    df = ak.bond_new_composite_index_cbond()
    df = df.rename(columns={'date': 'date', 'value': 'close'})
    df['date'] = pd.to_datetime(df['date'])
    df = df[df['date'] >= '2022-08-01'].sort_values('date').reset_index(drop=True)
    df.to_csv(os.path.join(DATA, 'bond_index_daily.csv'), index=False, encoding='utf-8-sig')
    print(f'  bond_index_daily.csv: {len(df)} rows, {df["date"].min().date()} ~ {df["date"].max().date()}')
except Exception as e:
    errors.append(f'Bond index: {e}')

# ============================================================
# 7. Government Bond Yields (10Y/30Y)
# ============================================================
print(f'\n[{pd.Timestamp.now():%H:%M}] Fetching bond yields...')
try:
    url = 'https://yield.chinabond.com.cn/cbweb-pbc-web/pbc/historyQuery'
    frames = []
    end = pd.to_datetime(TODAY)
    stop = pd.to_datetime('2022-08-01')
    while end > stop:
        seg_start = max(stop, end - pd.DateOffset(years=1)).strftime('%Y-%m-%d')
        r = requests.get(url, params={
            'startDate': seg_start,
            'endDate': end.strftime('%Y-%m-%d'),
            'gjqx': '0', 'qxId': 'ycqx', 'locale': 'cn_ZH'
        }, timeout=20)
        dfs = pd.read_html(StringIO(r.text.replace('&nbsp', '')), header=0)
        if len(dfs) >= 2:
            frames.append(dfs[1])
        end = pd.to_datetime(seg_start) - pd.Timedelta(days=1)
        time.sleep(1)
    result = pd.concat(frames, ignore_index=True)
    result = result.rename(columns={'日期': 'date', '10年': 'yield_10y', '30年': 'yield_30y'})
    result['date'] = pd.to_datetime(result['date'], errors='coerce')
    result = result.dropna(subset=['date'])
    for c in ['yield_10y', 'yield_30y']:
        result[c] = pd.to_numeric(result[c], errors='coerce')
    result = result.drop_duplicates('date').sort_values('date').reset_index(drop=True)
    result[['date', 'yield_10y', 'yield_30y']].to_csv(
        os.path.join(DATA, 'bond_yields_daily.csv'), index=False, encoding='utf-8-sig')
    print(f'  bond_yields_daily.csv: {len(result)} rows, {result["date"].min().date()} ~ {result["date"].max().date()}')
except Exception as e:
    errors.append(f'Bond yields: {e}')

# ============================================================
# Summary
# ============================================================
print(f'\n[{"="*50}]')
print(f'Done at {pd.Timestamp.now():%Y-%m-%d %H:%M}')
if errors:
    print(f'ERRORS ({len(errors)}):')
    for e in errors:
        print(f'  - {e}')
    sys.exit(1)
else:
    print('All data sources refreshed successfully.')
    # Print file sizes
    for f in sorted(os.listdir(DATA)):
        if f.endswith('.csv'):
            sz = os.path.getsize(os.path.join(DATA, f)) / 1024
            print(f'  {f}: {sz:.0f} KB')
