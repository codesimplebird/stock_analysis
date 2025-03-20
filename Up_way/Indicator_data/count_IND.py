import tushare as ts
import akshare as ak
from concurrent.futures import ThreadPoolExecutor

# # 设置 Tushare 的 token（需要注册 Tushare 账号获取）

# Indicator_data
# ts.set_token("d3decd78eb8cf2cb37fa8a8cec767b47aeaacbd037ba03af37496172")
# pro = ts.pro_api()

# # 获取某一天的股票数据
# target_date = "20231101"  # 格式为 "YYYYMMDD"
# df = pro.daily(trade_date=target_date)


# # 筛选需要的列（交易日期、股票代码、成交额）
# result_df = df[["trade_date", "ts_code", "amount"]]
# # 保存为 CSV 文件
# result_df.to_csv(
#     f"all_stocks_turnover_{target_date}.csv", index=False, encoding="utf_8_sig"
# )
class Stock_Analysis:
    def __init__(self):
        ts.set_token("d3decd78eb8cf2cb37fa8a8cec767b47aeaacbd037ba03af37496172")
        self.pro = ts.pro_api()

    @staticmethod
    def search_date():
        trade_date_df = ak.tool_trade_date_hist_sina()

        # 打印数据
        date = [
            str(trade_date_df["trade_date"][i]).replace("-", "")
            for i in range(len(trade_date_df) - 200, 6800, -1)
        ]  # 日期
        return date

    def stock_amount(self, trade_date):
        # 设置 Tushare 的 token（需要注册 Tushare 账号获取）

        # 获取某一天的股票数据
        try:
            df = self.pro.daily(trade_date=trade_date)
        except Exception as e:
            print(f"{trade_date},数据获取失败")
            return 0

        # 筛选需要的列（交易日期、股票代码、成交额）
        result_df = df[["trade_date", "ts_code", "amount"]]
        # 保存为 CSV 文件
        return self.process_date(result_df, trade_date)

    def stock_saveData_csv(self, trade_date):

        # 保存为 CSV 文件
        try:
            df = self.pro.daily(trade_date=trade_date)
        except Exception as e:
            print(f"{trade_date},数据获取失败")
            return 0
        df.to_csv(
            f"stockData_allDay/{trade_date}.csv", index=False, encoding="utf_8_sig"
        )
        print(f"数据已保存为{trade_date}.csv")
        return 0

    def process_date(self, df_amount, trade_date):

        df_sorted = df_amount.sort_values(by="amount", ascending=False)
        # 打印数据
        total_stocks = len(df_sorted)
        if total_stocks <= 5:
            print(f"{trade_date},数据不足")
            return 0
        top_5_percent_count = int(total_stocks * 0.05)
        top_5_percent_stocks = df_sorted.head(top_5_percent_count)
        top_5_percent_turnover = top_5_percent_stocks["amount"].sum()
        total_turnover = df_sorted["amount"].sum()
        turnover_ratio = top_5_percent_turnover / total_turnover
        with open("拥挤度数据.csv", "a+") as f:
            f.write(
                f"{trade_date},{total_stocks},{top_5_percent_count},{turnover_ratio.round(4)}\n"
            )

        print(f"{trade_date},{turnover_ratio.round(4)}")
        return 0


if __name__ == "__main__":
    # 获取 A 股所有股票列表
    Stock_Analysis = Stock_Analysis()
    Stock_Analysis.stock_amount("20250307")

    # date_all = Stock_Analysis.search_date()
    # # print(len(date_all))
    # with ThreadPoolExecutor(max_workers=10) as executor:
    #     executor.map(Stock_Analysis.stock_saveData_csv, date_all)
    # # Stock_Analysis.stock_amount("20250217")
