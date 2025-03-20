'''格式为
日期 开盘价 收盘价 当日最高 当日最低 成交量 成交额 振幅 涨跌幅 涨跌额 换手

'''
import datetime

import openpyxl
import akshare

share_num1 = '600584'


def main(share_num):
    stock_zh_a_hist_df = akshare.stock_zh_a_hist(symbol=share_num, period="daily", start_date="20210301",
                                            end_date='20221117',
                                            adjust="qfq")
    wb = openpyxl.Workbook()
    sheet = wb.active
    sheet.title = share_num
    sheet.append(('日期', '开盘价', '收盘价', '当日最高',
                  '当日最低', '成交量', '成交额', '振幅', '涨跌幅', '涨跌额', '换手'))
    for item in stock_zh_a_hist_df.values:
        sheet.append(tuple(item))

    wb.save(f'Share_data_xl/{share_num}.xlsx')


def main_va():
    data = akshare.stock_zh_a_spot_em()

    wb = openpyxl.Workbook()
    sheet = wb.active
    sheet.title = str(datetime.date.today())
    sheet.append(('序号', '代码', '名称', '最新价', '涨跌幅', '涨跌额', '成交量', '成交额',
                  '振幅', '最高', '最低', '今开', '昨收', '量比', '换手率', '市盈率-动态','市净率', '总市值', '流通市值', '涨速',
                  '5分钟涨跌', '60日涨跌幅', '年初至今涨跌幅'))
    for item in data.values:
        sheet.append(tuple(item))

    wb.save(f'../Share_data_xl/{datetime.date.today()}.xlsx')


if __name__ == '__main__':
    main_va()
