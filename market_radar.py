import yfinance as yf
import pandas as pd
import os
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
from datetime import datetime

# ==========================================
# 0. 📧 邮件配置 (自动读取你之前设好的密码)
# ==========================================
def send_email(content):
    mail_user = os.environ.get("MAIL_USER")
    mail_pass = os.environ.get("MAIL_PASS")
    mail_to = os.environ.get("MAIL_TO")

    if not mail_user or not mail_pass or not mail_to:
        print("❌ 邮箱配置缺失，请检查 GitHub Secrets")
        return

    message = MIMEText(content, 'html', 'utf-8')
    message['From'] = formataddr(["市场指挥官", mail_user])
    message['To'] = formataddr(["交易员", mail_to])
    
    # 标题带上日期
    subject = f"🌍 美股全景战报: 资金流向与宏观重力 ({datetime.now().strftime('%m-%d')})"
    message['Subject'] = subject

    try:
        smtp_obj = smtplib.SMTP_SSL('smtp.163.com', 465) 
        smtp_obj.login(mail_user, mail_pass)
        smtp_obj.sendmail(mail_user, [mail_to], message.as_string())
        print("✅ 邮件发送成功！")
        smtp_obj.quit()
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")

# ==========================================
# 1. 核心监控列表 (加入美债和美元)
# ==========================================
WATCHLIST = {
    # --- 大盘指数 ---
    'SPY': '标普500 (大盘)',
    'QQQ': '纳指100 (科技)',
    'IWM': '罗素2000 (小盘)',
    '^VIX': '恐慌指数 (VIX)',
    
    # --- 宏观重力 (最重要) ---
    '^TNX': '10年美债收益率',  # 利率锚
    'DX-Y.NYB': '美元指数 (DXY)', # 资金流向反指
    
    # --- 11大板块 (资金轮动) ---
    'XLK': '科技 (Technology)',
    'XLF': '金融 (Financial)',
    'XLV': '医疗 (Health)',
    'XLY': '可选消费 (Discretionary)',
    'XLP': '必需消费 (Staples)',
    'XLE': '能源 (Energy)',
    'XLI': '工业 (Industrial)',
    'XLB': '材料 (Materials)',
    'XLRE': '地产 (Real Estate)',
    'XLC': '通讯 (Comm)',
    'XLU': '公用事业 (Utilities)',
    
    # --- 关键资产 ---
    'GLD': '黄金',
    'USO': '原油',
    'BITO': '比特币期货'
}

def get_color(change):
    """涨红跌绿"""
    if change > 0: return "color:red; font-weight:bold;"
    if change < 0: return "color:green; font-weight:bold;"
    return "color:black;"

def scan_market():
    print(f"📡 正在扫描全球市场数据...")
    
    tickers = list(WATCHLIST.keys())
    
    try:
        # 下载最近2天数据来计算涨跌幅
        data = yf.download(tickers, period="5d", interval="1d", group_by='ticker', threads=True, progress=False)
        
        market_data = []
        
        for ticker in tickers:
            try:
                # 兼容数据格式
                if ticker in data.columns.get_level_values(0):
                    df = data[ticker]
                else:
                    df = data
                
                df = df.dropna()
                if len(df) < 2: continue
                
                price = df['Close'].iloc[-1]
                prev_price = df['Close'].iloc[-2]
                change = (price - prev_price) / prev_price * 100
                
                name = WATCHLIST[ticker]
                
                # 简单分类
                category = "MACRO" 
                if ticker in ['^TNX', 'DX-Y.NYB', '^VIX']: category = "GRAVITY" # 重力
                elif ticker.startswith('XL'): category = "SECTOR" # 板块
                elif ticker in ['SPY', 'QQQ', 'IWM']: category = "INDEX" # 指数
                else: category = "ASSET" # 其他资产
                
                market_data.append({
                    "Ticker": ticker, "Name": name, "Price": price, "Change": change, "Cat": category
                })
            except:
                continue
        
        # === 生成邮件 HTML ===
        lines = []
        lines.append(f"<h2>📊 市场全景 ({datetime.now().strftime('%H:%M')} UTC)</h2>")
        
        # 1. 宏观重力 (Gravity)
        lines.append("<h3>⚖️ 宏观重力 (决定估值天花板)</h3>")
        gravity = [x for x in market_data if x['Cat'] == 'GRAVITY']
        lines.append("<ul>")
        for item in gravity:
            c = get_color(item['Change'])
            lines.append(f"<li><b>{item['Name']}:</b> {item['Price']:.2f} (<span style='{c}'>{item['Change']:.2f}%</span>)</li>")
        lines.append("</ul>")
        lines.append("<p><i>提示：美债(TNX)和美元(DXY)大涨通常利空股市。VIX飙升代表恐慌。</i></p>")

        # 2. 大盘指数
        lines.append("<h3>📈 主要指数</h3>")
        indices = [x for x in market_data if x['Cat'] == 'INDEX']
        lines.append("<table border='1' cellpadding='5' cellspacing='0' style='border-collapse:collapse; width:100%'>")
        lines.append("<tr style='background-color:#f2f2f2'><th>指数</th><th>现价</th><th>涨跌</th></tr>")
        for item in indices:
            c = get_color(item['Change'])
            lines.append(f"<tr><td>{item['Name']}</td><td>{item['Price']:.2f}</td><td style='{c}'>{item['Change']:.2f}%</td></tr>")
        lines.append("</table>")

        # 3. 资金流向 (板块排行)
        sectors = [x for x in market_data if x['Cat'] == 'SECTOR']
        sectors.sort(key=lambda x: x['Change'], reverse=True) # 涨幅排序
        
        lines.append("<h3>💸 板块资金流向 (Sector Rotation)</h3>")
        lines.append(f"<p>🔥 <b>今日领涨:</b> {sectors[0]['Name']} (<span style='color:red'>{sectors[0]['Change']:.2f}%</span>)</p>")
        lines.append(f"<p>🧊 <b>今日领跌:</b> {sectors[-1]['Name']} (<span style='color:green'>{sectors[-1]['Change']:.2f}%</span>)</p>")
        
        lines.append("<table border='1' cellpadding='5' cellspacing='0' style='border-collapse:collapse; width:100%'>")
        lines.append("<tr style='background-color:#e3f2fd'><th>排名</th><th>板块</th><th>涨跌幅</th></tr>")
        for i, item in enumerate(sectors):
            c = get_color(item['Change'])
            lines.append(f"<tr><td>{i+1}</td><td>{item['Name']} ({item['Ticker']})</td><td style='{c}'>{item['Change']:.2f}%</td></tr>")
        lines.append("</table>")
        
        # 发送
        send_email("".join(lines))

    except Exception as e:
        print(f"❌ 运行出错: {e}")

if __name__ == "__main__":
    scan_market()
