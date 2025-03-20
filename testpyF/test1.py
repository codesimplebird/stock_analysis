import datetime
import time

import akshare as ak
import pandas as pd


# stock_board_industry_name_em_df = ak.stock_board_industry_name_em()
# bk = stock_board_industry_name_em_df['板块名称']
# stock_board_industry_cons_ems = pd.DataFrame()
# for i in bk:
#     stock_board_industry_cons_em_df = ak.stock_board_industry_cons_em(symbol=i)
#
#     stock_board_industry_cons_em_df['行业'] = i
#
#     stock_board_industry_cons_ems = pd.concat([stock_board_industry_cons_ems, stock_board_industry_cons_em_df])
#
# stock_board_industry_cons_ems.to_csv('hy.csv',encoding='gbk')
# # stock_board_industry_cons_em_df = ak.stock_board_industry_cons_em(symbol="小金属")
# import sys
# from PyQt5.QtWidgets import QApplication, QWidget, QPushButton
#
#
# class MyWindow(QWidget):
#     def __init__(self):
#         super().__init__()
#         self.initUI()
#
#     def initUI(self):
#         # 设置窗口标题
#         self.setWindowTitle('My PyQt Window')
#         # 设置窗口的大小和位置
#         self.setGeometry(300, 300, 300, 200)
#         # 添加一个按钮控件
#         btn = QPushButton('Click me', self)
#         # 设置按钮的位置和大小
#         btn.setGeometry(10, 10, 100, 30)
#         # 添加按钮点击事件的处理函数
#         btn.clicked.connect(self.on_click)
#
#         btn1 = QPushButton('Click to me', self)
#         btn1.setGeometry(100, 10, 100, 30)
#         btn1.clicked.connect(self.tow_click)
#
#     def on_click(self):
#         # 处理按钮点击事件的函数
#         print('Button clicked!')
#
#     def tow_click(self):
#         print('tow')
#
# if __name__ == '__main__':
#     # 创建应用程序
#     app = QApplication(sys.argv)
#     # 创建窗口对象
#     window = MyWindow()
#     # 显示窗口
#     window.show()
#     # 进入应用程序事件循环
#     sys.exit(app.exec_())

# df = ak.stock_board_industry_name_em()
# print(df[df['板块名称']=='半导体'])

# df = ak.stock_board_concept_name_em()['板块代码'].values
# print(df)
import PySimpleGUI as sg
import time

# 定义窗口布局
layout = [
    [sg.Text('Welcome to My App!', font=('Arial', 16))],
    [sg.Text('Please enter your name: '), sg.InputText(key='name')],
    [sg.Text('Please select your gender: '), sg.Radio('Male', 'gender', key='male'), sg.Radio('Female', 'gender', key='female')],
    [sg.Text('Please select your favorite color: '), sg.Combo(['Red', 'Green', 'Blue'], key='color')],
    [sg.Checkbox('I agree to the terms and conditions', key='agree')],
    [sg.Button('Submit'), sg.Button('Cancel')],
]

# 创建窗口对象
window = sg.Window('My App', layout)

# 事件循环
while True:
    event, values = window.read()
    if event == sg.WIN_CLOSED or event == 'Cancel':
        break
    elif event == 'Submit':
        name = values['name']
        gender = 'Male' if values['male'] else 'Female'
        color = values['color']
        agree = values['agree']
        sg.popup(f'Name: {name}\nGender: {gender}\nColor: {color}\nAgree: {agree}')
    elif event == 'tow_click':
        print('tow')

# 关闭窗口
window.close()