from akshare import stock_zh_a_spot_em
import os
from datetime import date

DataPath = '../../mystock/stock_select'


def stock_select(model='select'):
    now_day = date.today()
    new_stock = stock_zh_a_spot_em()
    if model == 'select':

        new_stock = new_stock[new_stock['市盈率-动态'] > 1]
        new_stock = new_stock[new_stock['市盈率-动态'] < 50]
        new_stock = new_stock[new_stock['市净率'] > 0]
        new_stock = new_stock[new_stock['换手率'] > 0.2]
        new_stock = new_stock[new_stock['总市值'] > 1000000000]
        new_stock = new_stock[new_stock['总市值'] < 40000000000]
        new_stock = new_stock[new_stock['年初至今涨跌幅'] < 20]
        new_stock = new_stock[new_stock['60日涨跌幅'] < 20]
        new_stock = delete_invalid_stock(new_stock=new_stock)

        if not os.path.exists(DataPath):
            os.makedirs(DataPath)

        new_stock.to_csv(
            f'{DataPath}/{now_day}股票数据.csv', encoding='gbk')
    else:
        new_stock = delete_invalid_stock(new_stock)
        new_stock.to_csv(f'{DataPath}/{now_day}全股票数据.csv', encoding='gbk')


def delete_invalid_stock(new_stock):
    """去除4,8,30,688开头股票"""
    code = new_stock['代码'].values

    m = [True for _ in range(len(code))]
    for i in ['688', '30', '8', '4']:
        x = [False if codei.startswith(i) else True for codei in code]
        for item in range(len(m)):
            if not x[item]:
                m[item] = x[item]

    new_stock = new_stock[m]
    return new_stock


if __name__ == '__main__':
    stock_select()
