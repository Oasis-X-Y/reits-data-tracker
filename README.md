# REITs Data Tracker

保障房REITs利差研究——自动化数据管道。

每天北京时间 9:00（周一至周五）自动拉取最新行情数据，计算利差序列。

## 数据源

| 数据 | 来源 | 更新频率 |
|------|------|:--:|
| 9只REITs日线行情 | 新浪财经 API | 每日 |
| 沪深300/中证500/中证1000 | 新浪财经 API | 每日 |
| REITs全收益指数 (932047) | 中证指数 (via AKShare) | 每日 |
| 中债新综合财富指数 | 中国债券信息网 (via AKShare) | 每日 |
| 10Y/30Y国债收益率 | 中国债券信息网 | 每日 |

## 目录

```
├ .github/workflows/daily-update.yml   # GitHub Actions 定时任务
├ scripts/
│   ├ fetch_all.py                     # 拉取所有原始数据
│   └ compute_spreads.py               # 计算利差序列
├ data/
│   ├ raw/                             # 原始行情 CSV
│   └ processed/                       # 利差序列 CSV
├ requirements.txt
└ README.md
```

## 本地使用

```bash
git clone <this-repo>
pip install -r requirements.txt

# 手动拉取最新数据
python scripts/fetch_all.py
python scripts/compute_spreads.py
```

## 最新数据

<!-- AUTO-UPDATE-MARKER -->
<!-- 由 GitHub Actions 自动更新 -->

