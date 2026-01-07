# ... (前段 get_stroke_count, get_element 等函數保持不變)

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text.strip()
    match = re.match(r"([^\d\+\s\-]+)[\+\s\-]*(\d*)", msg)
    
    if match:
        full_name = match.group(1)
        birth_year = match.group(2)
        try:
            # 判斷姓名邏輯保持不變
            if (len(full_name) >= 3 and full_name[:2] in DOUBLE_SURNAME_LIST) or len(full_name) == 4:
                surname, name = full_name[:2], full_name[2:]
            else:
                surname, name = full_name[:1], full_name[1:]

            s_strk = [get_stroke_count(c) for c in surname]
            n_strk = [get_stroke_count(c) for c in name]
            
            tian = (sum(s_strk) if len(surname) > 1 else s_strk[0] + 1)
            ren = (s_strk[-1] + n_strk[0])
            di = ((n_strk[0] + 1) if len(name) == 1 else sum(n_strk[:2]))
            wai = (2 if len(name) == 1 else n_strk[-1] + (1 if len(surname) == 1 else s_strk[0]))
            zong = sum(s_strk) + sum(n_strk)
            n_res = get_nayin_simple(birth_year)

            BACKGROUND_URL = "https://raw.githubusercontent.com/Leo1421/line-name-bot/main/background.jpg?v=58"
            MAIN_TEXT_COLOR = "#4a4a4a"  # 統一名字與主要資訊的顏色
            SUB_TEXT_COLOR = "#8e8e8e"   # 標籤顏色

            name_with_strokes = []
            for char in full_name:
                stroke = get_stroke_count(char)
                name_with_strokes.append({
                    "type": "box", "layout": "horizontal", "contents": [
                        {"type": "text", "text": char, "weight": "bold", "size": "3xl", "flex": 3, "align": "end", "color": MAIN_TEXT_COLOR},
                        {"type": "text", "text": f"{stroke}", "size": "sm", "flex": 2, "color": "#7a7a7a", "gravity": "center"}
                    ]
                })

            flex_contents = {
                "type": "bubble",
                "size": "giga",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "paddingAll": "0px",
                    "contents": [
                        # 背景圖
                        {
                            "type": "image",
                            "url": BACKGROUND_URL,
                            "size": "full",
                            "aspectMode": "cover",
                            "position": "absolute",
                            "width": "100%",
                            "height": "100%",
                            "gravity": "center"
                        },
                        # 內容區
                        {
                            "type": "box",
                            "layout": "vertical",
                            "paddingAll": "25px",
                            "contents": [
                                {"type": "text", "text": " — 婉 穎 命 光 所 — ", "weight": "bold", "color": "#6d6d6d", "size": "sm", "align": "center", "letterSpacing": "2px"},
                                {"type": "box", "layout": "horizontal", "margin": "xxl", "contents": [
                                    # 1. 外格
                                    {"type": "box", "layout": "vertical", "flex": 15, "justifyContent": "center", "contents": [
                                        {"type": "text", "text": "外格", "size": "xs", "color": SUB_TEXT_COLOR, "align": "center"},
                                        {"type": "text", "text": get_element(wai), "weight": "bold", "align": "center", "size": "sm", "color": MAIN_TEXT_COLOR}
                                    ]},
                                    # 2. 名字
                                    {"type": "box", "layout": "vertical", "flex": 35, "justifyContent": "center", "spacing": "sm", "contents": name_with_strokes},
                                    # 3. 天人地格 (設定為置中對齊)
                                    {"type": "box", "layout": "vertical", "flex": 25, "spacing": "xl", "justifyContent": "center", "contents": [
                                        {"type": "box", "layout": "vertical", "contents": [{"type": "text", "text": "天格", "size": "xs", "color": SUB_TEXT_COLOR, "align": "center"}, {"type": "text", "text": get_element(tian), "weight": "bold", "size": "sm", "color": MAIN_TEXT_COLOR, "align": "center"}]},
                                        {"type": "box", "layout": "vertical", "contents": [{"type": "text", "text": "人格", "size": "xs", "color": SUB_TEXT_COLOR, "align": "center"}, {"type": "text", "text": get_element(ren), "weight": "bold", "size": "sm", "color": MAIN_TEXT_COLOR, "align": "center"}]},
                                        {"type": "box", "layout": "vertical", "contents": [{"type": "text", "text": "地格", "size": "xs", "color": SUB_TEXT_COLOR, "align": "center"}, {"type": "text", "text": get_element(di), "weight": "bold", "size": "sm", "color": MAIN_TEXT_COLOR, "align": "center"}]}
                                    ]},
                                    # 4. 出生年與五行
                                    {"type": "box", "layout": "vertical", "flex": 25, "justifyContent": "center", "spacing": "md", "contents": [
                                        {"type": "box", "layout": "vertical", "contents": [
                                            {"type": "text", "text": "出生年", "size": "xs", "color": SUB_TEXT_COLOR, "align": "center"},
                                            {"type": "text", "text": f"{birth_year if birth_year else '--'}", "weight": "bold", "align": "center", "size": "sm", "color": MAIN_TEXT_COLOR}
                                        ]},
                                        {"type": "text", "text": f"{n_res if n_res else '--'}", "weight": "bold", "align": "center", "size": "sm", "color": MAIN_TEXT_COLOR}
                                    ]}
                                ]},
                                # 強化分隔線：顏色與名字一致
                                {"type": "separator", "margin": "xl", "color": MAIN_TEXT_COLOR},
                                # 5. 總格 (僅保留五行)
                                {"type": "box", "layout": "vertical", "margin": "lg", "paddingBottom": "20px", "contents": [
                                    {"type": "text", "text": "總格", "size": "xs", "color": SUB_TEXT_COLOR, "align": "center"},
                                    {"type": "text", "text": get_element(zong), "weight": "bold", "size": "xl", "color": "#2c2c2c", "align": "center"}
                                ]}
                            ]
                        }
                    ]
                }
            }
            line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text=f"{full_name}鑑定中", contents=flex_contents))
        except Exception:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="解析失敗"))

# ... (後段 callback 保持不變)
