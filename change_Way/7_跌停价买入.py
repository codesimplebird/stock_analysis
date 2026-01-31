import os
import datetime
import statistics

from concurrent.futures import ThreadPoolExecutor
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

import akshare as ak

plt.rcParams['font.sans-serif'] = 'SimHei'
plt.rcParams['axes.unicode_minus'] = False

'''实现传入一个或者多个代码都能进行运算'''


class StockAnalysis:

    def __init__(self, code, name='', save_type='.png', is_hy=False) -> None:
        if name == '' and is_hy == False:
            # 获取实时行情数据
            stock_data = ak.stock_zh_a_spot_em()
            # 设置股票代码为索引列
            stock_data = stock_data.set_index("代码")
            name = stock_data.loc[code, "名称"]
        self.today = datetime.date.today().strftime('%Y%m%d')
        self.SaveDir = f'../../mystock/AnalysisFileall/{code + name}'

        self.stock_Info = ak.stock_zh_a_hist(symbol=code, period="daily", start_date="19980910",
                                             end_date=self.today,
                                             adjust="")

        self.save_type = save_type
        self.code = code
        self.name = name

    @staticmethod
    def select_stock(model='select'):
        if model == 'select':
            filedir = f'../../mystock/stock_select/{datetime.date.today()}股票数据.csv'
        elif model == 'all':
            filedir = f'../../mystock/stock_select/{datetime.date.today()}全股票数据.csv'
        else:
            raise "选股模式只有'select'和'all'"
        if os.path.exists(filedir):
            pass
        else:
            import SelectStock_tocsv
            SelectStock_tocsv.stock_select(model)
        df = pd.read_csv(filedir, encoding='gbk')
        code = [str(i) if len(str(i)) == 6 else '0' *
                                                (6 - len(str(i))) + str(i) for i in df['代码']]
        name = [i for i in df['名称']]
        return list(zip(code, name))

    def all_display(self):
        print(self.code, self.name, '完成')
        df = self.stock_Info

        df['日期'] = df['日期'].astype("datetime64[ns]")

        df.set_index('日期', inplace=True)
        df_exchange = pd.DataFrame(df['换手率'])
        df_price = pd.DataFrame(df['收盘'])  # price 价格
        df_price['20日线'] = df_price.rolling(20).mean()
        df_exchange['10日线'] = df_exchange.rolling(10).mean()
        exc_quantile = df_exchange['10日线'].quantile(
            list(np.arange(11) / 10)).values
        result = self.lowerchangedate(df_exchange, df_price, )
        buydate = result[0].index
        if result[1] > 0:
            if not os.path.exists(self.SaveDir):
                os.makedirs(self.SaveDir)

            # 保存一个收益文本
            try:
                os.makedirs(''.join([self.SaveDir, '/复利收益-', str(result[1])]))
            except FileExistsError:
                print('收益没变化')
            print('文件创建完成')
            with open(f'收益/{self.today}.csv', mode='a', encoding='gbk') as f:

                f.write(','.join([self.code, self.name, str(result[1]), '\n']))

            self.designPlot(df_price, buydate)
            self.designPlot(df_exchange, buydate, exc_quantile)
            if result[2] == 1:
                print('在附近')

            print('制图完成', )
        else:
            print('不合格')

    def only_data(self):
        print(self.code)
        df = self.stock_Info
        df['日期'] = df['日期'].astype("datetime64[ns]")
        df.set_index('日期', inplace=True)

        df_price = pd.DataFrame(df['收盘'])  # price 价格
        df_price['20日线'] = df_price.rolling(20).mean()

        result = self.lowerchangedate(df, df_price, -9.5)
        '''result : ['收益时间和收益率的df','总和复利','是否在40天内']'''
        return result

    def designPlot(self, df, buydate, *q_list: list):
        """为其换手率以及股价画图"""
        df.plot(figsize=(20, 8), linewidth=0.5)
        try:
            plt.xticks(ticks=pd.date_range(
                df.index[0], df.index[-1] + datetime.timedelta(days=50), freq="M")[::4])
        except:
            print(self.name, '制图错误')
        plt.xlabel('日期')
        plt.ylabel(list(df.columns)[0])
        if q_list:
            q_list = list(q_list)[0]
            plt.hlines(y=q_list[:5], xmin=df.index[0], xmax=df.index[-1],
                       colors="red", linewidth=0.5, linestyle="dashed")
            plt.hlines(y=q_list[5:], xmin=df.index[0], xmax=df.index[-1],
                       colors="g", linewidth=0.5, linestyles="dashed")

        else:
            pass

        for item in buydate:
            plt.vlines(x=item, ymin=0, ymax=df.iloc[:, :1].values.max(
            ), linewidth=0.5, linestyles="dashed")

        save_path_plot = self.SaveDir + '/' + list(df.columns)[0] + self.name + self.save_type
        plt.savefig(save_path_plot)
        plt.close()

    def lowerchangedate(self, df, df_pr, most_down) -> list:
        ''' 将其低与10%换手日期和收益率进行返回 '''
        '''返回为一个df对象'''

        ex_low_date = df[df['涨跌幅'] < most_down].index  # 获取小于10%的10日平均换手
        '''获得一个跌停的日期以及值'''

        date = ex_low_date

        coll = self.futureEarnings(df_pr)  # earning: 收入

        Yieldlist = []  # 收益率
        one = 1
        for i in date:

            if (i + datetime.timedelta(60)) > df_pr.index.max():
                x = (coll['收盘'][df.index.max()] -
                     coll['收盘'][i]) / coll['收盘'][i]
                Yieldlist.append(x)
                break
            else:
                x = (coll['六十日'][i] - coll['收盘'][i]) / coll['收盘'][i]
                Yieldlist.append(x)
        for i in Yieldlist:
            one *= (i + 1)
        one = round(one, 3)
        average = statistics.mean(Yieldlist)
        # print('平均收益:',average, end='|')
        # print('复利收益:', one)
        print('收益为:', one)
        return [one,len(Yieldlist),average]

    @staticmethod
    def futureEarnings(df_pr):

        wroth = df_pr.copy()
        wr3 = pd.DataFrame(wroth).shift(-3)
        wr3.rename(columns={'收盘': '三日'}, inplace=True)
        wr5 = pd.DataFrame(wroth).shift(-5)
        wr5.rename(columns={'收盘': '五日'}, inplace=True)

        wr10 = pd.DataFrame(wroth).shift(-10)
        wr10.rename(columns={'收盘': '十日'}, inplace=True)
        wr60 = pd.DataFrame(wroth).shift(-60)
        wr60.rename(columns={'收盘': '六十日'}, inplace=True)
        wr40 = pd.DataFrame(wroth).shift(-40)
        wr40.rename(columns={'收盘': '四十日'}, inplace=True)
        coll = pd.concat([wroth, wr5, wr10, wr60, wr40,wr3], axis=1)
        return coll


def process_instance(codelist):
    inst = StockAnalysis(codelist[0], codelist[1])
    result = inst.only_data()
    try:
        with open(f'../../mystock/stock_select/{datetime.date.today()}跌停收益.csv', 'a+', encoding='gbk') as f:

            f.write(f'{codelist[0]},{codelist[1]},{result[0]},{result[1]},{result[2]}\n')

    except FileNotFoundError:

        os.makedirs('../../mystock/AnalysisFileall/stock_select/')
    del inst


if __name__ == '__main__':
    '''实例化对象使用多线程'''
    model = 'select'
    info = 1

    if info:
        code_list = ['000837', '600584', '002322', '001283']
        for code in code_list:
            s = StockAnalysis(code, is_hy=False)
            s.only_data()
    else:

        code_list = StockAnalysis.select_stock(model)

        with ThreadPoolExecutor() as pool:
            pool.map(process_instance, code_list)
