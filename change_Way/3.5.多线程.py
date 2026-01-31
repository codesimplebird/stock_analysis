import os
import datetime
import time
from concurrent.futures import ThreadPoolExecutor
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

import akshare as ak

plt.rcParams['font.sans-serif'] = 'SimHei'
plt.rcParams['axes.unicode_minus'] = False

'''实现传入一个或者多个代码都能进行运算'''


class Stock_Analysis:
    def __init__(self, code) -> None:
        self.today = datetime.date.today().strftime('%Y%m%d')
        self.Savedir = f'./AnalysisFileall/{code}'
        self.ex_quantile = None
        self.result = None
        self.stock_Info = None
        self.code = code
        if os.path.exists(self.Savedir):

            pass
        else:
            os.makedirs(self.Savedir)

    def all_display(self):

        self.stock_Info = ak.stock_zh_a_hist(symbol=self.code, period="daily", start_date="20120301",
                                             end_date=self.today,
                                             adjust="qfq")
        print(self.code)
        df = self.stock_Info
        df['日期'] = df['日期'].astype("datetime64[ns]")
        df.set_index('日期', inplace=True)
        df_exchange = pd.DataFrame(df['换手率'])
        df_price = pd.DataFrame(df['收盘'])  # price 价格
        df_price['20日线'] = df_price.rolling(20).mean()
        df_exchange['10日线'] = df_exchange.rolling(10).mean()
        exc_quantile = df_exchange['10日线'].quantile(
            list(np.arange(11) / 10)).values
        self.result = self.LowerChangeDate(df_exchange, df_price, exc_quantile[1])
        buydate = self.result[0].index
        self.DesignPlot(df_price, buydate)
        self.DesignPlot(df_exchange, buydate, exc_quantile)

    def DesignPlot(self, df, buydate, *q_list: list):

        '''为其换手率以及股价画图'''
        df.plot(figsize=(20, 8), linewidth=0.5)
        try:
            plt.xticks(ticks=pd.date_range(
                df.index[0], df.index[-1] + datetime.timedelta(days=40), freq="M")[::4])
        except:
            pass
        plt.xlabel('日期')
        plt.ylabel(list(df.columns)[0])
        if q_list:
            q_list = list(q_list)[0]
            plt.hlines(y=q_list[:5], xmin=df.index[0], xmax=df.index[-1],
                       colors="red", linewidth=0.5, linestyle="dashed")
            plt.hlines(y=q_list[5:], xmin=df.index[0], xmax=df.index[-1],
                       colors="g", linewidth=0.5, linestyle="dashed")

        else:
            pass

        for item in buydate:
            plt.vlines(x=item, ymin=0, ymax=df.iloc[:, :1].values.max(
            ), linewidth=0.5, linestyles="dashed")

        save_path_plot = self.Savedir + '/' + list(df.columns)[0] + '.svg'
        plt.savefig(save_path_plot)
        plt.close()

    def LowerChangeDate(self, df_ex, df_pr, Tenthsdata) -> list:

        ''' 将其低与10%换手日期和收益率进行返回 '''
        '''返回为一个df对象'''
        df_ex10 = df_ex['10日线']
        ex_low_date = df_ex10[df_ex10 < Tenthsdata]  # 获取小于10%的10日平均换手
        '''获得一个小于10%换手率的日期以及值'''

        days = []
        num = []
        m = []
        s = []
        date = ex_low_date.keys()

        for i in range(len(date) - 1):
            if (date[i + 1] - date[i]) < datetime.timedelta(5):
                m.append(df_ex10[date[i]])
                s.append(date[i])

            else:
                s.append(date[i])
                m.append(df_ex10[date[i]])
                num.append(m)
                days.append(s)
                m = []
                s = []
        if m == []:
            pass
        else:
            num.append(m)
            days.append(s)
        t_date = []

        t_num = []  # 以上有时间进行封装
        for i in range(len(num)):
            if len(num[i]) == 1:
                t_date.append(days[i][0])
                t_num.append(num[i][0])
            else:
                t_num.append(num[i][num[i].index(min(num[i]))])
                t_date.append(days[i][num[i].index(min(num[i]))])

        lowerData = pd.DataFrame(data=t_num, index=t_date)
        lowerData.rename(columns={0: '换手率'}, inplace=True)

        coll = self.futureEarnings(df_pr)  # earning: 收入

        Yieldlist = []  # 收益率
        one = 1
        for i in lowerData.index:
            if (i + datetime.timedelta(60)) > df_pr.index.max():
                x = (coll['收盘'][df_pr.index.max()] - coll['收盘'][i]) / coll['收盘'][i]
                Yieldlist.append(x)
                break
            else:
                x = (coll['四十日'][i] - coll['收盘'][i]) / coll['收盘'][i]
                Yieldlist.append(x)
        for i in Yieldlist:
            one *= (i + 1)
        one = round(one, 3)
        print(one, end=' ')
        if len(Yieldlist) == len(t_date):

            pass
        else:
            _ = len(t_date) - len(Yieldlist)
            for i in range(_):
                Yieldlist.append(0)
        df_Yield = pd.DataFrame(data=Yieldlist, index=t_date)
        result_df = pd.concat([lowerData, df_Yield], axis=1)

        return [result_df, one]

    def futureEarnings(self, df_pr):

        wroth = df_pr.copy()
        wr5 = pd.DataFrame(wroth).shift(-5)
        wr10 = pd.DataFrame(wroth).shift(-10)
        wr10.rename(columns={'收盘': '十日'}, inplace=True)
        wr5.rename(columns={'收盘': '五日'}, inplace=True)
        wr60 = pd.DataFrame(wroth).shift(-60)
        wr60.rename(columns={'收盘': '六十日'}, inplace=True)
        wr40 = pd.DataFrame(wroth).shift(-40)
        wr40.rename(columns={'收盘': '四十日'}, inplace=True)
        coll = pd.concat([wroth, wr5, wr10, wr60, wr40], axis=1)
        return coll


def StcokCodeList() -> list:
    filedir = f'AnalysisFileall/stock_select/{datetime.date.today()}股票数据.csv'

    if os.path.exists(filedir):
        pass
    else:
        import SelectStock_tocsv
        selectStock_tocsv.stock_select()
    df = pd.read_csv(filedir, encoding='gbk')
    code = [str(i) if len(str(i)) == 6 else '0' * (6 - len(str(i))) + str(i) for i in df['代码']]
    return code


if __name__ == '__main__':
    start = time.time()
    codelist = StcokCodeList()

    SA = Stock_Analysis.all_display
    with ThreadPoolExecutor() as pool:
        pool.map(SA, codelist)

    end = time.time()
    print(start - end)
    # Stock_Analysis('600584').all_display()