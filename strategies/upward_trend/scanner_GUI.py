# -*- coding: utf-8 -*-
"""
scanner_GUI.py — 向上趋势选股系统 GUI 版本
基于 scanner.py 的 StockUpward 引擎，提供桌面交互界面
"""
import sys
import os
import csv
import time
import traceback
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QGroupBox, QFormLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QSpinBox, QDoubleSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QTextEdit, QTabWidget, QMessageBox,
    QFileDialog, QComboBox, QCheckBox, QFrame, QAbstractItemView,
    QStatusBar, QMenuBar, QAction, QToolBar,
    QGraphicsOpacityEffect,
)
from PyQt5.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QSize, QMutex, QMutexLocker,
    QPropertyAnimation, QEasingCurve,
)
from PyQt5.QtGui import (
    QFont, QPixmap, QIcon, QTextCursor, QPalette, QColor,
)

# ---------------------------------------------------------------------------
# 导入 scanner 引擎
# ---------------------------------------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from scanner import StockUpward, RESULT_DIR, DATA_DIR, STOCK_CSV_PATH


# ===================================================================
# 后台工作线程 — 在不阻塞 GUI 的情况下运行扫描
# ===================================================================
class ScanWorker(QThread):
    """在独立线程中运行全市场扫描，通过信号与 GUI 通信。"""

    # 信号定义
    progress_updated = pyqtSignal(int, int, str)      # 当前索引, 总数, 股票名称
    stock_matched = pyqtSignal(dict)                   # 符合条件的股票信息
    log_message = pyqtSignal(str)                      # 日志行
    scan_finished = pyqtSignal(float, int)             # 耗时(秒), 匹配数
    scan_error = pyqtSignal(str)                       # 错误消息

    def __init__(self, params: dict, parent=None):
        """
        params 支持以下键:
            start_date, end_date, max_workers, start_index,
            upward_long_days, upward_long_threshold,
            upward_short_days, upward_short_threshold,
            data_offset
        """
        super().__init__(parent)
        self.params = params
        self._engine = StockUpward()
        self._engine.start_date = params.get("start_date", "20250102")
        self._engine.end_date = params.get("end_date", datetime.today().strftime("%Y%m%d"))
        
        # 同步 UI 传入的阈值参数到 StockUpward 实例
        if "upward_long_days" in params:
            self._engine.upward_long_days = params["upward_long_days"]
        if "upward_long_threshold" in params:
            self._engine.upward_long_threshold = params["upward_long_threshold"]
        if "upward_short_days" in params:
            self._engine.upward_short_days = params["upward_short_days"]
        if "upward_short_threshold" in params:
            self._engine.upward_short_threshold = params["upward_short_threshold"]
        if "data_offset" in params:
            self._engine.data_offset = params["data_offset"]
            
        self._matched_stocks = []
        self._stop_flag = False
        self._scan_start_time = time.time()

    def stop(self):
        self._stop_flag = True

    @property
    def matched_stocks(self):
        return self._matched_stocks

    def run(self):
        try:
            self._do_scan()
        except Exception as e:
            self.scan_error.emit(f"扫描线程异常: {e}\n{traceback.format_exc()}")

    # ------------------------------------------------------------------
    def _do_scan(self):
        self._scan_start_time = time.time()  # 确保扫描开始时间正确初始化
        engine = self._engine

        # 1. 加载股票列表
        self.log_message.emit("正在加载股票代码列表…")
        all_stocks_df = engine.fetch_stock_code()
        total = len(all_stocks_df)
        self.log_message.emit(f"共加载 {total} 只股票")

        # 2. 参数
        max_workers = self.params.get("max_workers", 10)
        start_index = self.params.get("start_index", 0)

        # 3. 准备结果文件
        result_path = os.path.join(RESULT_DIR, f"{datetime.now().strftime('%Y%m%d')}.csv")
        os.makedirs(RESULT_DIR, exist_ok=True)
        with open(result_path, "w", newline="", encoding="utf-8") as f:
            f.write(f"代码,名字,近期涨跌幅,市盈率,行业,当日涨跌幅,{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # 4. 构建股票列表
        stocks_df = all_stocks_df.iloc[start_index:]
        stock_list = list(zip(
            stocks_df["代码"], stocks_df["名称"],
            stocks_df["市盈率-动态"], stocks_df.index,
        ))

        # 5. 多线程扫描
        matched = []
        completed = start_index
        lock = QMutex()

        self.log_message.emit(
            f"开始扫描 ({max_workers} 线程, 起始索引 {start_index})…"
        )

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {
                executor.submit(self._safe_run_one, engine, item, lock): item
                for item in stock_list
            }

            for future in as_completed(future_map):
                if self._stop_flag:
                    # 不再提交新任务，但已提交的继续
                    executor.shutdown(wait=False, cancel_futures=True)
                    self.log_message.emit("用户已停止扫描")
                    break

                result = future.result()
                completed += 1

                # 更新 checkpoint
                idx = future_map[future][3]
                with lock:
                    try:
                        with open(os.path.join(RESULT_DIR, "stop_code.txt"), "w") as fc:
                            fc.write(str(idx))
                    except OSError:
                        pass

                # 进度信号
                item_tuple = future_map[future]
                self.progress_updated.emit(completed, total, f"{item_tuple[0]} {item_tuple[1]}")

                if result is not None:
                    matched.append(result)
                    with lock:
                        # 写入结果文件
                        try:
                            with open(result_path, "a", newline="", encoding="utf-8") as f:
                                f.write(
                                    f"{result['code']},{result['name']},"
                                    f"{result['amplitude']:.4f},{result['pe_ratio']},"
                                    f"{result['industry']},{result['change_pct']},\n"
                                )
                        except OSError:
                            pass
                    self.stock_matched.emit(result)

        # 6. 收尾
        elapsed = time.time() - self._scan_start_time
        self._matched_stocks = matched

        # 复制结果到汇总文件
        try:
            import shutil
            shutil.copy(result_path, os.path.join(DATA_DIR, "stock_upward.csv"))
        except OSError:
            pass

        self.log_message.emit(
            f"扫描完成! 共 {len(matched)} 只符合条件, 耗时 {elapsed:.1f} 秒"
        )
        self.scan_finished.emit(elapsed, len(matched))

    # ------------------------------------------------------------------
    def _safe_run_one(self, engine, stock_item, lock):
        """包装 engine.run()，返回结构化结果或 None。"""
        if self._stop_flag:
            return None
        code, name, pe_ratio, idx = stock_item
        try:
            stock_data = engine.search_stock(code)
            if stock_data is None or stock_data.empty:
                return None

            processed = engine.process_dataframe(stock_data)
            if processed is None:
                return None

            criteria = engine.check_criteria(processed)
            if not isinstance(criteria, list):
                return None

            amplitude, change_pct = criteria[1], criteria[2]

            # 绘制 K 线图 (使用锁确保 Matplotlib 画图在多线程环境下的线程安全)
            with lock:
                engine.plot_kline(stock_data, code, name)

            return {
                "code": code,
                "name": name,
                "amplitude": amplitude,
                "pe_ratio": pe_ratio,
                "change_pct": change_pct,
                "industry": "未知行业",
            }
        except Exception as e:
            self.log_message.emit(f"{code} {name} 处理异常: {e}")
            return None

    def start_scan(self):
        self._scan_start_time = time.time()
        self.start()


# ===================================================================
# 历史结果加载线程
# ===================================================================
class LoadResultWorker(QThread):
    """在后台加载历史结果 CSV，不阻塞 GUI。"""
    result_loaded = pyqtSignal(list)       # 行数据列表
    load_error = pyqtSignal(str)
    log_message = pyqtSignal(str)

    def __init__(self, filepath, parent=None):
        super().__init__(parent)
        self.filepath = filepath

    def run(self):
        encodings = ["utf-8", "gbk", "gb18030"]
        rows = []
        last_err = None
        for enc in encodings:
            try:
                with open(self.filepath, "r", encoding=enc) as f:
                    reader = csv.reader(f)
                    next(reader, None)  # 跳过表头
                    for row in reader:
                        if row and row[0].strip():
                            rows.append(row)
                last_err = None
                break
            except (UnicodeDecodeError, UnicodeError) as e:
                last_err = e
                continue
        if last_err:
            self.load_error.emit(f"加载结果失败 (尝试 utf-8/gbk 均不可用): {last_err}")
        else:
            self.result_loaded.emit(rows)
            self.log_message.emit(f"已加载 {len(rows)} 条历史结果: {os.path.basename(self.filepath)}")


# ===================================================================
# 主窗口
# ===================================================================
class MainWindow(QMainWindow):
    """向上趋势选股系统主界面。"""

    # ---- 样式表 ----
    STYLE = """
    QMainWindow {
        background-color: #f5f5f5;
    }
    QGroupBox {
        font-weight: bold;
        border: 1px solid #cccccc;
        border-radius: 6px;
        margin-top: 10px;
        padding-top: 16px;
        background-color: #ffffff;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
    }
    QPushButton {
        border: 1px solid #bbbbbb;
        border-radius: 4px;
        padding: 6px 16px;
        background-color: #e6e6e6;
        min-height: 24px;
    }
    QPushButton:hover {
        background-color: #d5d5d5;
    }
    QPushButton:pressed {
        background-color: #c0c0c0;
    }
    QPushButton#btnStart {
        background-color: #4CAF50;
        color: white;
        border: none;
    }
    QPushButton#btnStart:hover {
        background-color: #45a049;
    }
    QPushButton#btnStop {
        background-color: #f44336;
        color: white;
        border: none;
    }
    QPushButton#btnStop:hover {
        background-color: #da190b;
    }
    QTableWidget {
        gridline-color: #e0e0e0;
        border: 1px solid #cccccc;
        border-radius: 4px;
        background-color: #ffffff;
    }
    QHeaderView::section {
        background-color: #f0f0f0;
        border: 1px solid #dddddd;
        padding: 4px;
        font-weight: bold;
    }
    QTextEdit {
        border: 1px solid #cccccc;
        border-radius: 4px;
        background-color: #1e1e1e;
        color: #d4d4d4;
        font-family: Consolas, Courier New, monospace;
    }
    QProgressBar {
        border: 1px solid #cccccc;
        border-radius: 4px;
        text-align: center;
        background-color: #e0e0e0;
        height: 22px;
    }
    QProgressBar::chunk {
        background-color: #4CAF50;
        border-radius: 3px;
    }
    """

    def __init__(self):
        super().__init__()
        self._worker = None
        self._current_image_path = None
        self._matched_count = 0
        self._init_ui()
        self._connect_signals()
        
        # 自动加载断点索引
        try:
            checkpoint = StockUpward.load_checkpoint()
            self.spin_start_idx.setValue(checkpoint)
            self._append_log(f"已自动加载断点索引: {checkpoint}")
        except Exception as e:
            print(f"自动加载断点索引失败: {e}")

    # ------------------------------------------------------------------
    def _init_ui(self):
        self.setWindowTitle("向上趋势选股系统 v1.0")
        self.resize(1280, 800)

        # --- 中央部件 ---
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(10, 6, 10, 6)

        # --- 横向分割: 左(参数) | 右(结果+K线+日志) ---
        splitter = QSplitter(Qt.Horizontal)

        # ---- 左侧面板 ----
        left_widget = self._build_left_panel()
        splitter.addWidget(left_widget)

        # ---- 右侧面板 ----
        right_widget = self._build_right_panel()
        splitter.addWidget(right_widget)

        splitter.setStretchFactor(0, 0)  # 左侧不拉伸
        splitter.setStretchFactor(1, 1)  # 右侧拉伸
        splitter.setSizes([280, 960])

        main_layout.addWidget(splitter, 1)

        # --- 底部: 进度条 + 状态 ---
        self._build_bottom_bar(main_layout)

        # --- 状态栏 ---
        self.statusBar().showMessage("就绪")

        self.setStyleSheet(self.STYLE)

    # ------------------------------------------------------------------
    def _build_left_panel(self):
        """左侧参数面板。"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(8)

        # ---- 参数组 ----
        grp_params = QGroupBox("扫描参数")
        form = QFormLayout(grp_params)
        form.setSpacing(6)

        self.edit_start_date = QLineEdit("20250102")
        self.edit_start_date.setToolTip("数据开始日期 (YYYYMMDD)")
        form.addRow("开始日期:", self.edit_start_date)

        self.spin_workers = QSpinBox()
        self.spin_workers.setRange(1, 50)
        self.spin_workers.setValue(10)
        self.spin_workers.setToolTip("并发线程数")
        form.addRow("线程数:", self.spin_workers)

        self.spin_start_idx = QSpinBox()
        self.spin_start_idx.setRange(0, 99999)
        self.spin_start_idx.setValue(0)
        self.spin_start_idx.setToolTip("起始股票索引(用于断点续扫)")
        form.addRow("起始索引:", self.spin_start_idx)

        # ---- 阈值组 ----
        grp_thresh = QGroupBox("筛选阈值")
        thr_form = QFormLayout(grp_thresh)
        thr_form.setSpacing(6)

        self.spin_long_days = QSpinBox()
        self.spin_long_days.setRange(5, 120)
        self.spin_long_days.setValue(30)
        thr_form.addRow("长期天数:", self.spin_long_days)

        self.spin_long_thresh = QSpinBox()
        self.spin_long_thresh.setRange(1, 120)
        self.spin_long_thresh.setValue(23)
        thr_form.addRow("长期达标:", self.spin_long_thresh)

        self.spin_short_days = QSpinBox()
        self.spin_short_days.setRange(1, 30)
        self.spin_short_days.setValue(5)
        thr_form.addRow("短期天数:", self.spin_short_days)

        self.spin_short_thresh = QSpinBox()
        self.spin_short_thresh.setRange(1, 30)
        self.spin_short_thresh.setValue(5)
        thr_form.addRow("短期达标:", self.spin_short_thresh)

        # ---- 按钮组 ----
        grp_btn = QGroupBox("操作")
        btn_layout = QVBoxLayout(grp_btn)
        btn_layout.setSpacing(8)

        self.btn_start = QPushButton("▶ 开始扫描")
        self.btn_start.setObjectName("btnStart")
        self.btn_start.setMinimumHeight(36)
        btn_layout.addWidget(self.btn_start)

        self.btn_stop = QPushButton("■ 停止")
        self.btn_stop.setObjectName("btnStop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.setMinimumHeight(36)
        btn_layout.addWidget(self.btn_stop)

        # 加载历史结果
        self.btn_load = QPushButton("📂 加载历史结果")
        self.btn_load.setMinimumHeight(32)
        btn_layout.addWidget(self.btn_load)

        # 打开数据目录
        self.btn_open_dir = QPushButton("📂 打开数据目录")
        self.btn_open_dir.setMinimumHeight(32)
        btn_layout.addWidget(self.btn_open_dir)

        btn_layout.addStretch()

        # 组装左侧
        layout.addWidget(grp_params)
        layout.addWidget(grp_thresh)
        layout.addWidget(grp_btn)
        layout.addStretch()
        return widget

    # ------------------------------------------------------------------
    def _build_right_panel(self):
        """右侧标签页: 结果 / K线 / 日志。"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()

        # ---- Tab 1: 筛选结果表 ----
        tab_result = QWidget()
        tab_layout = QVBoxLayout(tab_result)
        tab_layout.setContentsMargins(4, 4, 4, 4)

        self.lbl_result_count = QLabel("符合条件: 0 只")
        self.lbl_result_count.setStyleSheet("font-weight: bold; font-size: 13px; padding: 2px;")

        self.table_result = QTableWidget()
        self.table_result.setColumnCount(7)
        self.table_result.setHorizontalHeaderLabels([
            "代码", "名称", "20日振幅", "市盈率", "行业", "当日涨跌幅", "操作"
        ])
        self.table_result.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_result.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_result.setAlternatingRowColors(True)
        self.table_result.horizontalHeader().setStretchLastSection(True)
        self.table_result.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table_result.verticalHeader().setVisible(False)

        tab_layout.addWidget(self.lbl_result_count)
        tab_layout.addWidget(self.table_result, 1)
        self.tabs.addTab(tab_result, "📊 筛选结果")

        # ---- Tab 2: K线图 ----
        tab_kline = QWidget()
        kline_layout = QVBoxLayout(tab_kline)
        kline_layout.setContentsMargins(4, 4, 4, 4)

        self.lbl_kline_title = QLabel("点击右侧「查看K线」按钮查看 K 线图")
        self.lbl_kline_title.setAlignment(Qt.AlignCenter)
        self.lbl_kline_title.setStyleSheet("font-size: 13px; color: #666666; padding: 8px;")

        self.lbl_kline_image = QLabel()
        self.lbl_kline_image.setAlignment(Qt.AlignCenter)
        self.lbl_kline_image.setMinimumSize(500, 300)
        self.lbl_kline_image.setStyleSheet("background-color: #ffffff; border: 1px solid #dddddd;")

        kline_layout.addWidget(self.lbl_kline_title)
        kline_layout.addWidget(self.lbl_kline_image, 1)
        self.tabs.addTab(tab_kline, "📈 K线详情")

        # ---- Tab 3: 日志 ----
        tab_log = QWidget()
        log_layout = QVBoxLayout(tab_log)
        log_layout.setContentsMargins(4, 4, 4, 4)

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMinimumHeight(100)
        log_layout.addWidget(self.txt_log, 1)
        self.tabs.addTab(tab_log, "📝 运行日志")

        layout.addWidget(self.tabs)
        return widget

    # ------------------------------------------------------------------
    def _build_bottom_bar(self, parent_layout):
        """底部进度条。"""
        bar_layout = QVBoxLayout()
        bar_layout.setSpacing(2)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        bar_layout.addWidget(self.progress_bar)

        self.lbl_progress = QLabel("就绪")
        self.lbl_progress.setStyleSheet("color: #555555; font-size: 12px;")
        bar_layout.addWidget(self.lbl_progress)

        parent_layout.addLayout(bar_layout)

    # ------------------------------------------------------------------
    def _connect_signals(self):
        self.btn_start.clicked.connect(self._on_start_scan)
        self.btn_stop.clicked.connect(self._on_stop_scan)
        self.btn_load.clicked.connect(self._on_load_result)
        self.btn_open_dir.clicked.connect(self._on_open_data_dir)

    # ==============================================================
    # 槽函数
    # ==============================================================
    def _on_start_scan(self):
        """开始扫描。"""
        if self._worker and self._worker.isRunning():
            QMessageBox.warning(self, "提示", "扫描正在进行中")
            return

        # 收集参数
        params = {
            "start_date": self.edit_start_date.text().strip() or "20250102",
            "max_workers": self.spin_workers.value(),
            "start_index": self.spin_start_idx.value(),
            "end_date": datetime.today().strftime("%Y%m%d"),
            "upward_long_days": self.spin_long_days.value(),
            "upward_long_threshold": self.spin_long_thresh.value(),
            "upward_short_days": self.spin_short_days.value(),
            "upward_short_threshold": self.spin_short_thresh.value(),
            "data_offset": 0,  # 默认对应 scanner 中的 DATA_OFFSET 为 0
        }

        # 清空之前的结果
        self.table_result.setRowCount(0)
        self._matched_count = 0
        self.lbl_result_count.setText("符合条件: 0 只")
        self._clear_kline()

        # 创建并启动工作线程
        self._worker = ScanWorker(params)
        self._worker.progress_updated.connect(self._on_progress)
        self._worker.stock_matched.connect(self._on_stock_matched)
        self._worker.log_message.connect(self._append_log)
        self._worker.scan_finished.connect(self._on_scan_finished)
        self._worker.scan_error.connect(self._on_scan_error)

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.progress_bar.setValue(0)

        self._append_log("=" * 50)
        self._append_log(f"扫描启动 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self._worker.start()

    def _on_stop_scan(self):
        """停止扫描。"""
        if self._worker:
            self._worker.stop()
            self._append_log("正在停止扫描 (等待当前任务完成)…")

    def _on_progress(self, current, total, name):
        """更新进度条。"""
        pct = int(current / total * 100) if total > 0 else 0
        self.progress_bar.setValue(pct)
        self.lbl_progress.setText(f"{name}  ({current}/{total})")
        self.statusBar().showMessage(f"扫描中… {current}/{total}")

    def _on_stock_matched(self, info: dict):
        """符合条件的股票，加入结果表。"""
        row = self.table_result.rowCount()
        self.table_result.insertRow(row)

        self.table_result.setItem(row, 0, QTableWidgetItem(info["code"]))
        self.table_result.setItem(row, 1, QTableWidgetItem(info["name"]))
        self.table_result.setItem(row, 2, QTableWidgetItem(f"{info['amplitude']:.2%}"))
        self.table_result.setItem(row, 3, QTableWidgetItem(str(info["pe_ratio"])))
        self.table_result.setItem(row, 4, QTableWidgetItem(info["industry"]))
        self.table_result.setItem(row, 5, QTableWidgetItem(f"{info['change_pct']:.2f}%"))

        # 操作按钮 (查看K线)
        btn_view = QPushButton("查看K线")
        btn_view.clicked.connect(lambda _, c=info["code"], n=info["name"]: self._show_kline(c, n, show_toast=True))
        self.table_result.setCellWidget(row, 6, btn_view)

        self._matched_count += 1
        self.lbl_result_count.setText(f"符合条件: {self._matched_count} 只")

    def _on_scan_finished(self, elapsed, matched_count):
        """扫描完成。"""
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.statusBar().showMessage(f"扫描完成 | {matched_count} 只匹配 | 耗时 {elapsed:.1f} 秒")
        self._append_log(f"扫描完成, 共 {matched_count} 只, 耗时 {elapsed:.1f} 秒")

    def _on_scan_error(self, msg):
        """扫描异常。"""
        self._append_log(f"[错误] {msg}")
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def _on_open_data_dir(self):
        """打开数据及结果保存目录。"""
        import platform
        import subprocess
        try:
            if platform.system() == "Windows":
                os.startfile(DATA_DIR)
            elif platform.system() == "Darwin":  # macOS
                subprocess.Popen(["open", DATA_DIR])
            else:  # Linux
                subprocess.Popen(["xdg-open", DATA_DIR])
            self._append_log(f"已打开数据目录: {DATA_DIR}")
        except Exception as e:
            self._append_log(f"无法打开目录: {e}")

    # --------------------------------------------------------------
    def _on_load_result(self):
        """加载历史结果文件。"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "选择历史结果", RESULT_DIR, "CSV 文件 (*.csv)"
        )
        if not filepath:
            return

        self._load_worker = LoadResultWorker(filepath)
        self._load_worker.result_loaded.connect(self._on_result_loaded)
        self._load_worker.log_message.connect(self._append_log)
        self._load_worker.load_error.connect(lambda m: self._append_log(f"[错误] {m}"))
        self._load_worker.start()
        self._append_log(f"正在加载: {filepath}")

    def _on_result_loaded(self, rows):
        """将历史结果填充到表格。"""
        self.table_result.setRowCount(0)
        for row_data in rows:
            row = self.table_result.rowCount()
            self.table_result.insertRow(row)
            for col, val in enumerate(row_data[:6]):
                self.table_result.setItem(row, col, QTableWidgetItem(val.strip()))
            # 操作按钮
            if len(row_data) >= 2:
                code, name = row_data[0].strip(), row_data[1].strip()
                btn_view = QPushButton("查看K线")
                btn_view.clicked.connect(lambda _, c=code, n=name: self._show_kline(c, n, show_toast=True))
                self.table_result.setCellWidget(row, 6, btn_view)

        self._matched_count = len(rows)
        self.lbl_result_count.setText(f"历史结果: {len(rows)} 条")

    # --------------------------------------------------------------

    def _show_kline(self, code, name, show_toast=False):
        """从 kline_charts 目录加载对应 PNG 显示。"""
        kline_dir = os.path.join(CURRENT_DIR, "kline_charts")
        candidates = [
            os.path.join(kline_dir, f"{code}{name}.png"),
            os.path.join(kline_dir, f"{code} {name}.png"),
        ]
        for path in candidates:
            if os.path.exists(path):
                self._display_image(path, f"{code} {name} K线图")
                return

        msg = f"未找到 {code} {name} 的 K线图"
        self._append_log(msg)
        self._clear_kline(f"{msg}，请先运行扫描")
        if show_toast:
            self.show_toast(msg)

    def _display_image(self, path, title=None):
        """在 K线标签页显示图片。"""
        self._current_image_path = path
        if title:
            self._current_image_title = title
            self.lbl_kline_title.setText(f"📈 {title}")
        
        self._update_kline_display()
        self.tabs.setCurrentIndex(1)  # 切换到K线标签页

    def _update_kline_display(self):
        """根据当前 label 尺寸动态自适应缩放显示 K线图片。"""
        if not getattr(self, "_current_image_path", None):
            return
        pixmap = QPixmap(self._current_image_path)
        if pixmap.isNull():
            return
            
        max_w = self.lbl_kline_image.width() or 600
        max_h = self.lbl_kline_image.height() or 400
        
        # 留白 4px 避免拉大窗口时触发无限调整的布局死循环
        if max_w > 10 and max_h > 10:
            scaled = pixmap.scaled(max_w - 4, max_h - 4, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.lbl_kline_image.setPixmap(scaled)

    def _clear_kline(self, msg=None):
        """清空 K线 显示。"""
        self.lbl_kline_image.clear()
        self.lbl_kline_title.setText(msg or "点击右侧「查看K线」按钮查看 K 线图")
        self._current_image_path = None
        self._current_image_title = None

    def resizeEvent(self, event):
        """窗口尺寸变动事件，动态触发 K线图自适应重绘缩放。"""
        super().resizeEvent(event)
        if getattr(self, "_current_image_path", None):
            self._update_kline_display()

    def show_toast(self, message):
        """在窗口中央显示一个渐隐的气泡通知（Toast）。"""
        toast = QLabel(message, self)
        toast.setAlignment(Qt.AlignCenter)
        toast.setStyleSheet("""
            background-color: rgba(40, 40, 40, 220);
            color: #ffffff;
            border: 1px solid rgba(255, 255, 255, 30);
            border-radius: 20px;
            padding: 10px 24px;
            font-family: 'Microsoft YaHei UI', sans-serif;
            font-size: 13px;
        """)
        toast.adjustSize()
        
        # 居中定位
        x = (self.width() - toast.width()) // 2
        y = (self.height() - toast.height()) // 2
        toast.move(x, y)
        toast.show()
        
        # 渐隐动画
        opacity_effect = QGraphicsOpacityEffect(toast)
        toast.setGraphicsEffect(opacity_effect)
        
        anim = QPropertyAnimation(opacity_effect, b"opacity")
        anim.setDuration(2500)  # 持续 2.5 秒
        anim.setStartValue(1.0)
        anim.setKeyValueAt(0.6, 1.0)  # 前 1.5 秒保持完全可见
        anim.setEndValue(0.0)         # 后 1.0 秒渐隐
        anim.setEasingCurve(QEasingCurve.OutQuad)
        
        # 自动销毁 Label
        anim.finished.connect(toast.deleteLater)
        
        # 保持引用，防止垃圾回收
        if not hasattr(self, "_toast_anims"):
            self._toast_anims = []
        self._toast_anims.append(anim)
        anim.finished.connect(lambda: self._toast_anims.remove(anim) if anim in self._toast_anims else None)
        
        anim.start()

    # --------------------------------------------------------------
    def _append_log(self, msg):
        """追加日志。"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.txt_log.append(f"[{timestamp}] {msg}")
        # 自动滚动到底部
        cursor = self.txt_log.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.txt_log.setTextCursor(cursor)

        # 如果当前在日志标签页，不用切换；否则保持当前标签
        # 同时也输出到控制台
        print(f"[{timestamp}] {msg}")


# ===================================================================
# 入口
# ===================================================================
def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    font = QFont("Microsoft YaHei UI", 9)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
