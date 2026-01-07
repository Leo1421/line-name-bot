import os
import json
import re
import logging
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, FlexSendMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 環境變數設定 ---
line_bot_api = LineBotApi(os.environ.get('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('CHANNEL_SECRET'))

# --- 1. 讀取康熙筆畫資料 ---
KANGXI_JSON_PATH = os.path.join(os.path.dirname(__file__), "kangxi_total_strokes_kv.json")
try:
    with open(KANGXI_JSON_PATH, "r", encoding="utf-8") as f:
        STROKE_DICT = json.load(f)
except Exception:
    STROKE_DICT = {}

DOUBLE_SURNAME_LIST = [
    "張簡", "歐陽", "范姜", "周黃", "張廖", "張李", "張許", "張陳", 
    "劉張", "陳吳", "陳李", "陳黃", "李林", "郭李", "鄭黃", "江謝", 
    "翁林", "姜林", "阮呂", "曾江", "簡蕭", "鍾巴", "朱陳", "梁丘", 
    "吳鄭", "洪許", "徐辜", "胡周", "葉劉", "蔡黃", "蘇陳", "莊吳",
    "諸葛", "司馬", "司徒", "上官", "端木", "皇甫", "尉遲", "公孫", 
    "軒轅", "令狐", "鍾離", "宇文", "鮮于", "東方", "南宮", "長孫", 
    "夏侯", "申屠", "公羊", "澹台", "獨孤", "第伍", "濮陽", "賀蘭"
]

def get_stroke_count(char):
    return STROKE_DICT.get(char, 10)

def get_element(number):
    last_digit = int(str(number)[-1])
    map_dict = {1:'木', 2:'木', 3:'火', 4:'火', 5:'土', 6:'土', 7:'金', 8:'金', 9:'水', 0:'水'}
    return map_dict.get(last_digit, '未知')

def get_nayin_simple(year):
    nayins = ["海中金","爐中火","大林木","路旁土","劍鋒金","山頭火","澗下水","城頭土","白蠟金","楊柳木",
              "泉中水","屋上土","霹靂火","松柏木","長流水","沙中金","山下火","平地木","壁上土","金箔金",
              "覆燈火","天河水","大驛土","釵釧金","桑柘木","大溪水","沙中土","天上火","石榴木","大海水"]
    try:
        y = int(year)
        if y < 1924: return None
        return nayins[((y - 1924) % 60) // 2][-1] 
    except: return None

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text.strip()
    match = re.match(r"([^\d\+\s\-]+)[\+\s\-]*(\d*)", msg)
    
    if match:
        full_name = match.group(1)
        birth_year = match.group(2)
        try:
            if (len(full_name) >= 3 and full_name[:2] in DOUBLE_SURNAME_LIST) or len(full_name) == 4:
                surname, name_part = full_name[:2], full_name[2:]
            else:
                surname, name_part = full_name[:1], full_name[1:]

            s_strk = [get_stroke_count(c) for c in surname]
            n_strk = [get_stroke_count(c) for c in name_part] if name_part else [10]
            
            zong = sum(s_strk) + sum(n_strk)
            tian = (sum(s_strk) if len(surname) > 1 else s_strk[0] + 1)
            ren = (s_strk[-1] + n_strk[0])
            di = ((n_strk[0] + 1) if len(name_part) <= 1 else sum(n_strk))
            wai = 2 if len(full_name) == 2 else zong - ren + 1
            
            n_res = get_nayin_simple(birth_year)

            # --- 配置設定 ---
            BACKGROUND_URL = "https://raw.githubusercontent.com/Leo1421/line-name-bot/main/background.jpg?v=86"
            MAIN_TEXT_COLOR = "#333333" 
            SUB_TEXT_COLOR = "#999999"  

            # 名字與筆畫置中
            name_with_strokes = []
            for char in full_name:
                stroke = get_stroke_count(char)
                name_with_strokes.append({
                    "type": "box", "layout": "horizontal", "alignItems": "center",
                    "contents": [
                        {"type": "text", "text": char, "weight": "bold", "size": "xl", "flex": 0, "color": MAIN_TEXT_COLOR},
                        {"type": "text", "text": str(stroke), "size": "xxs", "flex": 0, "color": "#aaaaaa", "margin": "sm"}
                    ],
                    "justifyContent": "center"
                })

            flex_contents = {
                "type": "bubble",
                "size": "mega",
                "body": {
                    "type": "box", "layout": "vertical", "paddingAll": "0px",
                    "contents": [
                        {"type": "image", "url": BACKGROUND_URL, "size": "full", "aspectMode": "cover", "position": "absolute"},
                        {
                            "type": "box", "layout": "vertical", "paddingTop": "35px", "paddingBottom": "35px", "paddingStart": "15px", "paddingEnd": "15px",
                            "contents": [
                                {"type": "text", "text": "  婉 穎 命 光 所  ", "weight": "bold", "color": "#777777", "size": "xs", "align": "center", "letterSpacing": "2px"},
                                
                                # 四大區塊
                                {"type": "box", "layout": "horizontal", "margin": "xxl", "contents": [
                                    {"type": "box", "layout": "vertical", "flex": 1, "justifyContent": "center", "contents": [
                                        {"type": "text", "text": "外格", "size": "xxs", "color": SUB_TEXT_COLOR, "align": "center"},
                                        {"type": "text", "text": get_element(wai), "weight": "bold", "align": "center", "size": "md", "color": MAIN_TEXT_COLOR}
                                    ]},
                                    {"type": "box", "layout": "vertical", "flex": 2, "justifyContent": "center", "spacing": "md", "contents": name_with_strokes},
                                    {"type": "box", "layout": "vertical", "flex": 1, "spacing": "md", "justifyContent": "center", "contents": [
                                        {"type": "box", "layout": "vertical", "contents": [{"type": "text", "text": "天格", "size": "xxs", "color": SUB_TEXT_COLOR, "align": "center"}, {"type": "text", "text": get_element(tian), "weight": "bold", "size": "md", "color": MAIN_TEXT_COLOR, "align": "center"}]},
                                        {"type": "box", "layout": "vertical", "contents": [{"type": "text", "text": "人格", "size": "xxs", "color": SUB_TEXT_COLOR, "align": "center"}, {"type": "text", "text": get_element(ren), "weight": "bold", "size": "md", "color": MAIN_TEXT_COLOR, "align": "center"}]},
                                        {"type": "box", "layout": "vertical", "contents": [{"type": "text", "text": "地格", "size": "xxs", "color": SUB_TEXT_COLOR, "align": "center"}, {"type": "text", "text": get_element(di), "weight": "bold", "size": "md", "color": MAIN_TEXT_COLOR, "align": "center"}]}
                                    ]},
                                    {"type": "box", "layout": "vertical", "flex": 1, "justifyContent": "center", "spacing": "sm", "contents": [
                                        {"type": "text", "text": "出生年", "size": "xxs", "color": SUB_TEXT_COLOR, "align": "center"},
                                        {"type": "text", "text": str(birth_year) if birth_year else "--", "weight": "bold", "align": "center", "size": "xs", "color": MAIN_TEXT_COLOR},
                                        {"type": "text", "text": str(n_res) if n_res else "--", "weight": "bold", "align": "center", "size": "md", "color": MAIN_TEXT_COLOR}
                                    ]}
                                ]},

                                # 自定義實體分隔線 (使用 box 模擬)
                                {
                                    "type": "box", 
                                    "layout": "vertical", 
                                    "margin": "xxl", 
                                    "height": "1px", 
                                    "backgroundColor": MAIN_TEXT_COLOR, # 這裡使用跟名字一樣的深灰色
                                    "width": "90%",
                                    "offsetStart": "5%"
                                },

                                # 總格
                                {"type": "box", "layout": "vertical", "margin": "xl", "contents": [
                                    {"type": "text", "text": "總格五行", "size": "xxs", "color": SUB_TEXT_COLOR, "align": "center"},
                                    {"type": "text", "text": get_element(zong), "weight": "bold", "size": "lg", "color": "#000000", "align": "center"}
                                ]}
                            ]
                        }
                    ]
                }
            }
            line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text=f"{full_name}鑑定結果", contents=flex_contents))
        except Exception as e:
            logger.error(f"Error: {e}")

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

