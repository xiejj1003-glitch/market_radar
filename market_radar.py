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
# 0. 📧 邮件配置
# ==========================================
def send_email(content):
    mail_user = os.environ.get("MAIL_USER")
    mail_pass = os.environ.get("MAIL_PASS")
    mail_to = os.environ.get("MAIL_TO")

    if not mail_user or not mail_pass or not mail_to:
        print("❌ 邮箱配置缺失")
        return

    message = MIMEText(content, 'html', 'utf-8')
    message['From'] = formataddr(["市场雷达PRO", mail_user])
    message['To'] = formataddr(["指挥官", mail_to])
    
    subject = f"🦅 市场深层扫描: 情绪+广度+内参 ({datetime.now().strftime('%m-%d')})"
    message['Subject'] = subject

    try:
        # 👇 修复点：换行，并使用 QQ 服务器
        smtp_obj = smtplib.SMTP_SSL('smtp.qq.com', 465) 
        smtp_obj.login(mail_user, mail_pass)
        smtp_obj.sendmail(mail_user, [mail_to], message.as_string())
        print("✅ 美股战报已发送！")
        smtp_obj.quit()
    except Exception as e:
        print(f"❌ 发送失败: {e}")

# ==========================================
# 1. 核心数据源配置
# ==========================================
# 宏观与重力
MACRO = {
    '^TNX': '10年美债 (全球资产之锚)', 
    'DX-Y.NYB': '美元指数 (流动性阀门)',
    '^VIX': '恐慌指数 (期权避险成本)'
}

# 11大板块 (计算市场广度)
SECTORS = [
    'XLK', 'XLF', 'XLV', 'XLY', 'XLP', 'XLE', 
    'XLI', 'XLB', 'XLRE', 'XLC', 'XLU'
]

# 七巨头 (Mag 7 - 市场真实的发动机)
MAG7 = {
    'NVDA': '英伟达', 'AAPL': '苹果', 'MSFT': '微软', 
    'AMZN': '亚马逊', 'GOOGL': '谷歌', 'META': 'Meta', 'TSLA': '特斯拉'
}

# 关键大宗
COMMODITIES = {'GLD': '黄金', 'USO': '原油', 'BITO': '比特币'}

# ==========================================
# 2. 爬虫工具：获取 CNN 恐慌贪婪指数
#    (这是 Smart Money 最好的综合指标，包含 PCR 数据)
# ==========================================
def get_fear_greed():
    print("🕷️ 正在抓取市场情绪 (Fear & Greed)...")
    url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        score = int(data['fear_and_greed']['score'])
        rating = data['fear_and_greed']['rating']
        
        # 简单解读
        sentiment_text = f"{score} - {rating.upper()}"
        if score < 25: sentiment_text += " (❄️ 极度恐慌 - 可能见底)"
        elif score > 75: sentiment_text += " (🔥 极度贪婪 - 风险剧增)"
        
        return sentiment_text, score
    except Exception as e:
        print(f"情绪抓取失败: {e}")
        return "数据暂时不可用", 50

# ==========================================
# 3. 辅助函数：颜色与计算
# ==========================================
def get_color(val, is_percent=True):
    suffix = "%" if is_percent else ""
    if val > 0: return f"<span style='color:red; font-weight:bold'>+{val:.2f}{suffix}</span>"
    if val < 0: return f"<span style='color:green; font-weight:bold'>{val:.2f}{suffix}</span>"
    return f"{val:.2f}{suffix}"

def analyze_trend(current, high_52w, low_52w):
    """计算价格在 52周范围内的位置 (0% = 新低, 100% = 新高)"""
    if high_52w == low_52w: return 50
    pos = (current - low_52w) / (high_52w - low_52w) * 100
    return pos

# ==========================================
# 4. 主扫描逻辑
# ==========================================
def scan_market_pro():
    print(f"📡 启动深层扫描 PRO版...")
    
    # 1. 获取情绪
    sentiment_text, sentiment_score = get_fear_greed()
    
    # 2. 准备所有 Ticker
    all_tickers = list(MACRO.keys()) + SECTORS + list(MAG7.keys()) + list(COMMODITIES.keys())
    
    # 3. 下载数据 (包含 52周 High/Low 用于判断新高)
    #    Threads=False 防止数据库锁死
    try:
        data = yf.download(all_tickers, period="1y", interval="1d", group_by='ticker', threads=False, progress=False)
    except Exception as e:
        print(f"❌ 数据下载严重错误: {e}")
        return

    # 4. 数据处理容器
    macro_data = []
    sector_data = []
    mag7_data = []
    comm_data = []
    
    for ticker in all_tickers:
        try:
            # 兼容性处理
            if ticker in data.columns.get_level_values(0):
                df = data[ticker]
            else:
                continue # 数据缺失跳过
            
            df = df.dropna()
            if len(df) < 5: continue
            
            price = df['Close'].iloc[-1]
            prev_price = df['Close'].iloc[-2]
            change = (price - prev_price) / prev_price * 100
            
            # 52周数据 (Catalyst: 动力衰竭检测)
            high_52 = df['High'].max()
            low_52 = df['Low'].min()
            pos_52 = analyze_trend(price, high_52, low_52)
            
            item = {
                'Ticker': ticker,
                'Price': price,
                'Change': change,
                'Pos52': pos_52
            }
            
            if ticker in MACRO: 
                item['Name'] = MACRO[ticker]
                macro_data.append(item)
            elif ticker in SECTORS:
                item['Name'] = ticker
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
    # 5. 生成深度战报 HTML
    # ==========================================
    msg = []
    msg.append(f"<h2>🦅 市场深层扫描 ({datetime.now().strftime('%H:%M')} UTC)</h2>")
    
    # --- 模块 A: 市场情绪 (Smart Money 替代) ---
    bg_color = "#e8f5e9" if sentiment_score < 40 else ("#ffebee" if sentiment_score > 60 else "#fff3e0")
    msg.append(f"<div style='background-color:{bg_color}; padding:10px; border-radius:5px;'>")
    msg.append(f"<h3>🧠 市场心理 (Smart Money): <b>{sentiment_text}</b></h3>")
    msg.append("<p style='font-size:12px; color:#666;'>*此指标综合了 PCR (期权博弈)、VIX、动量和垃圾债需求。</p>")
    msg.append("</div>")
    
    # --- 模块 B: 宏观重力 (Gravity) ---
    msg.append("<h3>⚖️ 宏观重力 (估值天花板)</h3>")
    msg.append("<ul>")
    tnx = next((x for x in macro_data if x['Ticker'] == '^TNX'), None)
    dxy = next((x for x in macro_data if x['Ticker'] == 'DX-Y.NYB'), None)
    
    if tnx: msg.append(f"<li><b>10年美债:</b> {tnx['Price']:.2f}% ({get_color(tnx['Change'])}) - <i>若暴涨则杀科技股估值</i></li>")
    if dxy: msg.append(f"<li><b>美元指数:</b> {dxy['Price']:.2f} ({get_color(dxy['Change'])}) - <i>若涨则利空大宗和美股</i></li>")
    msg.append("</ul>")

    # --- 模块 C: 市场内部广度 (Market Internals) ---
    # 计算板块涨跌比
    up_sectors = sum(1 for s in sector_data if s['Change'] > 0)
    breadth_ratio = f"{up_sectors}/{len(sector_data)}"
    
    msg.append(f"<h3>🩻 市场内部健康度 (广度测谎)</h3>")
    msg.append(f"<p><b>板块红绿比:</b> {breadth_ratio} (11大板块)</p>")
    
    # 七巨头监控
    msg.append("<table border='1' cellpadding='4' cellspacing='0' style='width:100%; border-collapse:collapse;'>")
    msg.append("<tr style='background-color:#f2f2f2'><th>七巨头 (Mag7)</th><th>涨跌</th><th>位置(52周)</th></tr>")
    
    for item in mag7_data:
        # 位置描述：接近新高是强势，接近新低是弱势
        pos_desc = f"{item['Pos52']:.0f}%"
        pos_style = "color:red" if item['Pos52'] > 90 else ("color:green" if item['Pos52'] < 10 else "color:black")
        
        msg.append(f"<tr><td>{item['Name']}</td><td>{get_color(item['Change'])}</td><td style='{pos_style}'>{pos_desc}</td></tr>")
    msg.append("</table>")
    msg.append("<p style='font-size:12px'>*位置(52周): 100%代表创新高(动力强)，0%代表创新低(动力衰竭)。</p>")

    # --- 模块 D: 资金流向 (Sector Rotation) ---
    sector_data.sort(key=lambda x: x['Change'], reverse=True)
    top_sec = sector_data[0]
    bot_sec = sector_data[-1]
    
    msg.append(f"<h3>💸 资金流向 (板块轮动)</h3>")
    msg.append(f"<ul><li><b>资金进攻:</b> {top_sec['Name']} ({get_color(top_sec['Change'])})</li>")
    msg.append(f"<li><b>资金撤退:</b> {bot_sec['Name']} ({get_color(bot_sec['Change'])})</li></ul>")

    # --- 模块 E: 关键资产 ---
    msg.append("<h3>💰 关键资产</h3>")
    msg.append("<table border='0' cellpadding='5'><tr>")
    for item in comm_data:
        msg.append(f"<td><b>{item['Name']}:</b> {get_color(item['Change'])}</td>")
    msg.append("</tr></table>")

    send_email("".join(msg))

if __name__ == "__main__":
    scan_market_pro()
