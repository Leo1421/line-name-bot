import os
import json
import re
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, FlexSendMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ.get('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('CHANNEL_SECRET'))

# --- 1. 讀取康熙筆畫 ---
KANGXI_JSON_PATH = os.path.join(os.path.dirname(__file__), "kangxi_total_strokes_kv.json")
try:
    with open(KANGXI_JSON_PATH, "r", encoding="utf-8") as f:
        STROKE_DICT = json.load(f)
except Exception:
    STROKE_DICT = {}

def get_stroke_count(char):
    return STROKE_DICT.get(char, 10)

def get_element(number):
    last_digit = int(str(number)[-1])
    map_dict = {1:'木', 2:'木', 3:'火', 4:'火', 5:'土', 6:'土', 7:'金', 8:'金', 9:'水', 0:'水'}
    return map_dict.get(last_digit, '未知')

def get_nayin(year):
    nayins = ["海中金","爐中火","大林木","路旁土","劍鋒金","山頭火","澗下水","城頭土","白蠟金","楊柳木",
              "泉中水","屋上土","霹靂火","松柏木","長流水","沙中金","山下火","平地木","壁上土","金箔金",
              "覆燈火","天河水","大驛土","釵釧金","桑柘木","大溪水","沙中土","天上火","石榴木","大海水"]
    try:
        y = int(year)
        if y < 1924: return None
        return nayins[((y - 1924) % 60) // 2]
    except: return None

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text.strip()
    match = re.match(r"([^\d\+\s\-]+)[\+\s\-]*(\d*)", msg)
    
    if match:
        full_name = match.group(1)
        birth_year = match.group(2)
        try:
            # 筆畫計算
            surname, name = (full_name[:2], full_name[2:]) if len(full_name) >= 3 and full_name[:2] in ["歐陽", "司馬", "諸葛"] else (full_name[:1], full_name[1:])
            s_strk, n_strk = [get_stroke_count(c) for c in surname], [get_stroke_count(c) for c in name]
            tian = (sum(s_strk) if len(surname) > 1 else s_strk[0] + 1)
            ren = (s_strk[-1] + n_strk[0])
            di = ((n_strk[0] + 1) if len(name) == 1 else sum(n_strk[:2]))
            wai = (2 if len(name) == 1 else n_strk[-1] + 1)
            zong = sum(s_strk) + sum(n_strk)
            n_res = get_nayin(birth_year)

            # 更新網址版本以破解快取
            BACKGROUND_URL = "https://raw.githubusercontent.com/Leo1421/line-name-bot/main/background.jpg?v=7"

            # 【名字加大且直排】組件：增加 spacing 使字與字之間拉開，以對齊右側三格
            name_chars = [{"type": "text", "text": c, "weight": "bold", "size": "3xl", "align": "center", "color": "#000000"} for c in full_name]

            flex_contents = {
                "type": "bubble",
                "size": "giga",
                "body": {
                    "type": "box", "layout": "vertical", "paddingAll": "0px",
                    "contents": [
                        # 底圖
                        {
                            "type": "image", "url": BACKGROUND_URL, 
                            "aspectMode": "cover", "aspectRatio": "1:1.2", 
                            "size": "full", "position": "absolute"
                        },
                        # 內容容器
                        {"type": "box", "layout": "vertical", "paddingAll": "20px", "contents": [
                            {"type": "text", "text": "- 婉穎命理所 -", "weight": "bold", "color": "#8b4513", "size": "sm", "align": "center"},
                            
                            # 核心區：外格 | 直排名字 | 天人地 | 出生年
                            {"type": "box", "layout": "horizontal", "margin": "xxl", "contents": [
                                # 1. 外格
                                {"type": "box", "layout": "vertical", "flex": 2, "justifyContent": "center", "contents": [
                                    {"type": "text", "text": "外格", "size": "xs", "color": "#666666", "align": "center"},
                                    {"type": "text", "text": f"{wai} {get_element(wai)}", "weight": "bold", "align": "center", "size": "md"}
                                ]},
                                # 2. 直排名字 (加大且增加間距)
                                {"type": "box", "layout": "vertical", "flex": 3, "justifyContent": "center", "spacing": "lg", "contents": name_chars},
                                # 3. 天人地格 (右側對齊名字)
                                {"type": "box", "layout": "vertical", "flex": 3, "spacing": "xl", "justifyContent": "center", "paddingStart": "10px", "contents": [
                                    {"type": "box", "layout": "vertical", "contents": [{"type": "text", "text": "天格", "size": "xs", "color": "#666666"}, {"type": "text", "text": f"{tian} {get_element(tian)}", "weight": "bold", "size": "sm"}]},
                                    {"type": "box", "layout": "vertical", "contents": [{"type": "text", "text": "人格", "size": "xs", "color": "#666666"}, {"type": "text", "text": f"{ren} {get_element(ren)}", "weight": "bold", "size": "sm"}]},
                                    {"type": "box", "layout": "vertical", "contents": [{"type": "text", "text": "地格", "size": "xs", "color": "#666666"}, {"type": "text", "text": f"{di} {get_element(di)}", "weight": "bold", "size": "sm"}]}
                                ]},
                                # 4. 出生年
                                {"type": "box", "layout": "vertical", "flex": 2, "justifyContent": "center", "contents": [
                                    {"type": "text", "text": "出生年", "size": "xs", "color": "#666666", "align": "center"},
                                    {"type": "text", "text": f"{birth_year if birth_year else '--'}", "weight": "bold", "align": "center", "size": "sm"},
                                    {"type": "text", "text": f"({n_res if n_res else '--'})", "size": "xxs", "align": "center"}
                                ]}
                            ]},
                            
                            # 分隔線
                            {"type": "separator", "margin": "xxl", "color": "#333333"},
                            
                            # 底部總格
                            {"type": "box", "layout": "vertical", "margin": "lg", "contents": [
                                {"type": "text", "text": "總格", "size": "xs", "color": "#666666", "align": "center"},
                                {"type": "text", "text": f"{zong} {get_element(zong)}", "weight": "bold", "size": "xl", "color": "#ff0000", "align": "center"}
                            ]}
                        ]}
                    ]
                }
            }
            line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text=f"{full_name}鑑定書", contents=flex_contents))
        except Exception:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="格式錯誤。"))

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try: handler.handle(body, signature)
    except InvalidSignatureError: abort(400)
    return 'OK'

if __name__ == "__main__":
    app.run()
