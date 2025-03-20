import os
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import datetime
import akshare as ak

plt.rcParams['font.sans-serif'] = 'SimHei'
plt.rcParams['axes.unicode_minus'] = False

'''实现传入一个或者多个代码都能进行运算'''


def main(stock_code):
    try:
        os.mkdir(f'./AnalysisFileall/{stock_code}_data')
    except FileExistsError:
        print('文件存在')
    file_dir = f'./AnalysisFileall/{stock_code}_data'
    file_path = file_dir + '/' + f'{stock_code}'
    if os.path.exists(file_path + '.csv') == False:
        print('未查到该数据,重新获取数据')
        stock_zh_a_hist_df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date="20120301",
                                                end_date='20221216',
                                                adjust="qfq")
        stock_zh_a_hist_df.to_csv(file_path + '.csv', encoding='gbk')
    elif isnew(File_df(file_path)) == False:
        stock_zh_a_hist_df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date="20120301",
                                                end_date='20221216',
                                                adjust="qfq")
        stock_zh_a_hist_df.to_csv(file_path + '.csv', encoding='gbk')
        print('该文件存在,但是未更新')
    else:
        print('数据完整')

    df = File_df(file_path)
    result = process(df, file_path)
    t1 = datetime.datetime.now()
    t2 = datetime.datetime.strftime(t1, '%Y-%m-%d')
    result[0].to_csv(file_path + '结果.csv', encoding='gbk')
    F = open(file_dir + '/' + f'{result[1]}({t2}).txt', 'w')
    F.close()


def File_df(filepath: str):  # 读取csv文件
    '''将路径的csv文件,创建为pd.dataframe对象'''
    file = filepath + '.csv'
    df = pd.read_csv(file, engine="python", skiprows=0, encoding='gbk')
    df['日期'] = df['日期'].astype("datetime64[ns]")
    df.set_index('日期', inplace=True)
    return df


def process(df, save_path):  # process 过程
    '''获取dataframe对象(整个表格)'''
    '''返回最终结果'''
    df_exchange = pd.DataFrame(df['换手率'])
    df_price = pd.DataFrame(df['收盘'])  # price 价格
    df_price['20日线'] = df_price.rolling(20).mean()
    df_exchange['10日线'] = df_exchange.rolling(10).mean()
    exc_quantile = df_exchange['10日线'].quantile(
        list(np.arange(11) / 10)).values
    exc_quantile_list = []
    for i in exc_quantile:
        exc_quantile_list.append(i)  # list  获得一个换手率(0-100%)十个分位的值

    '''绘制股价以及换手率图'''

    df_result = dataAnalysis(df_exchange, exc_quantile_list[1], df_price)
    buy_date = df_result[0].index
    designPlot(df_exchange, buy_date, save_path, exc_quantile_list)
    designPlot(df_price, buy_date, save_path)

    return df_result


def designPlot(df, buyline, save_path, *q_list: list):
    '''为其换手率以及股价画图'''
    df.plot(figsize=(20, 8), linewidth=0.5)
    plt.xticks(ticks=pd.date_range(
        df.index[0], df.index[-1] + datetime.timedelta(days=40), freq="M")[::4])
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

    for item in buyline:
        plt.vlines(x=item, ymin=0, ymax=df.iloc[:, :1].values.max(
        ), linewidth=0.5, linestyles="dashed")

    save_path_plot = save_path + list(df.columns)[0] + '.svg'
    plt.savefig(save_path_plot)
    plt.close()


def dataAnalysis(df_ex, lower, df_pr):
    '''将其低与10%换手日期和收益率进行返回'''
    '''返回为一个df对象'''
    df_ex10 = df_ex['10日线']
    ex_low_date = df_ex10[df_ex10 < lower]  # 获取小于10%的10日平均换手

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

    coll = futureEarnings(df_pr)  # earning 收入

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
    result = pd.concat([lowerData, df_Yield], axis=1)

    return [result, one]


def futureEarnings(df_pr):
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


def isnew(df):
    data_date = df.index.max()

    data_date = datetime.datetime.date(data_date)

    t1 = datetime.date.today()  # 获取当前日期
    week = t1.weekday()

    if week > 5:

        return False
    elif data_date == t1:
        return False
    else:
        return True


if __name__ == '__main__':

    stock_code = '601636'
    main(stock_code)
