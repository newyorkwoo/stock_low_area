import flet as ft
import pandas as pd
import json
import mplfinance as mpf
import warnings
import matplotlib
import time
import os
import glob

matplotlib.use("agg")
warnings.filterwarnings("ignore", category=UserWarning)

matplotlib.rcParams['font.sans-serif'] = ['PingFang TC', 'Arial Unicode MS', 'Heiti TC', 'sans-serif']
matplotlib.rcParams['axes.unicode_minus'] = False

def load_json(filepath):
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        df = pd.DataFrame(data, columns=['Date', 'Open', 'Close', 'Low', 'High', 'Volume', 'VIX', 'RSI60'])
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        return df
    except Exception as e:
        print(f"無法載入 {filepath}: {e}")
        return None

def find_drawdowns(df, threshold=0.10):
    running_max = df['Close'].cummax()
    drawdown = (df['Close'] - running_max) / running_max
    is_in_drawdown = drawdown <= -threshold
    
    regions = []
    in_region = False
    start = None
    
    for date, val in is_in_drawdown.items():
        if val and not in_region:
            in_region = True
            start = date
        elif not val and in_region:
            in_region = False
            regions.append((start, date))
            
    if in_region:
        regions.append((start, df.index[-1]))
            
    return regions

def main(page: ft.Page):
    page.title = "市場指標分析與回撤監控 (iOS / iPadOS 支援版)"
    page.padding = 30
    page.theme_mode = ft.ThemeMode.LIGHT
    
    twii_data = load_json('twii_data.json')
    nasdaq_data = load_json('nasdaq_data.json')
    
    chart_container = ft.Container(expand=True, padding=10)
    
    # 紀錄目前使用的資料表
    current_df = None
    
    def render_chart():
        nonlocal current_df
        if current_df is None or current_df.empty:
            chart_container.content = ft.Text("⚠️ 找不到資料。")
            page.update()
            return
            
        start_idx = int(date_slider.start_value)
        end_idx = int(date_slider.end_value)
        
        if end_idx <= start_idx:
            end_idx = start_idx + 1
            
        # 根據滑桿範圍切片資料表 (實現真實的圖表 K線 放大/平移！)
        sliced_df = current_df.iloc[start_idx:end_idx]
        
        drawdown_regions = find_drawdowns(sliced_df, 0.10)

        mc = mpf.make_marketcolors(up='r', down='g', edge='inherit', wick='inherit', volume='in', inherit=True)
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle=":", y_on_right=False, base_mpf_style='yahoo')
        
        ap = [
            mpf.make_addplot(sliced_df['VIX'], panel=1, color='purple', ylabel='VIX'),
            mpf.make_addplot(sliced_df['RSI60'], panel=2, color='orange', ylabel='RSI (60)')
        ]
        
        fig, axlist = mpf.plot(sliced_df, type='candle', addplot=ap,
                               volume=False, style=s, panel_ratios=(4, 1, 1), 
                               returnfig=True, tight_layout=True)
        
        fig.suptitle(f"{index_selector.value} Historical Trend (with >10% Drawdowns, VIX & RSI)", fontsize=16, fontweight='bold')
        
        main_ax = axlist[0]
        date_to_idx = {date: idx for idx, date in enumerate(sliced_df.index)}
        
        for start, end in drawdown_regions:
            start_idx_ax = date_to_idx.get(start)
            end_idx_ax = date_to_idx.get(end)
            if start_idx_ax is not None and end_idx_ax is not None:
                main_ax.axvspan(start_idx_ax, end_idx_ax, color='green', alpha=0.15)
        
        for f in glob.glob("output_charts/chart_*.png"):
            try:
                os.remove(f)
            except:
                pass
                
        os.makedirs("output_charts", exist_ok=True)
        chart_filename = f"chart_{int(time.time() * 1000)}.png"
        # DPI 設為 150，兼顧清晰度與繪圖速度
        fig.savefig(f"output_charts/{chart_filename}", format="png", transparent=True, bbox_inches="tight", dpi=150)
        
        img = ft.Image(src=chart_filename, expand=True, fit="contain")
        
        # InteractiveViewer 屬性 boundary_margin=ft.margin.all(float('inf')) 讓滑鼠在圖片上拖曳時不會卡在邊界
        chart_container.content = ft.InteractiveViewer(
            content=img,
            max_scale=10.0,
            min_scale=0.5,
            boundary_margin=ft.margin.all(float('inf')), 
            expand=True
        )
        
        # 更新文字標籤
        start_date = sliced_df.index[0].strftime('%Y-%m-%d')
        end_date = sliced_df.index[-1].strftime('%Y-%m-%d')
        date_label.value = f"目前顯示區間: {start_date} ~ {end_date}"
        
        page.update()
        
        import matplotlib.pyplot as plt
        plt.close(fig)

    def update_index(e=None):
        nonlocal current_df
        current_df = twii_data if index_selector.value == "TWII" else nasdaq_data
        
        if current_df is not None and not current_df.empty:
            max_idx = len(current_df) - 1
            date_slider.min = 0
            date_slider.max = max_idx
            date_slider.end_value = max_idx
            # 預設看最後 300 根 K 線 (大約一年多)
            date_slider.start_value = max_idx - 300 if max_idx > 300 else 0
            
            render_chart()

    def on_slider_change_end(e):
        # 拖拉結束後才重新繪圖，避免卡頓
        render_chart()
        
    def on_slider_change(e):
        # 拖拉過程中更新文字標籤，提供即時回饋
        if current_df is not None and not current_df.empty:
            try:
                s_idx = int(e.control.start_value)
                e_idx = int(e.control.end_value)
                if e_idx <= s_idx: e_idx = s_idx + 1
                if e_idx >= len(current_df): e_idx = len(current_df) - 1
                start_date = current_df.index[s_idx].strftime('%Y-%m-%d')
                end_date = current_df.index[e_idx].strftime('%Y-%m-%d')
                date_label.value = f"滑動選擇中... ({start_date} ~ {end_date})"
                date_label.update()
            except:
                pass

    index_selector = ft.RadioGroup(
        content=ft.Row([
            ft.Radio(value="TWII", label="TWII (台灣加權指數)"),
            ft.Radio(value="NASDAQ", label="NASDAQ (納斯達克)"),
        ]),
        value="TWII",
        on_change=update_index
    )
    
    date_slider = ft.RangeSlider(
        min=0, max=1000,
        start_value=0, end_value=1000,
        on_change_end=on_slider_change_end,
        on_change=on_slider_change
    )
    
    date_label = ft.Text("目前顯示區間: ", size=16, weight="bold", color="blue")
    
    # 控制面板 (放下方)
    control_panel = ft.Container(
        content=ft.Column([
            ft.Row([ft.Text("📊 K線時間軸平移與縮放控制區:", weight="bold", size=16), date_label]),
            date_slider
        ]),
        padding=10,
        bgcolor="#eceff1", # BLUE_GREY_50 equivalent hex
        border_radius=10
    )
    
    page.add(
        ft.Row([
            ft.Text("市場底部指標分析工具", size=24, weight=ft.FontWeight.BOLD),
            ft.Container(width=20),
            ft.Text("選擇觀看指數:", size=16, weight=ft.FontWeight.W_500),
            index_selector
        ], alignment=ft.MainAxisAlignment.START),
        ft.Divider(),
        chart_container,
        control_panel
    )
    
    # 初始載入
    update_index()

if __name__ == "__main__":
    ft.app(target=main, assets_dir="output_charts")
