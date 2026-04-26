import streamlit as st
import streamlit.components.v1 as components
import json
import os
from export_data import prepare_data

st.set_page_config(page_title="歷史指數互動式看板", layout="wide")

st.title("📊 歷史指數互動式看板")
st.markdown("本系統提供台灣加權指數與那斯達克指數的互動式 K 線圖，包含季線、年線、動態支撐及**恐慌抄底/貪婪逃頂**等獨家指標。")

col1, col2 = st.columns([1, 4])
with col1:
    market_options = {"twii": "台灣加權指數 (^TWII)", "nasdaq": "那斯達克綜合指數 (^IXIC)"}
    selected_market = st.selectbox("選擇市場", options=list(market_options.keys()), format_func=lambda x: market_options[x])

    if st.button("更新最新歷史資料 (需時數秒)"):
        with st.spinner("正在從 Yahoo Finance 抓取最新資料..."):
            prepare_data("twii", "^TWII")
            prepare_data("nasdaq", "^IXIC")
        st.success("資料更新完成！")

# 確保資料存在
data_file = f"{selected_market}_data.json"
if not os.path.exists(data_file):
    with st.spinner("首次載入，正在下載歷史資料..."):
        index_symbol = "^TWII" if selected_market == "twii" else "^IXIC"
        prepare_data(selected_market, index_symbol)

# 讀取 JSON 資料
with open(data_file, "r", encoding="utf-8") as f:
    market_data_json = f.read()

# ECharts HTML 模板 (基於原本的 index.html 改寫，去除 fetch 與 Header)
html_template = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            margin: 0; padding: 0;
            background-color: #121212;
            color: #ffffff;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            overflow: hidden; /* 防止出現雙滾動條 */
        }}
        #chart-container {{ width: 100vw; height: 100vh; }}
    </style>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
</head>
<body>
<div id="chart-container"></div>
<script>
    const chartDom = document.getElementById('chart-container');
    const myChart = echarts.init(chartDom, 'dark', {{ renderer: 'canvas' }});

    const upColor = '#ec0000', upBorderColor = '#8A0000';
    const downColor = '#00da3c', downBorderColor = '#008F28';

    // ─── 資料解析 ──────────────────────────────────────────────────────────────
    function splitData(rawData) {{
        let categoryData = [], values = [], vixData = [], rsiData = [];
        for (let i = 0; i < rawData.length; i++) {{
            const item = rawData[i];
            categoryData.push(item[0]);
            values.push([item[1], item[2], item[3], item[4]]);
            vixData.push(item[6]);
            rsiData.push(item[7]);
        }}
        return {{ categoryData, values, vixData, rsiData }};
    }}

    // ─── 移動平均 ──────────────────────────────────────────────────────────────
    function calculateMA(dayCount, data) {{
        let result = [];
        for (let i = 0, len = data.length; i < len; i++) {{
            if (i < dayCount - 1) {{ result.push('-'); continue; }}
            let sum = 0;
            for (let j = 0; j < dayCount; j++) sum += data[i - j][1];
            result.push((sum / dayCount).toFixed(2));
        }}
        return result;
    }}

    // ─── 波段高低點標示 ──────────────────────────────────────────────────────────────
    function getSwingRegions(chartData) {{
        let markArea = [];
        let markPoint = [];
        let state = 1, peakIdx = 0, troughIdx = 0;
        const REVERSAL = 0.05; // 5% 反轉
        for (let i = 0; i < chartData.values.length; i++) {{
            let high = chartData.values[i][3], low = chartData.values[i][2], close = chartData.values[i][1];
            if (state === 1) {{
                if (high > chartData.values[peakIdx][3]) peakIdx = i;
                if ((chartData.values[peakIdx][3] - close) / chartData.values[peakIdx][3] >= REVERSAL) {{
                    state = -1; troughIdx = i;
                }}
            }} else {{
                if (low < chartData.values[troughIdx][2]) troughIdx = i;
                if ((close - chartData.values[troughIdx][2]) / chartData.values[troughIdx][2] >= REVERSAL) {{
                    let drop = (chartData.values[peakIdx][3] - chartData.values[troughIdx][2]) / chartData.values[peakIdx][3];
                    if (drop >= 0.08) {{ // 跌幅大於 8% 的波段
                        markArea.push([
                            {{ xAxis: chartData.categoryData[peakIdx], itemStyle: {{ color: 'rgba(239, 68, 68, 0.15)' }} }},
                            {{ xAxis: chartData.categoryData[troughIdx] }}
                        ]);
                        markPoint.push({{
                            name: '波段高點',
                            coord: [chartData.categoryData[peakIdx], chartData.values[peakIdx][3]],
                            value: chartData.values[peakIdx][3].toFixed(0),
                            symbol: 'path://M12 2L22 20H2L12 2Z',
                            symbolSize: 8,
                            symbolRotate: 180,
                            symbolOffset: [0, -15],
                            itemStyle: {{ color: '#facc15' }},
                            label: {{ color: '#facc15', position: 'top', fontSize: 10 }}
                        }});
                        markPoint.push({{
                            name: '波段低點',
                            coord: [chartData.categoryData[troughIdx], chartData.values[troughIdx][2]],
                            value: chartData.values[troughIdx][2].toFixed(0) + '\\n(-' + (drop * 100).toFixed(1) + '%)',
                            symbol: 'path://M12 2L22 20H2L12 2Z',
                            symbolSize: 8,
                            symbolRotate: 0,
                            symbolOffset: [0, 15],
                            itemStyle: {{ color: '#00da3c' }},
                            label: {{ color: '#00da3c', position: 'bottom', fontSize: 10, align: 'center', lineHeight: 12 }}
                        }});
                    }}
                    state = 1; peakIdx = i;
                }}
            }}
        }}
        if (state === -1) {{
            let drop = (chartData.values[peakIdx][3] - chartData.values[troughIdx][2]) / chartData.values[peakIdx][3];
            if (drop >= 0.08) {{
                markArea.push([
                    {{ xAxis: chartData.categoryData[peakIdx], itemStyle: {{ color: 'rgba(239, 68, 68, 0.15)' }} }},
                    {{ xAxis: chartData.categoryData[troughIdx] }}
                ]);
                markPoint.push({{
                    name: '波段高點',
                    coord: [chartData.categoryData[peakIdx], chartData.values[peakIdx][3]],
                    value: chartData.values[peakIdx][3].toFixed(0),
                    symbol: 'path://M12 2L22 20H2L12 2Z',
                    symbolSize: 8,
                    symbolRotate: 180,
                    symbolOffset: [0, -15],
                    itemStyle: {{ color: '#facc15' }},
                    label: {{ color: '#facc15', position: 'top', fontSize: 10 }}
                }});
                markPoint.push({{
                    name: '波段低點',
                    coord: [chartData.categoryData[troughIdx], chartData.values[troughIdx][2]],
                    value: chartData.values[troughIdx][2].toFixed(0) + '\\n(-' + (drop * 100).toFixed(1) + '%)',
                    symbol: 'path://M12 2L22 20H2L12 2Z',
                    symbolSize: 8,
                    symbolRotate: 0,
                    symbolOffset: [0, 15],
                    itemStyle: {{ color: '#00da3c' }},
                    label: {{ color: '#00da3c', position: 'bottom', fontSize: 10, align: 'center', lineHeight: 12 }}
                }});
            }}
        }}
        return {{ markArea, markPoint }};
    }}

    // ─── 領先預測指標：恐慌抄底大頭針 (基於 VIX/RSI 恐慌指數) ─────────────────────────
    function getPredictiveBottoms(chartData, panicScores) {{
        let points = [];
        for (let i = 120; i < chartData.values.length; i++) {{
            let score = parseFloat(panicScores[i]);
            let prevScore = parseFloat(panicScores[i-1]);
            let low = chartData.values[i][2];
            
            if (prevScore > 35 && score < prevScore) {{
                if (points.length === 0 || i - points[points.length - 1].index > 10) {{
                    if (prevScore > 90) {{
                        points.push({{
                            name: '百年鑽石底', coord: [chartData.categoryData[i], low], value: '終極大底',
                            index: i, symbol: 'pin', symbolSize: 55, symbolRotate: 180, symbolOffset: [0, -10],
                            itemStyle: {{ color: '#fbbf24' }}, label: {{ fontSize: 10, color: '#000', fontWeight: 'bold' }}
                        }});
                    }} else if (prevScore > 50) {{
                        points.push({{
                            name: '一般股災底', coord: [chartData.categoryData[i], low], value: '恐慌反轉',
                            index: i, symbol: 'pin', symbolSize: 40, symbolRotate: 180, symbolOffset: [0, -10],
                            itemStyle: {{ color: '#ef4444' }}, label: {{ fontSize: 9, color: '#fff', fontWeight: 'bold' }}
                        }});
                    }} else {{
                        points.push({{
                            name: '短線超跌底', coord: [chartData.categoryData[i], low], value: '小幅修正',
                            index: i, symbol: 'pin', symbolSize: 25, symbolRotate: 180, symbolOffset: [0, -10],
                            itemStyle: {{ color: '#f97316' }}, label: {{ fontSize: 8, color: '#fff', fontWeight: 'bold' }}
                        }});
                    }}
                }}
            }}
        }}
        return points;
    }}

    // ─── 領先預測指標：貪婪逃頂大頭針 (基於 RSI/VIX 貪婪指數) ─────────────────────────
    function getPredictiveTops(chartData, greedScores) {{
        let points = [];
        for (let i = 120; i < chartData.values.length; i++) {{
            let score = parseFloat(greedScores[i]);
            let prevScore = parseFloat(greedScores[i-1]);
            let high = chartData.values[i][3];
            
            if (prevScore > 60 && score < prevScore) {{
                if (points.length === 0 || i - points[points.length - 1].index > 10) {{
                    if (prevScore > 90) {{
                        points.push({{
                            name: '極度貪婪', coord: [chartData.categoryData[i], high], value: '閃崩前兆',
                            index: i, symbol: 'pin', symbolSize: 55, symbolOffset: [0, 10],
                            itemStyle: {{ color: '#ec4899' }}, label: {{ fontSize: 10, color: '#fff', fontWeight: 'bold' }}
                        }});
                    }} else if (prevScore > 70) {{
                        points.push({{
                            name: '高點警戒', coord: [chartData.categoryData[i], high], value: '貪婪反轉',
                            index: i, symbol: 'pin', symbolSize: 40, symbolOffset: [0, 10],
                            itemStyle: {{ color: '#10b981' }}, label: {{ fontSize: 9, color: '#fff', fontWeight: 'bold' }}
                        }});
                    }} else {{
                        points.push({{
                            name: '短線過熱', coord: [chartData.categoryData[i], high], value: '小幅過熱',
                            index: i, symbol: 'pin', symbolSize: 25, symbolOffset: [0, 10],
                            itemStyle: {{ color: '#3b82f6' }}, label: {{ fontSize: 8, color: '#fff', fontWeight: 'bold' }}
                        }});
                    }}
                }}
            }}
        }}
        return points;
    }}

    // ─── 計算動態共振支撐線 ────────────────────────────────────────────────────────
    function getDynamicSupports(chartData, ma240Data) {{
        let supportHigh = [];
        let supportMA = [];
        for (let i = 0; i < chartData.values.length; i++) {{
            if (i < 120) {{
                supportHigh.push('-');
                supportMA.push('-');
                continue;
            }}
            let recentHigh = 0;
            for (let j = i - 120; j <= i; j++) {{
                if (chartData.values[j][3] > recentHigh) recentHigh = chartData.values[j][3];
            }}
            let ma240 = parseFloat(ma240Data[i]);
            
            supportHigh.push((recentHigh * 0.88).toFixed(2));
            if (!isNaN(ma240)) {{
                supportMA.push((ma240 * 0.88).toFixed(2));
            }} else {{
                supportMA.push('-');
            }}
        }}
        return {{ supportHigh, supportMA }};
    }}

    // ─── 綜合恐慌抄底指數 (VIX / RSI 正規化) ────────────────────────────────────────────────────────
    function calculatePanicScore(chartData, ma60Data, ma240Data) {{
        let scores = [];
        for (let i = 0; i < chartData.values.length; i++) {{
            if (i < 120) {{ scores.push('-'); continue; }}
            let rsi = chartData.rsiData[i];
            let vix = chartData.vixData[i];
            if (rsi === 0) rsi = 1;
            let ratio = vix / rsi;
            let score = ratio * 60;
            score = Math.max(0, score);
            scores.push(score.toFixed(1));
        }}
        return scores;
    }}

    // ─── 貪婪逃頂指數 (RSI / VIX 正規化) ────────────────────────────────────────────────────────
    function calculateGreedScore(chartData) {{
        let scores = [];
        for (let i = 0; i < chartData.values.length; i++) {{
            if (i < 120) {{ scores.push('-'); continue; }}
            let rsi = chartData.rsiData[i];
            let vix = chartData.vixData[i];
            if (vix === 0) vix = 1; // 避免除以零
            let ratio = rsi / vix;
            let score = ratio * 15;
            score = Math.max(0, score);
            scores.push(score.toFixed(1));
        }}
        return scores;
    }}

    // ─── 主繪圖函數 ────────────────────────────────────────────────────────────
    function renderChart(rawData) {{
        const chartData = splitData(rawData);
        const ma60Data  = calculateMA(60,  chartData.values);
        const ma240Data = calculateMA(240, chartData.values);
        const swingData = getSwingRegions(chartData);
        
        const dynamicSupports = getDynamicSupports(chartData, ma240Data);
        const panicScores = calculatePanicScore(chartData, ma60Data, ma240Data);
        const greedScores = calculateGreedScore(chartData);
        
        const predictiveBottoms = getPredictiveBottoms(chartData, panicScores);
        const predictiveTops = getPredictiveTops(chartData, greedScores);

        const option = {{
            backgroundColor: '#121212',
            animation: false,
            legend: {{
                data: ['K線', '季線 (MA60)', '年線 (MA240)', '波段支撐 (-12%)', '年線支撐 (-12%)', 'VIX', 'RSI(60)', '恐慌抄底指數', '貪婪逃頂指數'],
                inactiveColor: '#777',
                textStyle: {{ color: '#fff' }},
                top: 0
            }},
            tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'cross' }} }},
            axisPointer: {{ link: [{{ xAxisIndex: 'all' }}], label: {{ backgroundColor: '#777' }} }},
            visualMap: {{ show: false }},
            grid: [
                {{ left: '3%', right: '3%', top: '5%',  height: '38%', containLabel: true }},
                {{ left: '3%', right: '3%', top: '46%', height: '10%', containLabel: true }},
                {{ left: '3%', right: '3%', top: '59%', height: '10%', containLabel: true }},
                {{ left: '3%', right: '3%', top: '72%', height: '11%', containLabel: true }},
                {{ left: '3%', right: '3%', top: '86%', height: '11%', containLabel: true }}
            ],
            xAxis: [
                {{ type: 'category', data: chartData.categoryData, scale: true, boundaryGap: false,
                  axisLine: {{ onZero: false }}, splitLine: {{ show: false }}, min: 'dataMin', max: 'dataMax', axisPointer: {{ z: 100 }} }},
                {{ type: 'category', gridIndex: 1, data: chartData.categoryData, scale: true, boundaryGap: false,
                  axisLine: {{ onZero: false }}, axisTick: {{ show: false }}, splitLine: {{ show: false }}, axisLabel: {{ show: false }}, min: 'dataMin', max: 'dataMax' }},
                {{ type: 'category', gridIndex: 2, data: chartData.categoryData, scale: true, boundaryGap: false,
                  axisLine: {{ onZero: false }}, axisTick: {{ show: false }}, splitLine: {{ show: false }}, axisLabel: {{ show: false }}, min: 'dataMin', max: 'dataMax' }},
                {{ type: 'category', gridIndex: 3, data: chartData.categoryData, scale: true, boundaryGap: false,
                  axisLine: {{ onZero: false }}, axisTick: {{ show: false }}, splitLine: {{ show: false }}, axisLabel: {{ show: false }}, min: 'dataMin', max: 'dataMax' }},
                {{ type: 'category', gridIndex: 4, data: chartData.categoryData, scale: true, boundaryGap: false,
                  axisLine: {{ onZero: false }}, axisTick: {{ show: false }}, splitLine: {{ show: false }}, axisLabel: {{ show: false }}, min: 'dataMin', max: 'dataMax' }}
            ],
            yAxis: [
                {{ scale: true, splitArea: {{ show: true, areaStyle: {{ color: ['rgba(255,255,255,0.02)', 'rgba(255,255,255,0.05)'] }} }}, splitLine: {{ show: false }} }},
                {{ gridIndex: 1, scale: true, splitNumber: 2, splitLine: {{ show: false }}, axisLabel: {{ formatter: '{{value}}' }} }},
                {{ gridIndex: 2, scale: true, splitNumber: 2, splitLine: {{ show: false }}, axisLabel: {{ formatter: '{{value}}' }} }},
                {{ gridIndex: 3, scale: false, min: 0, splitNumber: 2, splitLine: {{ show: true, lineStyle: {{ color: '#333' }} }}, axisLabel: {{ formatter: '{{value}}' }} }},
                {{ gridIndex: 4, scale: false, min: 0, splitNumber: 2, splitLine: {{ show: true, lineStyle: {{ color: '#333' }} }}, axisLabel: {{ formatter: '{{value}}' }} }}
            ],
            dataZoom: [
                {{
                    type: 'inside', xAxisIndex: [0, 1, 2, 3, 4],
                    start: 85, end: 100,
                    zoomOnMouseWheel: true, moveOnMouseMove: true, moveOnMouseWheel: false, preventDefaultMouseMove: true
                }},
                {{
                    show: true, type: 'slider', xAxisIndex: [0, 1, 2, 3, 4],
                    bottom: '1%', height: 20, start: 85, end: 100,
                    textStyle: {{ color: '#8392A5', fontSize: 10 }},
                    borderColor: '#444', fillerColor: 'rgba(80,120,200,0.2)',
                    handleStyle: {{ color: '#aaa' }},
                    dataBackground: {{ lineStyle: {{ color: '#555' }}, areaStyle: {{ color: '#333' }} }}
                }}
            ],
            series: [
                {{
                    name: 'K線',
                    type: 'candlestick',
                    data: chartData.values,
                    itemStyle: {{ color: upColor, color0: downColor, borderColor: upBorderColor, borderColor0: downBorderColor }},
                    markPoint: {{
                        data: [
                            ...predictiveBottoms,
                            ...predictiveTops
                        ]
                    }}
                }},
                {{
                    name: '季線 (MA60)', type: 'line', data: ma60Data,
                    smooth: true, showSymbol: false,
                    lineStyle: {{ width: 1.5, color: '#facc15' }}
                }},
                {{
                    name: '年線 (MA240)', type: 'line', data: ma240Data,
                    smooth: true, showSymbol: false,
                    lineStyle: {{ width: 1.5, color: '#ec4899' }}
                }},
                {{
                    name: '波段支撐 (-12%)', type: 'line', data: dynamicSupports.supportHigh,
                    smooth: true, showSymbol: false,
                    lineStyle: {{ width: 1, color: '#06b6d4', type: 'dashed', opacity: 0.7 }}
                }},
                {{
                    name: '年線支撐 (-12%)', type: 'line', data: dynamicSupports.supportMA,
                    smooth: true, showSymbol: false,
                    lineStyle: {{ width: 1, color: '#d946ef', type: 'dashed', opacity: 0.7 }}
                }},
                {{
                    name: 'VIX', type: 'line', xAxisIndex: 1, yAxisIndex: 1,
                    data: chartData.vixData, smooth: true, showSymbol: false,
                    lineStyle: {{ width: 1.5, color: '#f59e0b' }},
                    areaStyle: {{ color: new echarts.graphic.LinearGradient(0, 0, 0, 1,
                        [{{offset: 0, color: 'rgba(245,158,11,0.5)'}}, {{offset: 1, color: 'rgba(245,158,11,0.05)'}}]) }}
                }},
                {{
                    name: 'RSI(60)', type: 'line', xAxisIndex: 2, yAxisIndex: 2,
                    data: chartData.rsiData, smooth: true, showSymbol: false,
                    lineStyle: {{ width: 1.5, color: '#3b82f6' }}
                }},
                {{
                    name: '恐慌抄底指數', type: 'line', xAxisIndex: 3, yAxisIndex: 3,
                    data: panicScores, smooth: true, showSymbol: false,
                    lineStyle: {{ width: 2, color: '#ef4444' }},
                    areaStyle: {{ color: new echarts.graphic.LinearGradient(0, 0, 0, 1,
                        [{{offset: 0, color: 'rgba(239, 68, 68, 0.5)'}}, {{offset: 1, color: 'rgba(239, 68, 68, 0.05)'}}]) }},
                    markLine: {{
                        symbol: ['none', 'none'],
                        label: {{ show: true, position: 'insideStartTop' }},
                        data: [
                            {{ yAxis: 90, name: '百年黑天鵝', lineStyle: {{ color: '#fbbf24', type: 'dashed' }}, label: {{ color: '#fbbf24', formatter: '百年黑天鵝(>90)' }} }},
                            {{ yAxis: 50, name: '一般股災底', lineStyle: {{ color: '#ef4444', type: 'dashed' }}, label: {{ color: '#ef4444', formatter: '一般股災底(>50)' }} }},
                            {{ yAxis: 25, name: '市場失控警戒', lineStyle: {{ color: '#888', type: 'dotted' }}, label: {{ color: '#888', formatter: '市場失控(>25)' }} }}
                        ]
                    }}
                }},
                {{
                    name: '貪婪逃頂指數', type: 'line', xAxisIndex: 4, yAxisIndex: 4,
                    data: greedScores, smooth: true, showSymbol: false,
                    lineStyle: {{ width: 2, color: '#10b981' }}, // 翡翠綠
                    areaStyle: {{ color: new echarts.graphic.LinearGradient(0, 0, 0, 1,
                        [{{offset: 0, color: 'rgba(16, 185, 129, 0.5)'}}, {{offset: 1, color: 'rgba(16, 185, 129, 0.05)'}}]) }},
                    markLine: {{
                        symbol: ['none', 'none'],
                        label: {{ show: true, position: 'insideStartTop' }},
                        data: [
                            {{ yAxis: 90, name: '極度貪婪 (閃崩前兆)', lineStyle: {{ color: '#ec4899', type: 'dashed' }}, label: {{ color: '#ec4899', formatter: '極度貪婪(>90)' }} }},
                            {{ yAxis: 70, name: '高點警戒', lineStyle: {{ color: '#10b981', type: 'dotted' }}, label: {{ color: '#10b981', formatter: '高點警戒(>70)' }} }}
                        ]
                    }}
                }}
            ]
        }};

        myChart.setOption(option, true);
    }}

    const rawDataFromPython = {market_data_json};
    renderChart(rawDataFromPython);

    window.addEventListener('resize', () => {{ myChart.resize(); }});
</script>
</body>
</html>
"""

with col2:
    components.html(html_template, height=800)
