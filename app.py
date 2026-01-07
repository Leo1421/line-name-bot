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
        
        # 2. 構建名字欄位 (經典垂直排列)
        name_boxes = []
        for c in name_str:
            name_boxes.append({
                "type": "box", "layout": "horizontal", "contents": [
                    {"type": "text", "text": c, "weight": "bold", "size": "3xl", "flex": 3, "align": "end", "color": "#333333"},
                    {"type": "text", "text": str(get_stroke(c)), "size": "sm", "flex": 2, "color": "#888888", "margin": "md"}
                ]
            })

        # 3. 完整 Flex 設計
        flex_contents = {
            "type": "bubble",
            "size": "mega",
            "body": {
                "type": "box", "layout": "vertical", "paddingAll": "0px",
                "contents": [
                    # 穩定版背景
                    {"type": "image", "url": "https://raw.githubusercontent.com/Leo1421/line-name-bot/main/background.jpg?v=115", "size": "full", "aspectMode": "cover", "position": "absolute"},
                    {
                        "type": "box", "layout": "vertical", "paddingTop": "40px", "paddingBottom": "70px", "paddingStart": "20px", "paddingEnd": "20px",
                        "contents": [
                            # 頂部標題
                            {"type": "text", "text": "— 婉 穎 命 光 所 —", "weight": "bold", "color": "#777777", "size": "xs", "align": "center"},
                            
                            # 核心區：橫向四欄佈局 (找回原本的感覺)
                            {"type": "box", "layout": "horizontal", "margin": "xxl", "contents": [
                                # 第一欄：外格
                                {"type": "box", "layout": "vertical", "flex": 1, "justifyContent": "center", "contents": [
                                    {"type": "text", "text": "外格", "size": "xxs", "color": "#999999", "align": "center"},
                                    {"type": "text", "text": get_el(wai), "weight": "bold", "size": "xl", "align": "center", "color": "#9B7C48"}
                                ]},
                                # 第二欄：名字主體 (Flex佔比最大)
                                {"type": "box", "layout": "vertical", "flex": 2, "spacing": "sm", "contents": name_boxes},
                                # 第三欄：三才屬性
                                {"type": "box", "layout": "vertical", "flex": 1, "spacing": "md", "contents": [
                                    {"type": "text", "text": f"天{get_el(tian)}", "weight": "bold", "size": "md", "align": "center", "color": "#9B7C48"},
                                    {"type": "text", "text": f"人{get_el(ren)}", "weight": "bold", "size": "md", "align": "center", "color": "#9B7C48"},
                                    {"type": "text", "text": f"地{get_el(di)}", "weight": "bold", "size": "md", "align": "center", "color": "#9B7C48"}
                                ]},
                                # 第四欄：出生與納音
                                {"type": "box", "layout": "vertical", "flex": 1, "justifyContent": "center", "contents": [
                                    {"type": "text", "text": str(year_str) if year_str else "--", "size": "xxs", "color": "#999999", "align": "center"},
                                    {"type": "text", "text": get_ny(year_str), "weight": "bold", "size": "md", "align": "center", "color": "#555555"}
                                ]}
                            ]},
                            
                            # 底部總格 (獨立出來更有份量)
                            {"type": "box", "layout": "vertical", "margin": "xxl", "contents": [
                                {"type": "text", "text": "總格五行", "size": "xxs", "color": "#999999", "align": "center"},
                                {"type": "text", "text": get_el(zong), "weight": "bold", "size": "xxl", "align": "center", "color": "#D35400"}
                            ]}
                        ]
                    }
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
