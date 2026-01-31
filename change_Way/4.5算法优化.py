import os
import datetime

from concurrent.futures import ThreadPoolExecutor
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np


import akshare as ak

plt.rcParams["font.sans-serif"] = "SimHei"
plt.rcParams["axes.unicode_minus"] = False

"""实现传入一个或者多个代码都能进行运算"""


class StockAnalysis:
    """
    传入三个主要参数,股票代码,股票名称,保存图片所需格式
    """

    def __init__(self, code, name, img_save_type=".png") -> None:
        self.today = datetime.date.today().strftime("%Y%m%d")
        self.SaveDir = f"../../mystock/AnalysisFileall/{code + name}"

        self.stock_Info = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date="20120301",
            end_date=self.today,
            adjust="qfq",
        )
        self.code = code
        self.name = name
        self.img_save_type = img_save_type

    def all_display(self):
        print(self.code, "完成")
        df = self.stock_Info
        df["日期"] = df["日期"].astype("datetime64[ns]")
        df.set_index("日期", inplace=True)
        df_exchange = pd.DataFrame(df["换手率"])
        df_price = pd.DataFrame(df["收盘"])  # price 价格
        df_price["20日线"] = df_price.rolling(20).mean()
        df_exchange["10日线"] = df_exchange.rolling(10).mean()
        exc_quantile = df_exchange["10日线"].quantile(list(np.arange(11) / 10)).values
        result = self.lower_change_date(df_exchange, df_price, exc_quantile[1])
        buydate = result[0].index
        if result[1] > 2:
            if os.path.exists(self.SaveDir):
                pass
            else:
                os.makedirs(self.SaveDir)
            # 保存一个收益文本
            try:
                os.makedirs("".join([self.SaveDir, "/复利收益-", str(result[1])]))
            except FileExistsError:
                print("收益没变化")
            print("文件创建完成")
            f = open(f"收益/{self.today}.csv", mode="a", encoding="gbk")
            f.write(",".join([self.code, self.name, str(result[1]), "\n"]))
            f.close()

            self.design_plot(df_price, buydate)
            self.design_plot(df_exchange, buydate, exc_quantile)
            print("制图完成")
        else:
            print("不合格")

    def design_plot(self, df, buydate, *q_list: list):
        """为其换手率以及股价画图"""
        df.plot(figsize=(20, 8), linewidth=0.5)
        try:
            plt.xticks(
                ticks=pd.date_range(
                    df.index[0], df.index[-1] + datetime.timedelta(days=40), freq="M"
                )[::4]
            )
        except:
            pass
        plt.xlabel("日期")
        plt.ylabel(list(df.columns)[0])
        if q_list:
            q_list = list(q_list)[0]
            plt.hlines(
                y=q_list[:5],
                xmin=df.index[0],
                xmax=df.index[-1],
                colors="red",
                linewidth=0.5,
                linestyle="dashed",
            )
            plt.hlines(
                y=q_list[5:],
                xmin=df.index[0],
                xmax=df.index[-1],
                colors="g",
                linewidth=0.5,
                linestyle="dashed",
            )

        else:
            pass

        for item in buydate:
            plt.vlines(
                x=item,
                ymin=0,
                ymax=df.iloc[:, :1].values.max(),
                linewidth=0.5,
                linestyles="dashed",
            )

        save_path_plot = self.SaveDir + "/" + list(df.columns)[0] + self.img_save_type
        plt.savefig(save_path_plot)
        plt.close()

    def lower_change_date(self, df_ex, df_pr, tenths_data) -> list:
        """将其低与10%换手日期和收益率进行返回"""
        """返回为一个df对象"""
        df_ex10 = df_ex["10日线"]
        lower_data = df_ex10[df_ex10 < tenths_data]  # 获取小于10%的10日平均换手
        lower_data = pd.DataFrame({"date": lower_data.index, "data": lower_data.values})
        # 将日期列设为索引
        lower_data.set_index("date", inplace=True)

        # 按照日期的差值是否超过5天分组，生成组的标识
        timedelta = (
            lower_data.index.to_series().diff() > pd.Timedelta(days=5)
        ).cumsum()

        # 对于每个组，找到数据最小值所对应的索引
        idxmin = lower_data.groupby(timedelta)["data"].idxmin()
        print(idxmin)
        # 将所有最小值所对应的索引保存到一个列表中
        min_indexes = idxmin.tolist()

        lower_data = lower_data.rename(columns={0: "换手率"}, inplace=True)

        coll = self.future_earnings(df_pr)  # earning: 收入
        lyield_list = []  # 收益率
        one = 1
        for i in min_indexes:
            if (i + datetime.timedelta(60)) > df_pr.index.max():
                x = (coll["收盘"][df_pr.index.max()] - coll["收盘"][i]) / coll["收盘"][i]
                lyield_list.append(x)
                break
            else:
                x = (coll["四十日"][i] - coll["收盘"][i]) / coll["收盘"][i]
                lyield_list.append(x)
        for i in lyield_list:
            one *= i + 1
        one = round(one, 3)
        print(one)

        if len(lyield_list) == len(coll):
            pass
        else:
            _ = len(min_indexes) - len(lyield_list)
            for i in range(_):
                lyield_list.append(0)
        df_yield = pd.DataFrame(data=lyield_list, index=min_indexes)
        result_df = pd.concat([lower_data, df_yield], axis=1)

        return [result_df, one]

    @staticmethod
    def future_earnings(df_pr):
        wroth = df_pr.copy()
        wr5 = pd.DataFrame(wroth).shift(-5)
        wr10 = pd.DataFrame(wroth).shift(-10)
        wr10.rename(columns={"收盘": "十日"}, inplace=True)
        wr5.rename(columns={"收盘": "五日"}, inplace=True)
        wr60 = pd.DataFrame(wroth).shift(-60)
        wr60.rename(columns={"收盘": "六十日"}, inplace=True)
        wr40 = pd.DataFrame(wroth).shift(-40)
        wr40.rename(columns={"收盘": "四十日"}, inplace=True)
        coll = pd.concat([wroth, wr5, wr10, wr60, wr40], axis=1)
        return coll


def select_stock():
    filedir = (
        f"../../mystock/AnalysisFileall/stock_select/{datetime.date.today()}股票数据.csv"
    )

    if os.path.exists(filedir):
        pass
    else:
        import SelectStock_tocsv

        SelectStock_tocsv.stock_select()
    df = pd.read_csv(filedir, encoding="gbk")
    code = [
        str(i) if len(str(i)) == 6 else "0" * (6 - len(str(i))) + str(i)
        for i in df["代码"]
    ]
    name = [i for i in df["名称"]]
    return list(zip(code, name))


if __name__ == "__main__":
    """实例化对象使用多线程"""

    def process_instance(stock_code_list):
        inst = StockAnalysis(stock_code_list[0], stock_code_list[1])
        inst.all_display()
        del inst

    info = 1
    if info:
        s = StockAnalysis("600584", "长电科技")
        s.all_display()
    else:
        codeList = select_stock()
        with ThreadPoolExecutor() as pool:
            pool.map(process_instance, codeList)
