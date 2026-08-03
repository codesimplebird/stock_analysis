# 导入tushare
import os
import tushare as ts

# 初始化pro接口（token 从环境变量读取，避免硬编码泄露）
pro = ts.pro_api(os.environ.get("TS_TOKEN", ""))

# 拉取数据
df = pro.daily(
    **{
        "ts_code": 600584,
        "trade_date": "",
        "start_date": "",
        "end_date": "",
        "limit": "",
        "offset": "",
    },
    fields=[
        "ts_code",
        "trade_date",
        "open",
        "high",
        "low",
        "close",
        "pre_close",
        "change",
        "pct_chg",
        "vol",
        "amount",
    ]
)
print(df)
