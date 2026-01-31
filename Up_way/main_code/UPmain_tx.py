import akshare as ak
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import time


# 1. 获取股票代码
# 2. 获取股票数据
# 3. 处理数据


END_DATE = datetime.today().strftime("%Y%m%d")
START_DATE = "20240901"

UPWARD_longDate = 30
UPWARD_longDate_limitation = 25
UPWARD_shortDate = 7
UPWARD_shortDate_limitation = 7


class stock_upward:
    def __init__(self):
        self.start_date = START_DATE
        self.end_date = END_DATE

    @staticmethod
    def fitch_stock_code():
        data = pd.read_csv("20250303.csv", encoding="gbk")
        data["代码"] = data["代码tx"].astype(str).str.zfill(6)
        return data[["代码", "名称"]]

    def search_stock(self, stock_code):
        print(stock_code)

        try:
            stock_data = ak.stock_zh_a_hist_tx(
                symbol=stock_code,
                start_date=self.start_date,
                end_date=self.end_date,
                adjust="qfq",
            )
        except Exception as e:
            print(f"{stock_code} 获取失败")

        return stock_data

    @staticmethod
    def process_dataframe(stock_data):
        stock_data200 = stock_data.iloc[-100:].copy()
        # stock_data200["MA5"] = (
        #     stock_data["close"].rolling(window=5, min_periods=1).mean()
        # )

        # stock_data200["MA5_is_upward"] = (
        #     stock_data200["MA5"] < stock_data200["close"]
        # ).astype(int)
        # stock_data200["MA10"] = (
        #     stock_data200["close"].rolling(window=10, min_periods=1).mean()
        # )
        # stock_data200["MA10_is_upward"] = (
        #     stock_data200["MA10"] < stock_data200["close"]
        # ).astype(int)

        stock_data200["MA20"] = (
            stock_data200["close"].rolling(window=20, min_periods=1).mean()
        )
        stock_data200["MA20_is_upward"] = (
            stock_data200["MA20"] < stock_data200["close"]
        ).astype(int)

        stock_data200["MA30"] = (
            stock_data200["close"].rolling(window=30, min_periods=1).mean()
        )
        stock_data200["MA30_is_upward"] = (
            stock_data200["MA30"] < stock_data200["close"]
        ).astype(int)
        return stock_data200[
            [
                "date",
                "close",
                "MA30",
                "MA30_is_upward",
                "MA20",
                "MA20_is_upward",
            ]
        ]

    def rm_stop_and_down(self, stock_data):
        # 20日线向上
        if (
            stock_data["MA20_is_upward"].iloc[-UPWARD_longDate:].sum()
            < UPWARD_longDate_limitation
            or stock_data["MA20_is_upward"].iloc[-UPWARD_shortDate:].sum()
            < UPWARD_shortDate_limitation
        ):
            return False

        # 近期30交易日没有大幅度涨跌

        change_pct = (
            stock_data["close"].iloc[-20:].max() - stock_data["close"].iloc[-20:].min()
        ) / stock_data["close"].iloc[-20:].min()

        if change_pct > 0.6 or change_pct < 0.10:

            return False

        # 最近一天没有涨
        # if stock_data["涨跌幅"].iloc[-1,] < -8 or stock_data["涨跌幅"].iloc[-1,] > 9.8:
        #     return False
        self.change_pct = change_pct
        return True

    def run(self, stock):
        print(stock)
        code = stock[0]
        name = stock[1]
        # print(f"{code,name}")
        stock_data = self.search_stock(code)
        try:
            stock_data100 = self.process_dataframe(stock_data)
        except Exception as e:
            print(f"{e} 数据处理失败")

        if self.rm_stop_and_down(stock_data100):
            print(f"{code,name} 符合条件")

            with open("stock_upward.csv", "a+") as f:
                f.write(f"{code},{name},{self.change_pct}\n")
            return 0
        return 0


if __name__ == "__main__":
    start = time.time()
    stock = stock_upward()
    print("开始获取股代码")
    stock_code_Df = stock.fitch_stock_code()
    print("获取股代码完成")
    stock_list = list(zip(stock_code_Df["代码"], stock_code_Df["名称"]))
    print("开始获取股票数据")
    with open("stock_upward.csv", "a+") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"代码,名字,近期涨跌幅\n")
    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(stock.run, stock_list)

    print(f"耗时{time.time()-start}")
    

    # stock_individual_basic_info_xq_df = ak.stock_individual_basic_info_xq(
    #     symbol="SH601127"
    # )


# new_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
# open("stock_upward.csv", "a+").write(new_time + "\n")
# for i in range(len(stock_code["代码"])):
#     name = stock_code["名称"][i]
#     code = stock_code["代码"][i]

#     stock_data = stock.search_stock(stock_code["代码"][i])
#     try:
#         stock_data100 = stock.process_dataframe(stock_data)
#     except Exception as e:
#         print(f"{code,name} 数据处理失败")
#         continue
#     if stock.rm_stop_and_down(stock_data100):
#         print(f"{code,name} 符合条件")
#         open("stock_upward.csv", "a+").write(f"{code,name}\n")
#     else:
# print(f"{i}个")
