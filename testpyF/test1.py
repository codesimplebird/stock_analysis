import requests
import pandas as pd
import time
import random
from typing import Optional, List, Dict, Union


class EastMoneyCrawler:
    """东方财富行情爬虫（支持自定义Cookie）"""

    def __init__(
        self, cookie_str: Optional[str] = None, use_selenium_backup: bool = False
    ):
        """
        初始化爬虫
        :param cookie_str: 从浏览器复制的Cookie字符串，例如 "key1=value1; key2=value2"
        :param use_selenium_backup: 是否启用Selenium作为备用方案
        """
        self.base_url = "https://push2.eastmoney.com/api/qt/clist/get"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0",
            "Referer": "https://quote.eastmoney.com/",
            "Accept": "application/json, text/plain, */*",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

        # ----- 新增：处理Cookie -----
        if cookie_str:
            # 将 Cookie 字符串解析为字典并设置到 session.cookies
            cookie_dict = {}
            for item in cookie_str.split(";"):
                item = item.strip()
                if not item:
                    continue
                key, value = item.split("=", 1)
                cookie_dict[key] = value
            self.session.cookies.update(cookie_dict)
            print("已注入Cookie")

        self.use_selenium_backup = use_selenium_backup

    def _get_market_param(self) -> str:
        """获取市场参数：沪深A股（包括主板、创业板、科创板）"""
        return "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23"

    def _get_required_fields(self) -> str:
        """指定需要获取的数据字段，包含市盈率 f162"""
        return "f12,f14,f2,f3,f4,f5,f6,f15,f16,f17,f18,f162"

    def _fetch_page_by_api(
        self, page: int = 1, page_size: int = 2000
    ) -> Optional[List[Dict]]:
        params = {
            "pn": page,
            "pz": page_size,
            "po": 1,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "fid": "f3",
            "fs": self._get_market_param(),
            "fields": self._get_required_fields(),
        }
        try:
            response = self.session.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get("data") and data["data"].get("diff"):
                return data["data"]["diff"]
            else:
                return None
        except requests.exceptions.RequestException as e:
            print(f"API请求失败: {e}")
            return None

    def get_all_stocks_by_api(self) -> pd.DataFrame:
        all_data = []
        page = 1
        page_size = 2000
        print("开始通过API获取股票数据...")
        while True:
            print(f"正在获取第 {page} 页...")
            page_data = self._fetch_page_by_api(page, page_size)
            if not page_data:
                print(f"第 {page} 页无数据，数据获取完成。")
                break
            all_data.extend(page_data)
            print(f"第 {page} 页获取 {len(page_data)} 条数据，累计 {len(all_data)} 条")
            page += 1
            time.sleep(random.uniform(0.5, 1.5))

        if not all_data:
            print("未获取到任何数据，请检查网络或接口。")
            return pd.DataFrame()

        df = pd.DataFrame(all_data)
        column_mapping = {
            "f12": "股票代码",
            "f14": "股票名称",
            "f2": "最新价",
            "f3": "涨跌幅",
            "f4": "涨跌额",
            "f5": "成交量",
            "f6": "成交额",
            "f15": "最高",
            "f16": "最低",
            "f17": "今开",
            "f18": "昨收",
            "f162": "市盈率",
        }
        df.rename(columns=column_mapping, inplace=True)
        numeric_columns = [
            "最新价",
            "涨跌幅",
            "涨跌额",
            "成交量",
            "成交额",
            "最高",
            "最低",
            "今开",
            "昨收",
            "市盈率",
        ]
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df

    # 以下为Selenium备用方案（保持不变）
    def fetch_by_selenium(self, wait_time: int = 10) -> Optional[pd.DataFrame]:
        if not self.use_selenium_backup:
            print("Selenium备用方案未启用")
            return None
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.chrome.options import Options

            print("启用Selenium备用方案...")
            chrome_options = Options()
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--headless")
            chrome_options.add_experimental_option(
                "excludeSwitches", ["enable-automation"]
            )
            chrome_options.add_experimental_option("useAutomationExtension", False)
            driver = webdriver.Chrome(options=chrome_options)
            driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            url = "https://quote.eastmoney.com/center/gridlist.html#hs_a_board"
            driver.get(url)
            wait = WebDriverWait(driver, wait_time)
            wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "#table_wrapper-table")
                )
            )
            rows = driver.find_elements(
                By.CSS_SELECTOR, "#table_wrapper-table tbody tr"
            )
            data = []
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if cells:
                    row_data = [cell.text for cell in cells]
                    data.append(row_data)
            driver.quit()
            if data:
                df = pd.DataFrame(data[1:], columns=data[0])
                return df
            else:
                print("Selenium未获取到数据")
                return None
        except Exception as e:
            print(f"Selenium备用方案执行失败: {e}")
            return None

    def run(self) -> Optional[pd.DataFrame]:
        df = self.get_all_stocks_by_api()
        if df.empty and self.use_selenium_backup:
            print("API方案失败，切换到Selenium备用方案...")
            df = self.fetch_by_selenium()
        return df


if __name__ == "__main__":
    # 使用示例：从浏览器复制Cookie字符串（如F12 -> Network -> 任意请求 -> Request Headers -> cookie）
    # 注意：Cookie可能包含特殊字符，直接复制整段字符串即可。
    ***REMOVED***

    # 传入cookie（如果不使用Cookie，保持None即可）
    crawler = EastMoneyCrawler(cookie_str=cookie_example, use_selenium_backup=False)
    df = crawler.run()

    if df is not None and not df.empty:
        print(f"\n成功获取 {len(df)} 条股票数据")
        print("\n数据预览（前5条）：")
        print(df.head())
        # 可选：保存到CSV
        df.to_csv("eastmoney_stocks.csv", index=False, encoding="utf-8-sig")
    else:
        print("数据获取失败。")
