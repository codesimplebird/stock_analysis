from src_code import coreSearch as cs
import akshare as ak
import pandas as pd
from datetime import datetime

from concurrent.futures import ThreadPoolExecutor
import time


# 1. 获取股票代码
# 2. 获取股票数据
# 3. 处理数据
# 4. 判断是否符合条件 条件1 近期30交易日没有涨停板和跌5%的交易日 ,20日线向上


END_DATE = datetime.today().strftime("%Y%m%d")
START_DATE = "20240901"
RESULT_PATH = f"upward_result/{datetime.now().strftime('%Y%m%d')}.csv"

stockDATA_Sources = "stock_zh_a_spot_em.csv"
UPWARD_longDate = 30
UPWARD_longDate_limitation = 22
UPWARD_shortDate = 6
UPWARD_shortDate_limitation = 6

# -1 为前一天 None 为当天, RE_DATA 用于加减计算 re_date 切片计算
RE_DATA = 0
if RE_DATA == -1:
    re_date = -1
elif RE_DATA == 0:
    re_date = None


class stock_upward:
    def __init__(self):
        self.start_date = START_DATE
        self.end_date = END_DATE

    @staticmethod
    def fitch_stock_code():
        data = pd.read_csv(stockDATA_Sources, encoding="gbk")
        data["代码"] = data["代码"].astype(str).str.zfill(6)
        return data[["代码", "名称", "市盈率"]]

    def search_stock(self, stock_code):

        try:
            stock_data = cs.stock_zh_a_hist_zk(
                period="daily",
                symbol=stock_code,
                start_date=self.start_date,
                end_date=self.end_date,
                adjust="qfq",
            )
        except Exception as e:
            print(f",")

        return stock_data

    @staticmethod
    def process_dataframe(stock_data):
        stock_data200 = stock_data.iloc[-100:].copy()
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

        stock_data200["MA20"] = (
            stock_data200["收盘"].rolling(window=20, min_periods=1).mean()
        )
        stock_data200["MA20_is_upward"] = (
            stock_data200["MA20"] < stock_data200["收盘"]
        ).astype(int)

        stock_data200["MA30"] = (
            stock_data200["收盘"].rolling(window=30, min_periods=1).mean()
        )
        stock_data200["MA30_is_upward"] = (
            stock_data200["MA30"] < stock_data200["收盘"]
        ).astype(int)
        return stock_data200[
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

    def rm_stop_and_down(self, stock_data):
        # 20日线向上
        if (
            stock_data["MA20_is_upward"]
            .iloc[-UPWARD_longDate + RE_DATA : re_date]
            .sum()
            < UPWARD_longDate_limitation
            or stock_data["MA20_is_upward"]
            .iloc[-UPWARD_shortDate + RE_DATA : re_date]
            .sum()
            < UPWARD_shortDate_limitation
        ):
            return False

        # 近期30交易日没有大幅度涨跌
        change_pct_num = 20
        change_pct = (
            stock_data["收盘"].iloc[-change_pct_num:].max()
            - stock_data["收盘"].iloc[-change_pct_num:].min()
        ) / stock_data["收盘"].iloc[-change_pct_num:].min()

        if change_pct > 0.3 or change_pct < 0.15:

            return False

        # 最近一天没有涨跌扩大
        if (
            stock_data["涨跌幅"].iloc[-1 + RE_DATA : re_date].values[0] < -5
            or stock_data["涨跌幅"].iloc[-10 + RE_DATA : re_date].max() > 9
        ):

            return False
        down_pct = (
            stock_data["收盘"].iloc[-20:].max()
            - stock_data["收盘"].iloc[-1 + RE_DATA :].values[0]
        ) / stock_data["收盘"].iloc[-1 + RE_DATA :].values[0]
        up_pct = (
            stock_data["收盘"].iloc[-10:].min()
            - stock_data["收盘"].iloc[-1 + RE_DATA :].values[0]
        ) / stock_data["收盘"].iloc[-1 + RE_DATA :].values[0]
        # 最近20天没有大幅度下跌
        if down_pct > 0.05 or up_pct > 0.20:
            return False

        current_ZD = stock_data["涨跌幅"].iloc[-1:].values[0]
        return [True, change_pct, current_ZD]

    def run(self, stock):

        code = stock[0]
        name = stock[1]
        syl = stock[2]

        # print(f"{code,name}")
        stock_data = self.search_stock(code)

        try:
            stock_data100 = self.process_dataframe(stock_data)
        except Exception as e:
            print(f" 数据处理失败\n {e}")
            return 0
        process_Data = self.rm_stop_and_down(stock_data100)
        if isinstance(process_Data, list):
            stock_info = ak.stock_individual_info_em(symbol=code)
            hy_info = stock_info.values[6][1]
            print(f"{code,name} 符合条件")

            with open(RESULT_PATH, "a+") as f:
                f.write(
                    f"{code},{name},{process_Data[1]},{syl},{hy_info},{process_Data[2]}\n"
                )
            return 0
        else:
            pass
        return 0


if __name__ == "__main__":
    start = time.time()
    stock = stock_upward()
    print("开始获取股代码")
    stock_code_Df = stock.fitch_stock_code()
    print("获取股代码完成")
    stock_list = list(
        zip(stock_code_Df["代码"], stock_code_Df["名称"], stock_code_Df["市盈率"])
    )
    print("开始获取股票数据")
    with open(RESULT_PATH, "w") as f:

        f.write(
            f"代码,名字,近期涨跌幅,市盈率,行业,当日涨跌幅{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(stock.run, stock_list)

    print(f"耗时{time.time()-start}")
    import shutil

    try:
        shutil.copy(RESULT_PATH, "stock_upward.csv")
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
    # stock_upwards = stock_upward()
    # stock_data100 = stock_upwards.run(["000001", "平安银行"])
