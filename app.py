import os
import json
import re
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, FlexSendMessage
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

# --- 2. 輔助函式 ---
def get_stroke_count(char):
    return STROKE_DICT.get(char, 10)

def get_element(number):
    last_digit = int(str(number)[-1])
    map_dict = {1:'木', 2:'木', 3:'火', 4:'火', 5:'土', 6:'土', 7:'金', 8:'金', 9:'水', 0:'水'}
    return map_dict.get(last_digit, '未知')

def get_nayin(year):
    nayins = [
        "海中金","海中金","爐中火","爐中火","大林木","大林木","路旁土","路旁土","劍鋒金","劍鋒金",
        "山頭火","山頭火","澗下水","澗下水","城頭土","城頭土","白蠟金","白蠟金","楊柳木","楊柳木",
        "泉中水","泉中水","屋上土","屋上土","霹靂火","霹靂火","松柏木","松柏木","長流水","長流水",
        "沙中金","沙中金","山下火","山下火","平地木","平地木","壁上土","壁上土","金箔金","金箔金",
        "覆燈火","覆燈火","天河水","天河水","大驛土","大驛土","釵釧金","釵釧金","桑柘木","桑柘木",
        "大溪水","大溪水","沙中土","沙中土","天上火","天上火","石榴木","石榴木","大海水","大海水"
    ]
    try:
        y = int(year)
        if y < 1924: return None
        return nayins[(y - 1924) % 60]
    except: return None

def get_spirit_comment(zong):
    # 龍骨氣判定
    strong_numbers = [15, 16, 21, 23, 29, 31, 33, 37, 45, 52]
    if zong in strong_numbers:
        return "🐉 此名自帶「龍骨氣」，格局宏大。"
    return "✨ 此名格局溫和，處世圓融。"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text.strip()
    match = re.match(r"([^\d\+\s\-]+)[\+\s\-]*(\d*)", msg)
    
    if match:
        full_name = match.group(1)
        birth_year = match.group(2)
        try:
            # 姓名切割與計算
            surname, name = (full_name[:2], full_name[2:]) if len(full_name) >= 3 and full_name[:2] in ["歐陽", "司馬", "諸葛"] else (full_name[:1], full_name[1:])
            s_strk, n_strk = [get_stroke_count(c) for c in surname], [get_stroke_count(c) for c in name]
            tian, ren = (sum(s_strk) if len(surname) > 1 else s_strk[0] + 1), (s_strk[-1] + n_strk[0])
            di, wai = ((n_strk[0] + 1) if len(name) == 1 else sum(n_strk[:2])), (2 if len(name) == 1 else n_strk[-1] + 1)
            zong = sum(s_strk) + sum(n_strk)
            n_res = get_nayin(birth_year)

           # 底圖
            BACKGROUND_URL = "https://raw.githubusercontent.com/Leo1421/line-name-bot/main/background.jpg"

            flex_contents = {
                "type": "bubble",
                "size": "giga",
                "body": {
                    "type": "box", "layout": "vertical", "contents": [
                        # 底圖圖層
                        {"type": "image", "url": BACKGROUND_URL, "aspectMode": "cover", "aspectRatio": "1:1.3", "size": "full", "position": "absolute"},
                        # 內容圖層 (文字疊加在上方)
                        {"type": "box", "layout": "vertical", "contents": [
                            {"type": "text", "text": "- 婉穎命理所 -", "weight": "bold", "color": "#8b4513", "size": "sm", "align": "center"},
                            {"type": "box", "layout": "horizontal", "margin": "xxl", "contents": [
                                # 左側 (天格、外格)
                                {"type": "box", "layout": "vertical", "flex": 1, "spacing": "xl", "contents": [
                                    {"type": "box", "layout": "vertical", "contents": [{"type": "text", "text": "天格", "size": "xs", "color": "#666666"}, {"type": "text", "text": f"{tian} {get_element(tian)}", "weight": "bold", "size": "md"}]},
                                    {"type": "box", "layout": "vertical", "contents": [{"type": "text", "text": "外格", "size": "xs", "color": "#666666"}, {"type": "text", "text": f"{wai} {get_element(wai)}", "weight": "bold", "size": "md"}]}
                                ]},
                                # 中間 (大名字)
                                {"type": "box", "layout": "vertical", "flex": 2, "justifyContent": "center", "contents": [
                                    {"type": "text", "text": full_name, "weight": "bold", "size": "3xl", "align": "center", "color": "#000000"}
                                ]},
                                # 右側 (人格、地格)
                                {"type": "box", "layout": "vertical", "flex": 1, "spacing": "xl", "align": "end", "contents": [
                                    {"type": "box", "layout": "vertical", "align": "end", "contents": [{"type": "text", "text": "人格", "size": "xs", "color": "#666666"}, {"type": "text", "text": f"{ren} {get_element(ren)}", "weight": "bold", "size": "md"}]},
                                    {"type": "box", "layout": "vertical", "align": "end", "contents": [{"type": "text", "text": "地格", "size": "xs", "color": "#666666"}, {"type": "text", "text": f"{di} {get_element(di)}", "weight": "bold", "size": "md"}]}
                                ]}
                            ]},
                            # 底部內容
                            {"type": "box", "layout": "vertical", "margin": "xxl", "contents": [
                                {"type": "text", "text": f"總格：{zong} {get_element(zong)}", "weight": "bold", "size": "xl", "color": "#ff0000", "align": "center"},
                                {"type": "text", "text": f"出生年：{birth_year if birth_year else '--'} ({n_res if n_res else '---'})", "size": "xs", "align": "center", "margin": "sm", "color": "#333333"},
                                {"type": "text", "text": get_spirit_comment(zong), "margin": "md", "size": "xxs", "color": "#888888", "align": "center"}
                            ]}
                        ], "paddingAll": "30px"}
                    ], "paddingAll": "0px"
                }
            }
            line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text=f"{full_name}的分析結果", contents=flex_contents))
        except Exception:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="解析失敗，請輸入：姓名 1990"))

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try: handler.handle(body, signature)
    except InvalidSignatureError: abort(400)
    return 'OK'

if __name__ == "__main__":
    app.run()

