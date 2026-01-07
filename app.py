import os
import json
import re
import logging
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, FlexSendMessage
from linebot.exceptions import InvalidSignatureError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ.get('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('CHANNEL_SECRET'))

# --- 資料載入 ---
KANGXI_JSON_PATH = os.path.join(os.path.dirname(__file__), "kangxi_total_strokes_kv.json")
try:
    with open(KANGXI_JSON_PATH, "r", encoding="utf-8") as f:
        STROKE_DICT = json.load(f)
except:
    STROKE_DICT = {}

DOUBLE_SURNAME_LIST = ["張簡", "歐陽", "司馬", "諸葛", "司徒", "上官", "皇甫", "范姜", "長孫", "尉遲", "左丘", "東郭", "南門", "呼延"]

def get_stroke(char): return STROKE_DICT.get(char, 10)
def get_el(n):
    try: return {1:'木', 2:'木', 3:'火', 4:'火', 5:'土', 6:'土', 7:'金', 8:'金', 9:'水', 0:'水'}.get(int(str(n)[-1]), '?')
    except: return '?'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text.strip()
    match = re.match(r"([^\d\+\s\-]+)[\+\s\-]*(\d*)", msg)
    if not match: return

    name_str = match.group(1)
    year_str = match.group(2)

    try:
        # 1. 姓名算法
        if (len(name_str) >= 3 and name_str[:2] in DOUBLE_SURNAME_LIST) or len(name_str) == 4:
            s_part, n_part = name_str[:2], name_str[2:]
        else:
            s_part, n_part = name_str[:1], name_str[1:]

        s_stk = [get_stroke(c) for c in s_part]
        n_stk = [get_stroke(c) for c in n_part] if n_part else [10]
        
        zong = sum(s_stk) + sum(n_stk)
        tian = sum(s_stk) if len(s_part) > 1 else s_stk[0] + 1
        ren = s_stk[-1] + n_stk[0]
        di = sum(n_stk) if len(n_part) > 1 else n_stk[0] + 1
        wai = 2 if len(name_str) == 2 else zong - ren + 1
        
        # 2. 構建名字與筆畫 (垂直並排)
        name_contents = []
        for c in name_str:
            name_contents.append({
                "type": "box", "layout": "horizontal", "contents": [
                    {"type": "text", "text": c, "size": "3xl", "weight": "bold", "color": "#444444", "flex": 0},
                    {"type": "text", "text": str(get_stroke(c)), "size": "sm", "color": "#999999", "margin": "sm", "gravity": "top"}
                ],
                "justifyContent": "center", "margin": "sm"
            })

        # 3. 完整 Flex 設計 (完全對照圖片)
        flex_contents = {
            "type": "bubble",
            "size": "mega",
            "body": {
                "type": "box", "layout": "vertical", "paddingAll": "0px", "height": "380px",
                "contents": [
                    # 背景圖
                    {"type": "image", "url": "https://raw.githubusercontent.com/Leo1421/line-name-bot/main/background.jpg?v=120", "size": "full", "aspectMode": "cover", "position": "absolute"},
                    
                    # 頂部標題
                    {"type": "text", "text": "— 婉 穎 命 光 所 —", "size": "sm", "color": "#666666", "align": "center", "position": "absolute", "offsetTop": "25px", "width": "100%"},

                    # 左側：外格
                    {"type": "box", "layout": "vertical", "position": "absolute", "left": "35px", "top": "110px", "contents": [
                        {"type": "text", "text": "外格", "size": "xs", "color": "#999999", "align": "center"},
                        {"type": "text", "text": get_el(wai), "size": "xl", "weight": "bold", "color": "#333333", "align": "center"}
                    ]},

                    # 中間：姓名主體
                    {"type": "box", "layout": "vertical", "position": "absolute", "width": "100%", "top": "80px", "contents": name_contents},

                    # 中間偏右：天、人、地格
                    {"type": "box", "layout": "vertical", "position": "absolute", "right": "100px", "top": "75px", "spacing": "lg", "contents": [
                        {"type": "box", "layout": "vertical", "contents": [
                            {"type": "text", "text": "天格", "size": "xxs", "color": "#999999"},
                            {"type": "text", "text": get_el(tian), "size": "md", "weight": "bold", "color": "#333333"}
                        ]},
                        {"type": "box", "layout": "vertical", "contents": [
                            {"type": "text", "text": "人格", "size": "xxs", "color": "#999999"},
                            {"type": "text", "text": get_el(ren), "size": "md", "weight": "bold", "color": "#333333"}
                        ]},
                        {"type": "box", "layout": "vertical", "contents": [
                            {"type": "text", "text": "地格", "size": "xxs", "color": "#999999"},
                            {"type": "text", "text": get_el(di), "size": "md", "weight": "bold", "color": "#333333"}
                        ]}
                    ]},

                    # 右側：出生年
                    {"type": "box", "layout": "vertical", "position": "absolute", "right": "35px", "top": "100px", "contents": [
                        {"type": "text", "text": "出生年", "size": "xs", "color": "#999999", "align": "center"},
                        {"type": "text", "text": str(year_str) if year_str else "1990", "size": "sm", "color": "#333333", "align": "center", "weight": "bold"},
                        {"type": "text", "text": "土", "size": "xl", "weight": "bold", "color": "#333333", "align": "center", "margin": "md"}
                    ]},

                    # 水平分割線 (重點：圖片中那條橫線)
                    {"type": "box", "layout": "vertical", "position": "absolute", "width": "80%", "height": "1px", "backgroundColor": "#666666", "top": "270px", "offsetStart": "10%"},

                    # 底部：總格
                    {"type": "box", "layout": "vertical", "position": "absolute", "width": "100%", "top": "285px", "contents": [
                        {"type": "text", "text": "總格", "size": "xxs", "color": "#999999", "align": "center"},
                        {"type": "text", "text": get_el(zong), "size": "xl", "weight": "bold", "color": "#000000", "align": "center"}
                    ]}
                ]
            }
        }
        
        line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text=f"{name_str}鑑定結果", contents=flex_contents))
    except Exception as e:
        logger.error(f"Flex錯誤: {e}")

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    try: handler.handle(body, signature)
    except InvalidSignatureError: abort(400)
    return 'OK'

if __name__ == "__main__":
    app.run()
