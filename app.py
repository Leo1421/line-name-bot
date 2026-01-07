import os
import json
import re
import logging
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, FlexSendMessage
from linebot.exceptions import InvalidSignatureError

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- 環境變數 ---
line_bot_api = LineBotApi(os.environ.get('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('CHANNEL_SECRET'))

# --- 資料庫 ---
KANGXI_JSON_PATH = os.path.join(os.path.dirname(__file__), "kangxi_total_strokes_kv.json")
try:
    with open(KANGXI_JSON_PATH, "r", encoding="utf-8") as f:
        STROKE_DICT = json.load(f)
except:
    STROKE_DICT = {}

DOUBLE_SURNAME_LIST = ["張簡", "歐陽", "司馬", "諸葛", "司徒", "上官", "皇甫", "范姜", "長孫", "尉遲", "左丘", "東郭", "南門", "呼延"]

def get_stroke(char): return STROKE_DICT.get(char, 10)

def get_el(n):
    try:
        return {1:'木', 2:'木', 3:'火', 4:'火', 5:'土', 6:'土', 7:'金', 8:'金', 9:'水', 0:'水'}.get(int(str(n)[-1]), '?')
    except: return '?'

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
        # 1. 拆解姓名
        if (len(name_str) >= 3 and name_str[:2] in DOUBLE_SURNAME_LIST) or len(name_str) == 4:
            s_part, n_part = name_str[:2], name_str[2:]
        else:
            s_part, n_part = name_str[:1], name_str[1:]

        s_stk = [get_stroke(c) for c in s_part]
        n_stk = [get_stroke(c) for c in n_part] if n_part else [10]
        
        # 2. 計算五格
        zong = sum(s_stk) + sum(n_stk)
        tian = sum(s_stk) if len(s_part) > 1 else s_stk[0] + 1
        ren = s_stk[-1] + n_stk[0]
        di = sum(n_stk) if len(n_part) > 1 else n_stk[0] + 1
        wai = 2 if len(name_str) == 2 else zong - ren + 1
        
        # 3. 構建名字區塊 (移除 gravity，改用 alignItems 處理對齊)
        name_boxes = []
        for c in name_str:
            name_boxes.append({
                "type": "box", 
                "layout": "horizontal", 
                "alignItems": "center", # 垂直置中
                "contents": [
                    {"type": "text", "text": c, "weight": "bold", "size": "xxl", "flex": 3, "align": "end", "color": "#4a4a4a"},
                    {"type": "text", "text": str(get_stroke(c)), "size": "sm", "flex": 2, "color": "#7a7a7a", "align": "start", "margin": "sm"}
                ]
            })

        # 4. 構建完整 Flex JSON
        flex_contents = {
            "type": "bubble",
            "size": "giga",
            "body": {
                "type": "box",
                "layout": "vertical",
                "paddingAll": "0px",
                "contents": [
                    # 背景圖 (aspectMode: cover 是正確的)
                    {
                        "type": "image",
                        "url": "https://raw.githubusercontent.com/Leo1421/line-name-bot/main/background.jpg?v=110",
                        "size": "full",
                        "aspectMode": "cover",
                        "position": "absolute"
                    },
                    # 內容層
                    {
                        "type": "box",
                        "layout": "vertical",
                        "paddingTop": "45px",
                        "paddingBottom": "80px", # 增加底部空間，防止裁切
                        "paddingStart": "20px",
                        "paddingEnd": "20px",
                        "contents": [
                            # 標題
                            {"type": "text", "text": " — 婉 穎 命 光 所 — ", "weight": "bold", "color": "#6d6d6d", "size": "sm", "align": "center"},
                            
                            # 核心數據區
                            {"type": "box", "layout": "horizontal", "margin": "xxl", "alignItems": "flex-start", "contents": [
                                # 外格
                                {"type": "box", "layout": "vertical", "flex": 1, "contents": [
                                    {"type": "text", "text": "外格", "size": "xs", "color": "#8e8e8e", "align": "center"},
                                    {"type": "text", "text": get_el(wai), "weight": "bold", "size": "xl", "align": "center"}
                                ]},
                                # 名字列表
                                {"type": "box", "layout": "vertical", "flex": 2, "spacing": "sm", "contents": name_boxes},
                                # 三才
                                {"type": "box", "layout": "vertical", "flex": 1, "spacing": "md", "contents": [
                                    {"type": "text", "text": f"天{get_el(tian)}", "weight": "bold", "size": "lg", "align": "center"},
                                    {"type": "text", "text": f"人{get_el(ren)}", "weight": "bold", "size": "lg", "align": "center"},
                                    {"type": "text", "text": f"地{get_el(di)}", "weight": "bold", "size": "lg", "align": "center"}
                                ]},
                                # 年份
                                {"type": "box", "layout": "vertical", "flex": 1, "contents": [
                                    {"type": "text", "text": "出生", "size": "xs", "color": "#8e8e8e", "align": "center"},
                                    {"type": "text", "text": f"{year_str if year_str else '--'}", "size": "xs", "align": "center"},
                                    {"type": "text", "text": get_ny(year_str), "weight": "bold", "size": "lg", "align": "center"}
                                ]}
                            ]},
                            
                            # 底部總格 (使用 margin 推開，不使用 spacer)
                            {"type": "box", "layout": "vertical", "margin": "xxl", "contents": [
                                {"type": "text", "text": "總格", "size": "xs", "color": "#8e8e8e", "align": "center"},
                                {"type": "text", "text": get_el(zong), "weight": "bold", "size": "xl", "align": "center"}
                            ]}
                        ]
                    }
                ]
            }
        }

        # 重要：印出 JSON 以便除錯
        logger.info(f"Flex Payload: {json.dumps(flex_contents, ensure_ascii=False)}")
        
        line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text=f"{name_str}鑑定結果", contents=flex_contents))

    except Exception as e:
        logger.error(f"發生錯誤: {e}")

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
