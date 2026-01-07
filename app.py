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
def get_ny_el(y): # 取得納音五行屬性
    nayins = ["海中金","爐中火","大林木","路旁土","劍鋒金","山頭火","澗下水","城頭土","白蠟金","楊柳木",
              "泉中水","屋上土","霹靂火","松柏木","長流水","沙中金","山下火","平地木","壁上土","金箔金",
              "覆燈火","天河水","大驛土","釵釧金","桑柘木","大溪水","沙中土","天上火","石榴木","大海水"]
    try:
        val = int(y)
        if val < 1924: return "--"
        return nayins[((val - 1924) % 60) // 2][-1]
    except: return "？"

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
        
        # 2. 構建名字與筆畫 (垂直排，加大間距避免擁擠)
        name_contents = []
        for c in name_str:
            name_contents.append({
                "type": "box", "layout": "horizontal", "contents": [
                    {"type": "text", "text": c, "size": "3xl", "weight": "bold", "color": "#444444", "flex": 0},
                    {"type": "text", "text": str(get_stroke(c)), "size": "xs", "color": "#aaaaaa", "margin": "sm"}
                ],
                "justifyContent": "center"
            })

        # 3. 完整 Flex 設計 (加大間距版)
        flex_contents = {
            "type": "bubble",
            "size": "mega",
            "body": {
                "type": "box", "layout": "vertical", "paddingAll": "0px", "height": "400px",
                "contents": [
                    # 背景圖
                    {"type": "image", "url": "https://raw.githubusercontent.com/Leo1421/line-name-bot/main/background.jpg?v=125", "size": "full", "aspectMode": "cover", "position": "absolute"},
                    
                    # 頂部標題
                    {"type": "text", "text": "— 婉 穎 命 光 所 —", "size": "sm", "color": "#777777", "align": "center", "position": "absolute", "offsetTop": "25px", "width": "100%"},

                    # 左側：外格 (位置向左推)
                    {"type": "box", "layout": "vertical", "position": "absolute", "left": "25px", "top": "115px", "width": "60px", "contents": [
                        {"type": "text", "text": "外格", "size": "xs", "color": "#aaaaaa", "align": "center"},
                        {"type": "text", "text": get_el(wai), "size": "xl", "weight": "bold", "color": "#333333", "align": "center", "margin": "md"}
                    ]},

                    # 中間：姓名主體 (加大 spacing)
                    {"type": "box", "layout": "vertical", "position": "absolute", "width": "100%", "top": "85px", "spacing": "md", "contents": name_contents},

                    # 中間偏右：天、人、地格 (拉開上下間距)
                    {"type": "box", "layout": "vertical", "position": "absolute", "right": "95px", "top": "80px", "spacing": "xl", "contents": [
                        {"type": "box", "layout": "vertical", "contents": [
                            {"type": "text", "text": "天格", "size": "xxs", "color": "#aaaaaa"},
                            {"type": "text", "text": get_el(tian), "size": "md", "weight": "bold", "color": "#333333"}
                        ]},
                        {"type": "box", "layout": "vertical", "contents": [
                            {"type": "text", "text": "人格", "size": "xxs", "color": "#aaaaaa"},
                            {"type": "text", "text": get_el(ren), "size": "md", "weight": "bold", "color": "#333333"}
                        ]},
                        {"type": "box", "layout": "vertical", "contents": [
                            {"type": "text", "text": "地格", "size": "xxs", "color": "#aaaaaa"},
                            {"type": "text", "text": get_el(di), "size": "md", "weight": "bold", "color": "#333333"}
                        ]}
                    ]},

                    # 右側：出生年 (位置向右推)
                    {"type": "box", "layout": "vertical", "position": "absolute", "right": "25px", "top": "105px", "width": "60px", "contents": [
                        {"type": "text", "text": "出生年", "size": "xs", "color": "#aaaaaa", "align": "center"},
                        {"type": "text", "text": str(year_str) if year_str else "----", "size": "xs", "color": "#444444", "align": "center", "weight": "bold"},
                        {"type": "text", "text": get_ny_el(year_str), "size": "xl", "weight": "bold", "color": "#333333", "align": "center", "margin": "lg"}
                    ]},

                    # 水平分割線 (加深顏色並調整位置)
                    {"type": "box", "layout": "vertical", "position": "absolute", "width": "84%", "height": "1px", "backgroundColor": "#888888", "top": "290px", "offsetStart": "8%"},

                    # 底部：總格
                    {"type": "box", "layout": "vertical", "position": "absolute", "width": "100%", "top": "305px", "contents": [
                        {"type": "text", "text": "總格", "size": "xxs", "color": "#aaaaaa", "align": "center"},
                        {"type": "text", "text": get_el(zong), "size": "xl", "weight": "bold", "color": "#000000", "align": "center", "margin": "xs"}
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
