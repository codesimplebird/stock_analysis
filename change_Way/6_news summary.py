import requests
from datetime import date
from lxml import etree

path = '../../mystock/要闻分析/财经新闻/'


# original : 原来的
# 这是新的信息
def new_info():



    newdate = requests.get('https://finance.eastmoney.com/yaowen.html').content.decode('utf-8')

    # 将html转化为lxml对象
    e = etree.HTML(newdate)
    for i in range(50):
        info = e.xpath(f'//li[@id="newsTr{i + 1}"]//div[2]/p')
        info[0] = info[0].xpath('./a')[0]
        title = info[0].text
        long_info_link = info[0].get('href')
        short_info = info[1].get('title')
        info_time = info[2].text
        with open(f'{path}{date.today()}新闻摘要.csv', 'a+', encoding='gbk') as f:
            f.write(f'{info_time},{title},{long_info_link},{short_info}\n')


def history_info():
    head = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.48'
        ,
        'Cookie': '***REMOVED***;***REMOVED***;***REMOVED***;***REMOVED***