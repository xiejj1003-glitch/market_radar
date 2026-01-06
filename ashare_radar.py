import akshare as ak
import pandas as pd
import os
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
from datetime import datetime
import time

# ==========================================
# 0. 📧 邮件配置 (复用之前的配置)
# ==========================================
def send_email(content):
    mail_user = os.environ.get("MAIL_USER")
    mail_pass = os.environ.get("MAIL_PASS")
    mail_to = os.environ.get("MAIL_TO")

    if not mail_user or not mail_pass or not mail_to:
        print("❌ 邮箱配置缺失")
        return

    message = MIMEText(content, 'html', 'utf-8')
    message['From'] = formataddr(["A股指挥官", mail_user])
    message['To'] = formataddr(["指挥官", mail_to])
    
    subject = f"🇨🇳 A股收盘复盘: 资金流向与情绪 ({datetime.now().strftime('%m-%d')})"
    message['Subject'] = subject

    try:
        # 这里默认用 163，如果你是 QQ 请改回 smtp.qq.com
        smtp_obj = smtplib.SMTP_SSL('smtp.qq.com''smtp.qqq.com', 465) obj.login(mail_user, mail_pass)
        smtp_obj.sendmail(mail_user, [mail_to], message.as_string())
        print("✅ A股战报已发送！")
        smtp_obj.quit()
    except Exception as e:
        print(f"❌ 发送失败: {e}")

# ==========================================
# 1. 辅助功能
# ==========================================
def get_color(val):
    if val > 0: return f"<span style='color:red; font-weight:bold'>+{val:.2f}%</span>"
    if val < 0: return f"<span style='color:green; font-weight:bold'>{val:.2f}%</span>"
    return f"{val:.2f}%"

# ==========================================
# 2. 核心扫描逻辑
# ==========================================
def scan_ashare():
    print("🚀 启动 A股雷达 (AkShare)...")
    try:
        msg = []
        msg.append(f"<h2>🇨🇳 A股市场全景 ({datetime.now().strftime('%Y-%m-%d')})</h2>")

        # --- 模块 A: 大盘指数 (上证/深证/创业) ---
        print("1. 获取指数数据...")
        # akshare 接口: 实时指数行情
        index_df = ak.stock_zh_index_spot()
        # 筛选核心指数: 上证指数, 深证成指, 创业板指, 科创50
        target_indices = {
            'sh000001': '上证指数', 
            'sz399001': '深证成指', 
            'sz399006': '创业板指',
            'sh000688': '科创50'
        }
        
        msg.append("<h3>📊 核心指数</h3>")
        msg.append("<table border='1' cellpadding='4' cellspacing='0' style='width:100%; border-collapse:collapse;'>")
        msg.append("<tr style='background-color:#f2f2f2'><th>指数</th><th>点位</th><th>涨跌幅</th><th>成交额(亿)</th></tr>")
        
        for code, name in target_indices.items():
            try:
                row = index_df[index_df['代码'] == code].iloc[0]
                price = row['最新价']
                change = row['涨跌幅']
                amount = row['成交额'] / 100000000 # 转为亿
                
                msg.append(f"<tr><td>{name}</td><td>{price:.2f}</td><td>{get_color(change)}</td><td>{amount:.0f}</td></tr>")
            except:
                continue
        msg.append("</table>")

        # --- 模块 B: 市场情绪 (涨跌家数 + 涨停统计) ---
        print("2. 计算市场情绪...")
        # 获取全市场实时行情 (速度较慢，耐心等待)
        spot_df = ak.stock_zh_a_spot_em()
        
        up_count = len(spot_df[spot_df['涨跌幅'] > 0])
        down_count = len(spot_df[spot_df['涨跌幅'] < 0])
        flat_count = len(spot_df[spot_df['涨跌幅'] == 0])
        
        # 简单计算涨停/跌停 (近似值: >9.8%算涨停)
        limit_up = len(spot_df[spot_df['涨跌幅'] > 9.8])
        limit_down = len(spot_df[spot_df['涨跌幅'] < -9.8])
        
        # 情绪打分
        sentiment = "😐 震荡"
        if up_count > 3500: sentiment = "🔥 普涨 (情绪高涨)"
        elif down_count > 3500: sentiment = "❄️ 普跌 (冰点时刻)"
        elif limit_up > 80: sentiment = "🐂 局部牛市 (妖股横行)"
        
        msg.append(f"<h3>🌡️ 市场情绪: {sentiment}</h3>")
        msg.append(f"<ul>")
        msg.append(f"<li><b>涨跌分布:</b> 🔴涨: {up_count} | 🟢跌: {down_count} | ⚪平: {flat_count}</li>")
        msg.append(f"<li><b>极端个股:</b> 🔥涨停: <b>{limit_up}</b> 家 | ☠️跌停: <b>{limit_down}</b> 家</li>")
        msg.append(f"<li><b>总成交量:</b> {(spot_df['成交额'].sum() / 100000000):.0f} 亿</li>")
        msg.append(f"</ul>")

        # --- 模块 C: 北向资金 (Smart Money) ---
        # 注意：北向实时数据接口经常变动，如果获取失败则跳过
        try:
            print("3. 获取北向资金...")
            north_df = ak.stock_hsgt_north_net_flow_in_em(symbol="北上")
            # 获取最新的一行数据
            latest_north = north_df.iloc[-1]
            north_val = latest_north['value'] / 10000 # 转为亿
            
            north_color = "red" if north_val > 0 else "green"
            north_dir = "流入" if north_val > 0 else "流出"
            
            msg.append(f"<h3>💰 北向资金 (聪明钱)</h3>")
            msg.append(f"<p>今日净{north_dir}: <span style='color:{north_color}; font-weight:bold'>{north_val:.2f} 亿</span></p>")
        except:
            msg.append("<h3>💰 北向资金</h3><p>数据接口维护中...</p>")

        # --- 模块 D: 行业板块排行 ---
        print("4. 获取行业板块...")
        bk_df = ak.stock_board_industry_name_em()
        # 按涨跌幅排序
        bk_df = bk_df.sort_values(by='涨跌幅', ascending=False)
        
        top_bk = bk_df.head(5)
        bot_bk = bk_df.tail(5)
        
        msg.append("<h3>💸 行业板块轮动</h3>")
        msg.append("<table border='0' style='width:100%'><tr><td valign='top' width='50%'>")
        msg.append("<b>🚀 领涨板块:</b><br>")
        for _, row in top_bk.iterrows():
            msg.append(f"{row['板块名称']} ({get_color(row['涨跌幅'])})<br>")
        msg.append("</td><td valign='top'>")
        msg.append("<b>🌊 领跌板块:</b><br>")
        # 领跌要反过来遍历
        for i in range(len(bot_bk)-1, -1, -1):
            row = bot_bk.iloc[i]
            msg.append(f"{row['板块名称']} ({get_color(row['涨跌幅'])})<br>")
        msg.append("</td></tr></table>")

        # 发送
        send_email("".join(msg))

    except Exception as e:
        print(f"❌ 运行报错: {e}")

if __name__ == "__main__":
    scan_ashare()
