import yfinance as yf
import pandas as pd
import requests
import os
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
from datetime import datetime
import time

# ==========================================
# 0. 📧 邮件配置 (默认 QQ 邮箱)
# ==========================================
def send_email(content):
    mail_user = os.environ.get("MAIL_USER")
    mail_pass = os.environ.get("MAIL_PASS")
    mail_to = os.environ.get("MAIL_TO")

    if not mail_user or not mail_pass or not mail_to:
        print("❌ 邮箱配置缺失")
        return

    message = MIMEText(content, 'html', 'utf-8')
    message['From'] = formataddr(["美股雷达PRO", mail_user])
    message['To'] = formataddr(["指挥官", mail_to])
    
    subject = f"🦅 美股资金流向与情绪 ({datetime.now().strftime('%m-%d')})"
    message['Subject'] = subject

    try:
        # ✅ 默认使用 QQ 邮箱
        smtp_obj = smtplib.SMTP_SSL('smtp.qq.com', 465) 
        smtp_obj.login(mail_user, mail_pass)
        smtp_obj.sendmail(mail_user, [mail_to], message.as_string())
        print("✅ 战报已发送！")
        smtp_obj.quit()
    except Exception as e:
        print(f"❌ 发送失败: {e}")

# ==========================================
# 1. 核心数据源配置 (已完全汉化)
# ==========================================
# 宏观
MACRO = {
    '^TNX': '10年美债 (利率锚)', 
    'DX-Y.NYB': '美元指数 (DXY)',
    '^VIX': '恐慌指数 (VIX)'
}

# 11大板块 (资金流向核心)
SECTORS_MAP = {
    'XLK': '科技 (Tech)',
    'XLF': '金融 (Finance)',
    'XLV': '医疗 (Health)',
    'XLY': '非必消 (Discret)',
    'XLP': '必消费 (Staples)',
    'XLE': '能源 (Energy)',
    'XLI': '工业 (Indust)',
    'XLB': '材料 (Materials)',
    'XLRE': '地产 (Real Est)',
    'XLC': '通讯 (Comm)',
    'XLU': '公用 (Utilities)'
}

# 七巨头
MAG7 = {
    'NVDA': '英伟达', 'AAPL': '苹果', 'MSFT': '微软', 
    'AMZN': '亚马逊', 'GOOGL': '谷歌', 'META': 'Meta', 'TSLA': '特斯拉'
}

# 关键大宗
COMMODITIES = {'GLD': '黄金', 'USO': '原油', 'BITO': '比特币'}

# ==========================================
# 2. 爬虫工具：恐慌贪婪指数
# ==========================================
def get_fear_greed():
    print("🕷️ 正在抓取市场情绪...")
    url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        score = int(data['fear_and_greed']['score'])
        rating = data['fear_and_greed']['rating']
        
        text = f"{score} - {rating.upper()}"
        if score < 25: text += " (❄️极恐慌)"
        elif score > 75: text += " (🔥极贪婪)"
        return text, score
    except:
        return "数据暂缺", 50

# ==========================================
# 3. 辅助计算
# ==========================================
def get_color(val):
    try:
        if val > 0: return f"<span style='color:red; font-weight:bold'>+{val:.2f}%</span>"
        if val < 0: return f"<span style='color:green; font-weight:bold'>{val:.2f}%</span>"
        return f"{val:.2f}%"
    except: return "0.00%"

def analyze_trend(current, high_52, low_52):
    if high_52 == low_52: return 50
    return (current - low_52) / (high_52 - low_52) * 100

# ==========================================
# 4. 主扫描逻辑
# ==========================================
def scan_market_pro():
    print(f"📡 启动美股全景扫描...")
    
    # 1. 准备列表
    all_tickers = list(MACRO.keys()) + list(SECTORS_MAP.keys()) + list(MAG7.keys()) + list(COMMODITIES.keys())
    
    # 2. 下载数据 (关闭多线程防止锁库)
    try:
        data = yf.download(all_tickers, period="1y", interval="1d", group_by='ticker', threads=False, progress=False)
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        return

    # 3. 数据分类容器
    macro_data = []
    sector_data = []
    mag7_data = []
    comm_data = []
    
    # 4. 遍历处理
    for ticker in all_tickers:
        try:
            # 兼容性处理
            if ticker in data.columns.get_level_values(0):
                df = data[ticker].dropna()
            else:
                continue 
            
            if len(df) < 2: continue
            
            price = df['Close'].iloc[-1]
            prev = df['Close'].iloc[-2]
            change = (price - prev) / prev * 100
            
            # 52周位置
            pos_52 = analyze_trend(price, df['High'].max(), df['Low'].max())
            
            item = {'Ticker': ticker, 'Price': price, 'Change': change, 'Pos52': pos_52}
            
            if ticker in MACRO:
                item['Name'] = MACRO[ticker]
                macro_data.append(item)
            elif ticker in SECTORS_MAP:
                item['Name'] = SECTORS_MAP[ticker] # 使用中文名
                sector_data.append(item)
            elif ticker in MAG7:
                item['Name'] = MAG7[ticker]
                mag7_data.append(item)
            elif ticker in COMMODITIES:
                item['Name'] = COMMODITIES[ticker]
                comm_data.append(item)
                
        except Exception as e:
            continue

    # ==========================================
    # 5. 生成战报
    # ==========================================
    sentiment_text, sentiment_score = get_fear_greed()
    
    msg = []
    msg.append(f"<h2>🦅 美股全景 ({datetime.now().strftime('%H:%M')} UTC)</h2>")
    
    # --- A. 情绪 ---
    bg = "#ffebee" if sentiment_score > 75 else ("#e8f5e9" if sentiment_score < 25 else "#fff3e0")
    msg.append(f"<div style='background-color:{bg}; padding:10px;'><h3>🧠 市场心理: {sentiment_text}</h3></div>")
    
    # --- B. 宏观 ---
    msg.append("<h3>⚖️ 宏观重力</h3><ul>")
    for item in macro_data:
        msg.append(f"<li><b>{item['Name']}:</b> {item['Price']:.2f} ({get_color(item['Change'])})</li>")
    msg.append("</ul>")

    # --- C. 资金流向 (必不可少的部分) ---
    if sector_data:
        # 按涨跌幅排序
        sector_data.sort(key=lambda x: x['Change'], reverse=True)
        
        msg.append("<h3>💸 行业板块轮动 (Sector Rotation)</h3>")
        msg.append("<table border='1' cellspacing='0' cellpadding='4' style='border-collapse:collapse; width:100%'>")
        msg.append("<tr style='background-color:#f2f2f2'><th>排名</th><th>板块</th><th>涨跌幅</th><th>强度</th></tr>")
        
        for i, item in enumerate(sector_data):
            # 强度条 (可视化)
            width = min(abs(item['Change']) * 10, 50) 
            bar_color = "red" if item['Change'] > 0 else "green"
            bar = f"<div style='width:{width}px; height:10px; background-color:{bar_color};'></div>"
            
            msg.append(f"<tr><td>{i+1}</td><td>{item['Name']}</td><td>{get_color(item['Change'])}</td><td>{bar}</td></tr>")
        msg.append("</table>")
    else:
        msg.append("<h3>💸 行业板块</h3><p>⚠️ 数据下载超时，本次缺失。</p>")

    # --- D. 广度 (七巨头) ---
    msg.append("<h3>🏎️ 七巨头 (Mag 7)</h3>")
    msg.append("<table border='0' width='100%'>")
    for item in mag7_data:
        pos_desc = "🔥新高" if item['Pos52'] > 95 else ("❄️新低" if item['Pos52'] < 5 else "震荡")
        msg.append(f"<tr><td><b>{item['Name']}</b></td><td>{get_color(item['Change'])}</td><td><small>{pos_desc}</small></td></tr>")
    msg.append("</table>")

    send_email("".join(msg))

if __name__ == "__main__":
    scan_market_pro()
