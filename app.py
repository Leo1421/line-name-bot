import os
import json
import re
import logging
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, FlexSendMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- 環境變數 ---
line_bot_api = LineBotApi(os.environ.get('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('CHANNEL_SECRET'))

# --- 讀取筆畫資料 ---
KANGXI_JSON_PATH = os.path.join(os.path.dirname(__file__), "kangxi_total_strokes_kv.json")
try:
    with open(KANGXI_JSON_PATH, "r", encoding="utf-8") as f:
        STROKE_DICT = json.load(f)
except:
    STROKE_DICT = {}

# 複姓列表
DOUBLE_SURNAME_LIST = ["張簡", "歐陽", "司馬", "諸葛", "司徒", "上官", "皇甫", "范姜", "長孫", "尉遲", "左丘", "東郭", "南門", "呼延"]

def get_stroke(char): 
    return STROKE_DICT.get(char, 10)

def get_el(n):
    try:
        last_digit = int(str(n)[-1])
        return {1:'木', 2:'木', 3:'火', 4:'火', 5:'土', 6:'土', 7:'金', 8:'金', 9:'水', 0:'水'}.get(last_digit, '?')
    except:
        return '?'

def get_ny(y):
    nayins = ["海中金","爐中火","大林木","路旁土","劍鋒金","山頭火","澗下水","城頭土","白蠟金","楊柳木",
              "泉中水","屋上土","霹靂火","松柏木","長流水","沙中金","山下火","平地木","壁上土","金箔金",
              "覆燈火","天河水","大驛土","釵釧金","桑柘木","大溪水","沙中土","天上火","石榴木","大海水"]
    try: 
        val = int(y)
        if val < 1924: return "--"
        return nayins[((val - 1924) % 60) // 2][-1]
    except: return "--"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text.strip()
    logger.info(f"收到訊息: {msg}")
    
    match = re.match(r"([^\d\+\s\-]+)[\+\s\-]*(\d*)", msg)
    if not match: return

    name_str = match.group(1)
    year_str = match.group(2)

    try:
        # 1. 姓名拆解
        if (len(name_str) >= 3 and name_str[:2] in DOUBLE_SURNAME_LIST) or len(name_str) == 4:
            s_part, n_part = name_str[:2], name_str[2:]
        else:
            s_part, n_part = name_str[:1], name_str[1:]

        # 2. 取得筆畫
        s_stk = [get_stroke(c) for c in s_part]
        # 防呆：如果沒有名字部分（只有姓），預設給10畫避免報錯
        n_stk = [get_stroke(c) for c in n_part] if n_part else [10]
        
        # 3. 五格計算
        # 先算總格，確保變數已定義
        zong = sum(s_stk) + sum(n_stk)
        
        # 天格
        if len(s_part) > 1:
            tian = sum(s_stk)
        else:
            tian = s_stk[0] + 1
            
        # 人格
        ren = s_stk[-1] + n_stk[0]
        
        # 地格 (修正：單名+1，複名則是總和)
        if len(n_part) == 1:
            di = n_stk[0] + 1
        else:
            di = sum(n_stk)
        
        # 外格 (總格 - 人格 + 1)
        # 特例：單姓單名 (總長2字) 外格固定為 2
        if len(name_str) == 2:
            wai = 2
        else:
            wai = zong - ren + 1
        
        # 4. 構建 Flex Message
        # 準備名字區塊
        name_boxes = []
        for c in name_str:
            name_boxes.append({
                "type": "box", "layout": "horizontal", "contents": [
                    {"type": "text", "text": c, "weight": "bold", "size": "3xl", "flex": 3, "align": "end", "color": "#4a4a4a"},
                    {"type": "text", "text": f"{get_stroke(c)}", "size": "sm", "flex": 2, "color": "#7a7a7a", "gravity": "center"}
                ]
            })

        flex_msg = {
            "type": "bubble", 
            "size": "giga",
            "body": {
                "type": "box", 
                "layout": "vertical", 
                "paddingAll": "0px",
                "contents": [
                    # 背景圖：修正為 cover (fill是不合法的)
                    {
                        "type": "image", 
                        "url": "https://raw.githubusercontent.com/Leo1421/line-name-bot/main/background.jpg?v=108", 
                        "size": "full", 
                        "aspectMode": "cover", 
                        "position": "absolute"
                    },
                    # 內容容器
                    {
                        "type": "box", 
                        "layout": "vertical", 
                        # 使用 Padding 撐開高度，解決三字名背景裁切問題
                        "paddingTop": "45px", 
                        "paddingBottom": "80px", 
                        "paddingStart": "20px", 
                        "paddingEnd": "20px",
                        "contents": [
                            # 標題
                            {"type": "text", "text": " — 婉 穎 命 光 所 — ", "weight": "bold", "color": "#6d6d6d", "size": "sm", "align": "center"},
                            
                            # 主要數值區
                            {"type": "box", "layout": "horizontal", "margin": "xxl", "contents": [
                                # 外格
                                {"type": "box", "layout": "vertical", "flex": 1, "justifyContent": "center", "contents": [
                                    {"type": "text", "text": "外格", "size": "xs", "color": "#8e8e8e", "align": "center"},
                                    {"type": "text", "text": get_el(wai), "weight": "bold", "size": "xl", "align": "center"}
                                ]},
                                # 名字
                                {"type": "box", "layout": "vertical", "flex": 2, "spacing": "sm", "contents": name_boxes},
                                # 三才
                                {"type": "box", "layout": "vertical", "flex": 1, "spacing": "md", "contents": [
                                    {"type": "text", "text": f"天{get_el(tian)}", "weight": "bold", "size": "lg", "align": "center"},
                                    {"type": "text", "text": f"人{get_el(ren)}", "weight": "bold", "size": "lg", "align": "center"},
                                    {"type": "text", "text": f"地{get_el(di)}", "weight": "bold", "size": "lg", "align": "center"}
                                ]},
                                # 年份
                                {"type": "box", "layout": "vertical", "flex": 1, "justifyContent": "center", "contents": [
                                    {"type": "text", "text": "出生", "size": "xs", "color": "#8e8e8e", "align": "center"},
                                    {"type": "text", "text": f"{year_str if year_str else '--'}", "size": "xs", "align": "center"},
                                    {"type": "text", "text": get_ny(year_str), "weight": "bold", "size": "lg", "align": "center"}
                                ]}
                            ]},
                            
                            # 間距 spacer (比 separator 穩定)
                            {"type": "spacer", "size": "xxl"},
                            
                            # 總格
                            {"type": "box", "layout": "vertical", "contents": [
                                {"type": "text", "text": "總格", "size": "xs", "color": "#8e8e8e", "align": "center"},
                                {"type": "text", "text": get_el(zong), "weight": "bold", "size": "xl", "align": "center"}
                            ]}
                        ]
                    }
                ]
            }
        }
        line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text=f"{name_str}鑑定結果", contents=flex_msg))
    except Exception as e:
        logger.error(f"Flex構建失敗: {e}")

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

if __name__ == "__main__":
    app.run()
