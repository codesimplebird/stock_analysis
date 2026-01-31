from src_code import coreSearch as cs
import akshare as ak
import pandas as pd
from datetime import datetime

from concurrent.futures import ThreadPoolExecutor
import time
import random


# 1. 获取股票代码
# 2. 获取股票数据
# 3. 处理数据
# 4. 判断是否符合条件 条件1 近期30交易日没有涨停板和跌5%的交易日 ,20日线向上


END_DATE = datetime.today().strftime("%Y%m%d")
START_DATE = "20250102"
RESULT_PATH = f"upward_result/{datetime.now().strftime('%Y%m%d')}.csv"


MAX_WORKERS = 10  # 最大线程数
stockDATA_Sources = "stock_zh_a_spot_em.csv"
UPWARD_longDate = 30
UPWARD_longDate_limitation = 23

UPWARD_shortDate = 5
UPWARD_shortDate_limitation = 5


average_line_str = "MA20_is_upward"
average_line_long = "MA20"

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
            stock_data = ak.stock_zh_a_hist(
                period="daily",
                symbol=stock_code,
                start_date=self.start_date,
                end_date=self.end_date,
                adjust="qfq",
                timeout=2,
            )
        except Exception as e:
            print(f"{stock_code}从东财获取失败")

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

        if change_pct > 0.25 or change_pct < 0.05:

            return False

        # 最近一天没有涨跌扩大
        if (
            stock_data["涨跌幅"].iloc[-1 + RE_DATA : re_date].values[0] < -3
            or stock_data["涨跌幅"].iloc[-5 + RE_DATA : re_date].max() > 5
        ):

            return False

        # 近二十天最高价与现价不超过5%下跌
        # 近二十天最低价与现价不超过20%上涨
        down_pct = (
            stock_data["收盘"].iloc[-20:].max()
            - stock_data["收盘"].iloc[-1 + RE_DATA :].values[0]
        ) / stock_data["收盘"].iloc[-1 + RE_DATA :].values[0]
        up_pct = (
            stock_data["收盘"].iloc[-1 + RE_DATA :].values[0]
            - stock_data["收盘"].iloc[-20:].min()
        ) / stock_data["收盘"].iloc[-1 + RE_DATA :].values[0]
        # 最近20天没有大幅度下跌
        if down_pct > 0.05 or up_pct > 0.20:
            return False

        # 最近5天趋势向上
        d5_pct = (
            stock_data["收盘"].iloc[-5:].max() - stock_data["收盘"].iloc[-1:].values[0]
        ) / stock_data["收盘"].iloc[-1:].values[0]
        if d5_pct < 0.01 or d5_pct > 0.10:
            return False

        # 最近一天价格为相对最高
        if (
            stock_data["收盘"].iloc[-1:].values[0]
            < stock_data["收盘"].iloc[-10:].max() * 0.97
        ):
            return False
        current_ZD = stock_data["涨跌幅"].iloc[-1:].values[0]
        return [True, change_pct, current_ZD]

    def run(self, stock):
        time.sleep(random.uniform(0.1, 0.2))

        code = stock[0]
        name = stock[1]
        syl = stock[2]  # 市盈率
        index = stock[3]  # 索引

        # print(f"{code,name}")
        stock_data = self.search_stock(code)
        with open("./upward_result/stop_code.txt", "w") as f_code:
            f_code.write(str(index))
            f_code.close()
        try:
            stock_data100 = self.process_dataframe(stock_data)
        except Exception as e:
            print(f" 数据处理失败\n {e}")
            return 0
        process_Data = self.rm_stop_and_down(stock_data100)
        if isinstance(process_Data, list):
            # print(process_Data)
            # try:
            #     stock_trade_info = ak.stock_individual_info_em(symbol=code)
            #     hy_info = stock_trade_info[6]

            # except Exception as e:
            #     print(f"获取行业信息失败: ")

            hy_info = "未知行业"
            print(f"{code,name} 符合条件,行业:{hy_info},市盈率:{syl}")

            with open(RESULT_PATH, "a+") as f:
                f.write(
                    f"{code},{name},{process_Data[1]},{syl},{hy_info},{process_Data[2]},\n"
                )
            return 0
        else:
            pass  # print(f"{code,name} 不符合条件")
        return 0

    @staticmethod
    def research_stop_code():
        try:
            with open("./upward_result/stop_code.txt", "r", encoding="utf-8") as f:
                stop_codes = f.readlines()
                stop_codes = int(stop_codes[0].strip())
        except FileNotFoundError:
            stop_codes = 0

        if stop_codes > 3000:
            return 0
        return stop_codes


Search_StopCode_way = "eastMoney"
StockCode_list = []


if __name__ == "__main__":
    if Search_StopCode_way == "eastMoney":
        start = time.time()
        stock = stock_upward()

        stop_codes = stock.research_stop_code()
        print("上次停止数为%s", stop_codes)
        stock_code_Df_noiloc = stock.fitch_stock_code()
        stock_code_Df = stock_code_Df_noiloc[stop_codes:]

        print("获取股代码完成")
        stock_list = list(
            zip(
                stock_code_Df["代码"],
                stock_code_Df["名称"],
                stock_code_Df["市盈率"],
                stock_code_Df.index,
            )
        )
    elif Search_StopCode_way == "custom":
        stock_list = list(
            zip(
                StockCode_list["代码"],
                0,
                0,
                0,
            )
        )
        print("获取股代码失败,请检查数据源")
        exit(0)

    print("开始获取股票数据")
    with open(RESULT_PATH, "w") as f:

        f.write(
            f"代码,名字,近期涨跌幅,市盈率,行业,当日涨跌幅{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
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
