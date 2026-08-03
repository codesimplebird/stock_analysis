# -*- coding: utf-8 -*-
# scanner.py
from src_code import coreSearch as cs
import akshare as ak
import pandas as pd
from datetime import datetime

from concurrent.futures import ThreadPoolExecutor
import time
import random
import os

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle

# 1. 获取股票代码
# 2. 获取股票数据
# 3. 处理数据
# 4. 判断是否符合条件 条件1 近期30交易日没有涨停板和跌5%的交易日, 20日线向上

# 项目根目录: strategies/upward_trend/
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(CURRENT_DIR, "data")
RESULT_DIR = os.path.join(DATA_DIR, "upward_result")

END_DATE = datetime.today().strftime("%Y%m%d")
START_DATE = "20250102"
RESULT_PATH = os.path.join(RESULT_DIR, f"{datetime.now().strftime('%Y%m%d')}.csv")

MAX_WORKERS = 10  # 最大线程数
STOCK_CSV_PATH = os.path.join(DATA_DIR, "stock_zh_a_spot_em.csv")

UPWARD_LONG_DAYS = 30
UPWARD_LONG_THRESHOLD = 23

UPWARD_SHORT_DAYS = 5
UPWARD_SHORT_THRESHOLD = 5

# -1 为前一天 None 为当天, DATA_OFFSET 用于加减计算 slice_end 切片计算
DATA_OFFSET = 0
if DATA_OFFSET == -1:
    slice_end = -1
elif DATA_OFFSET == 0:
    slice_end = None


class StockUpward:
    def __init__(self):
        self.start_date = START_DATE
        self.end_date = END_DATE

    @staticmethod
    def fetch_stock_code():
        data = pd.read_csv(STOCK_CSV_PATH, encoding="gbk")
        data["代码"] = data["代码"].astype(str).str.zfill(6)
        return data[["代码", "名称", "市盈率-动态"]]

    def search_stock(self, stock_code):
        try:
            stock_data = ak.stock_zh_a_hist(
                period="daily",
                symbol=stock_code,
                start_date=self.start_date,
                end_date=self.end_date,
                adjust="qfq",
                timeout=2,
            )
            return stock_data
        except Exception as e:
            print(f"{stock_code}从东财获取失败: {e}")
            return None

    @staticmethod
    def process_dataframe(stock_data):
        if stock_data is None or stock_data.empty:
            return None
        recent_data = stock_data.iloc[-100:].copy()
        # stock_data200["MA5"] = (
        #     stock_data["收盘"].rolling(window=5, min_periods=1).mean()
        # )

        # stock_data200["MA5_is_upward"] = (
        #     stock_data200["MA5"] < stock_data200["收盘"]
        # ).astype(int)
        # stock_data200["MA10"] = (
        #     stock_data200["收盘"].rolling(window=10, min_periods=1).mean()
        # )
        # stock_data200["MA10_is_upward"] = (
        #     stock_data200["MA10"] < stock_data200["收盘"]
        # ).astype(int)

        recent_data["MA20"] = (
            recent_data["收盘"].rolling(window=20, min_periods=1).mean()
        )
        recent_data["MA20_is_upward"] = (
            recent_data["MA20"] < recent_data["收盘"]
        ).astype(int)

        recent_data["MA30"] = (
            recent_data["收盘"].rolling(window=30, min_periods=1).mean()
        )
        recent_data["MA30_is_upward"] = (
            recent_data["MA30"] < recent_data["收盘"]
        ).astype(int)
        return recent_data[
            [
                "日期",
                "收盘",
                "涨跌幅",
                "MA30",
                "MA30_is_upward",
                "MA20",
                "MA20_is_upward",
            ]
        ]

    def check_criteria(self, stock_data):
        # 20日线向上
        if (
            stock_data["MA20_is_upward"]
            .iloc[-UPWARD_LONG_DAYS + DATA_OFFSET : slice_end]
            .sum()
            < UPWARD_LONG_THRESHOLD
            or stock_data["MA20_is_upward"]
            .iloc[-UPWARD_SHORT_DAYS + DATA_OFFSET : slice_end]
            .sum()
            < UPWARD_SHORT_THRESHOLD
        ):
            return False

        # 近期30交易日没有大幅度涨跌
        amplitude_ratio_20d = (
            stock_data["收盘"].iloc[-20:].max() - stock_data["收盘"].iloc[-20:].min()
        ) / stock_data["收盘"].iloc[-20:].min()

        if amplitude_ratio_20d > 0.25 or amplitude_ratio_20d < 0.05:
            return False

        # 最近一天没有涨跌扩大
        if (
            stock_data["涨跌幅"].iloc[-1 + DATA_OFFSET : slice_end].values[0] < -3
            or stock_data["涨跌幅"].iloc[-5 + DATA_OFFSET : slice_end].max() > 5
        ):
            return False

        # 近二十天最高价与现价不超过5%下跌
        # 近二十天最低价与现价不超过20%上涨
        max_drawdown = (
            stock_data["收盘"].iloc[-20:].max()
            - stock_data["收盘"].iloc[-1 + DATA_OFFSET :].values[0]
        ) / stock_data["收盘"].iloc[-1 + DATA_OFFSET :].values[0]
        max_upside = (
            stock_data["收盘"].iloc[-1 + DATA_OFFSET :].values[0]
            - stock_data["收盘"].iloc[-20:].min()
        ) / stock_data["收盘"].iloc[-1 + DATA_OFFSET :].values[0]
        # 最近20天没有大幅度下跌
        if max_drawdown > 0.05 or max_upside > 0.20:
            return False

        # 最近5天趋势向上
        peak_gap_5d = (
            stock_data["收盘"].iloc[-5:].max() - stock_data["收盘"].iloc[-1:].values[0]
        ) / stock_data["收盘"].iloc[-1:].values[0]
        if peak_gap_5d < 0.01 or peak_gap_5d > 0.10:
            return False

        # 最近一天价格为相对最高
        if (
            stock_data["收盘"].iloc[-1:].values[0]
            < stock_data["收盘"].iloc[-10:].max() * 0.97
        ):
            return False
        latest_change = stock_data["涨跌幅"].iloc[-1:].values[0]
        return [True, amplitude_ratio_20d, latest_change]

    @staticmethod
    def plot_kline(stock_data, stock_code, stock_name):
        save_dir = os.path.join(os.path.dirname(__file__), "kline_charts")
        os.makedirs(save_dir, exist_ok=True)

        df = stock_data.tail(130).copy()
        df["日期"] = pd.to_datetime(df["日期"])
        df["MA20"] = df["收盘"].rolling(window=20, min_periods=1).mean()

        fig, ax = plt.subplots(figsize=(16, 8))
        fig.patch.set_facecolor("#f0f0f0")
        ax.set_facecolor("#ffffff")

        dates = mdates.date2num(df["日期"].dt.date)
        candle_width = (dates[-1] - dates[0]) / len(dates) * 0.6

        for i in range(len(df)):
            o, c, h, l = (
                df["开盘"].iloc[i],
                df["收盘"].iloc[i],
                df["最高"].iloc[i],
                df["最低"].iloc[i],
            )
            d = dates[i]
            color = "#e74c3c" if c >= o else "#2ecc71"
            body_bottom = min(o, c)
            body_height = abs(c - o) or 0.01

            ax.add_patch(
                Rectangle(
                    (d - candle_width / 2, body_bottom),
                    candle_width,
                    body_height,
                    facecolor=color,
                    edgecolor=color,
                    linewidth=0.5,
                )
            )
            ax.plot([d, d], [l, h], color=color, linewidth=1.2)

        ax.plot(
            dates, df["MA20"], color="#0000ff", linewidth=1.8, label="MA20", zorder=3
        )

        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
        fig.autofmt_xdate(rotation=45)

        ax.set_title(
            f"{stock_code} {stock_name}  K线图", fontsize=16, fontweight="bold"
        )
        ax.set_ylabel("价格", fontsize=12)
        ax.grid(True, alpha=0.3, linestyle="--")
        ax.legend(fontsize=12, loc="upper left")

        file_path = os.path.join(save_dir, f"{stock_code}{stock_name}.png")
        plt.tight_layout()
        plt.savefig(file_path, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"  K线图已保存: {file_path}")

    def run(self, stock):
        time.sleep(random.uniform(0.1, 0.2))

        code = stock[0]
        name = stock[1]
        pe_ratio = stock[2]  # 市盈率
        index = stock[3]  # 索引

        # print(f"{code,name}")
        stock_data = self.search_stock(code)
        if stock_data is None or stock_data.empty:
            return 0

        with open(os.path.join(RESULT_DIR, "stop_code.txt"), "w") as f_code:
            f_code.write(str(index))
            f_code.close()
        try:
            processed_data = self.process_dataframe(stock_data)
        except Exception as e:
            print(f" 数据处理失败\n {e}")
            return 0
        if processed_data is None:
            return 0
        criteria_result = self.check_criteria(processed_data)
        if isinstance(criteria_result, list):
            self.plot_kline(stock_data, code, name)

            industry = "未知行业"
            print(f"{code},{name} 符合条件,行业:{industry},市盈率:{pe_ratio}")

            with open(RESULT_PATH, "a+") as f:
                f.write(
                    f"{code},{name},{criteria_result[1]},{pe_ratio},{industry},{criteria_result[2]},\n"
                )
            return 0
        else:
            pass  # print(f"{code,name} 不符合条件")
        return 0

    @staticmethod
    def load_checkpoint():
        try:
            with open(
                os.path.join(RESULT_DIR, "stop_code.txt"), "r", encoding="utf-8"
            ) as f:
                last_index = f.readlines()
                last_index = int(last_index[0].strip())
        except FileNotFoundError:
            last_index = 0

        if last_index > 3000:
            return 0
        return last_index


SEARCH_MODE = "eastMoney"
STOCK_CODE_LIST = []


if __name__ == "__main__":
    if SEARCH_MODE == "eastMoney":
        start = time.time()
        stock = StockUpward()

        last_index = stock.load_checkpoint()
        print("上次停止数为%s", last_index)
        all_stocks_df = stock.fetch_stock_code()
        stocks_df = all_stocks_df[last_index:]

        print("获取股代码完成")
        stock_list = list(
            zip(
                stocks_df["代码"],
                stocks_df["名称"],
                stocks_df["市盈率"],
                stocks_df.index,
            )
        )
    elif SEARCH_MODE == "custom":
        stock_list = list(
            zip(
                STOCK_CODE_LIST["代码"],
                0,
                0,
                0,
            )
        )
        print("获取股代码失败,请检查数据源")
        exit(0)

    print("开始获取股票数据,写入表头")
    with open(RESULT_PATH, "w") as f:
        f.write(
            f"代码,名字,近期涨跌幅,市盈率,行业,当日涨跌幅{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        executor.map(stock.run, stock_list)

    print(f"耗时{time.time() - start}")
    import shutil

    try:
        shutil.copy(RESULT_PATH, os.path.join(DATA_DIR, "stock_upward.csv"))
        print(f"文件已成功复制并重命名为 stock_upward.csv")
    except IOError as e:
        print(f"无法复制文件. 错误: {e}")

    # stock = cs.stock_zh_a_hist_zk(
    #     period="daily",
    #     symbol="000001",
    #     start_date="20240901",
    #     end_date="20250901",
    #     adjust="qfq",
    # )
    # stock_upwards = StockUpward()
    # stock_data100 = stock_upwards.run(["000001", "平安银行"])
