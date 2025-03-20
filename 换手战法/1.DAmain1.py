# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import os
import datetime
import time
import asyncio
from concurrent.futures import ProcessPoolExecutor,ThreadPoolExecutor
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = 'SimHei'
plt.rcParams['axes.unicode_minus'] = False


def  main():
    read_dir = r'A:\BaiduNetdiskDownload\stock'
    save_dir = r'A:\BaiduNetdiskDownload\DataAnalysis'
    file_name = os.listdir(read_dir)[1200:1300]
    with ProcessPoolExecutor() as pool:
    # with ThreadPoolExecutor() as pool:
        pool.map(batchData,file_name)
    #
    # for i in file_name:
    #     batchData(i)

    # await asyncio.gather(batchData(file_name[1]),batchData(file_name[2]),batchData(file_name[3]),batchData(file_name[4]),batchData(file_name[0]))






def joinFile(filepath: str):
    '''将路径的csv文件,创建为pd.dataframe对象'''
    df = pd.read_csv(filepath, engine="python", skipfooter=1, skiprows=0,encoding='gbk')
    if df['交易日期'].max()>'2014-04-05':
        df=df[df['交易日期']>'2012-04-05']
        df['交易日期'] = df['交易日期'].astype("datetime64[ns]")
        df.set_index('交易日期', inplace=True)
        return df

    else :
        return None


def process(df,save_path):
    '''获取dataframe对象(整个表格)'''
    '''返回最终结果'''
    df_exchange = pd.DataFrame(df['换手率'])
    df_price = pd.DataFrame(df['收盘价'])
    df_price['20日线'] = df_price.rolling(20).mean()
    df_exchange['10日线'] = df_exchange.rolling(10).mean()
    exc_quantile = df_exchange['10日线'].quantile(list(np.arange(11) / 10)).values
    exc_quantile_list = []
    for i in exc_quantile:
        exc_quantile_list.append(i)
    designPlot(df_exchange,save_path, exc_quantile_list)
    designPlot(df_price,save_path)
    df_result = dataAnalysis(df_exchange, exc_quantile_list[1], df_price)
    return df_result


def designPlot(df, save_path,*q_list: list):
    '''为其换手率以及股价画图'''
    df.plot(figsize=(20, 8), linewidth=0.5)
    plt.xlabel('日期')
    plt.ylabel(list(df.columns)[0])
    if q_list:
        q_list = list(q_list)[0]
        plt.hlines(y=q_list[:5], xmin=df.index[0], xmax=df.index[-1], colors="red", linewidth=0.5, linestyle="dashed")
        plt.hlines(y=q_list[5:], xmin=df.index[0], xmax=df.index[-1], colors="g", linewidth=0.5, linestyle="dashed")


    else:
        pass
    save_path_plot=save_path+'\\'+list(df.columns)[0]
    plt.savefig(save_path_plot)
    plt.close()

def dataAnalysis(df_ex, low, df_pr):
    '''将其低换手日期和收益率进行返回'''
    '''返回为一个df对象'''
    df_ex10 = df_ex['10日线']
    ex_low_date = df_ex10[df_ex10 < low]  # 获取小于10%的10日平均换手

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

    coll = futureEarnings(df_pr)

    Yieldlist = []  # 收益率
    one = 1
    for i in lowerData.index:
        if (i + datetime.timedelta(60)) > df_pr.index.max():
            x=(coll['收盘价'][df_pr.index.max()]-coll['收盘价'][i])
            Yieldlist.append(x)
            break
        else:
            x = (coll['六十日'][i] - coll['收盘价'][i]) / coll['收盘价'][i]
            Yieldlist.append(x)
    for i in Yieldlist:
        one *= (i + 1)
    print(one,end=' ')
    if len(Yieldlist)==len(t_date):

        df_Yield = pd.DataFrame(data=Yieldlist, index=t_date)
    else :
        _=len(t_date)-len(Yieldlist)
        for i in range(_):
            Yieldlist.append(0)
        df_Yield = pd.DataFrame(data=Yieldlist, index=t_date)
    result = pd.concat([lowerData, df_Yield], axis=1)

    return [result,one]


def futureEarnings(df_pr):
    wroth = df_pr.copy()
    wr5 = pd.DataFrame(wroth).shift(-5)
    wr10 = pd.DataFrame(wroth).shift(-10)
    wr10.rename(columns={'收盘价': '十日'}, inplace=True)
    wr5.rename(columns={'收盘价': '五日'}, inplace=True)
    wr60 = pd.DataFrame(wroth).shift(-60)
    wr60.rename(columns={'收盘价': '六十日'}, inplace=True)
    wr40 = pd.DataFrame(wroth).shift(-40)
    wr40.rename(columns={'收盘价': '四十日'}, inplace=True)
    coll = pd.concat([wroth, wr5, wr10, wr60, wr40], axis=1)
    return coll

def batchData(file_name):
        item=file_name
        read_dir = r'A:\BaiduNetdiskDownload\stock'
        save_dir = r'A:\BaiduNetdiskDownload\DataAnalysis'
        save_path = save_dir + '\\' + item[:8]
        try:
            os.mkdir(save_path)
        except FileExistsError as fileerr:
            print('该文件已经存在')
        read_file_path = read_dir + '\\' + item
        df = joinFile(read_file_path)
        if type(df) == pd.core.frame.DataFrame:

            result = process(df, save_path)
            # print(item)
            save_file_path=save_path+'\\'+item[:8]+'.csv'
            result[0].to_csv(save_file_path, encoding='gbk')
        else:
            pass


if __name__ == '__main__':
    start=time.time()
    main()
    end=time.time()
    print(f'{end-start}秒')