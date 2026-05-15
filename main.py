import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
from datetime import datetime
from dotenv import load_dotenv
from auth_logic import *

# --- 1. 初期設定 ---
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key, transport="rest")
    model = genai.GenerativeModel('models/gemini-3-flash-preview')
else:
    st.error("APIキーがないよ！")
    st.stop()

st.set_page_config(page_title="Dinner Logic DX", layout="wide")

inject_responsive_css()
show_auth_screen()

if st.session_state.get('is_logged_in', False):
    # B. ログイン後のデータ取得
    user_id = st.session_state['current_user']
    df_users = get_all_users()
    user_row = df_users[df_users['user_id'].astype(str) == user_id].iloc[0]
    df_menu = load_menu()

    profile_locked = is_profile_locked(user_row)
    profile_needs_input = not profile_locked or pd.isna(user_row.get('height')) or pd.isna(user_row.get('weight')) or pd.isna(user_row.get('age')) or pd.isna(user_row.get('gender'))

    if profile_needs_input:
        st.title(f"📝 プロフィール登録 ({user_id})")
        st.info("身長・体重・年齢・性別は入力後1か月間固定されます。")

        default_height = safe_float(user_row.get('height', 160.0), 160.0)
        default_weight = safe_float(user_row.get('weight', 55.0), 55.0)
        default_age = safe_int(user_row.get('age', 20), 20)
        default_gender = user_row.get('gender', "女子") if not pd.isna(user_row.get('gender')) else "女子"

        height = st.number_input("身長 (cm)", 100.0, 220.0, default_height, key="register_height")
        weight = st.number_input("体重 (kg)", 30.0, 150.0, default_weight, key="register_weight")
        age = st.number_input("年齢", 15, 100, default_age, key="register_age")
        gender = st.radio("性別", ["女子", "男子"], index=["女子", "男子"].index(default_gender))

        if st.button("プロフィールを保存"):
            save_user(
                user_id,
                user_row['password'],
                user_row['target_weight'],
                user_row['consecutive_days'],
                height=height,
                weight=weight,
                age=age,
                gender=gender,
                profile_saved_date=datetime.now().strftime("%Y-%m-%d")
            )
            st.session_state['height'] = height
            st.session_state['weight'] = weight
            st.session_state['age'] = int(age)
            st.session_state['gender'] = gender
            st.success("プロフィールを保存しました。次回の変更は1か月後にできます。")
            st.rerun()

        st.stop()

    if 'height' not in st.session_state:
        st.session_state['height'] = safe_float(user_row.get('height', 160.0), 160.0)
    if 'weight' not in st.session_state:
        st.session_state['weight'] = safe_float(user_row.get('weight', 55.0), 55.0)
    if 'age' not in st.session_state:
        st.session_state['age'] = safe_int(user_row.get('age', 20), 20)
    if 'gender' not in st.session_state:
        st.session_state['gender'] = user_row.get('gender', "女子")

    # C. 目標設定画面
    if pd.isna(user_row['target_weight']) or datetime.now().day == 1:
        st.title(f"📅 目標設定 ({user_id})")
        t_w = st.number_input("今月の目標体重 (kg)", 30.0, 150.0, 52.0, key="target_weight_input")
        if st.button("目標を保存"):
            save_user(user_id, user_row['password'], t_w)
            st.rerun()
        st.stop()

    # --- 4. メイン画面の準備 ---
    # 画像アバターのパスを1箇所で確定させる！
    if os.path.exists("mii_thunder.jpg"):
        thunder_avatar = "mii_thunder.jpg"
    elif os.path.exists("mii_thunder.png"):
        thunder_avatar = "mii_thunder.png"
    else:
        thunder_avatar = "⚡️"

    st.title(f"🥘 美食家サンダーさん とライエット")

    # --- 連続ログイン日数表示 ---
    consecutive_days = int(user_row.get('consecutive_days', 1))
    st.markdown("---")
    with st.container(border=True):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown(f"<div style='text-align: center;'><h2 style='color: #ff6b6b; margin-bottom: 5px;'>🔥 連続ログイン</h2><p style='font-size: 16px; color: #666; margin: 5px 0;'>あなたは今日で</p><p style='font-size: 48px; font-weight: bold; color: #ff6b6b; margin: 10px 0;'>{consecutive_days}</p><p style='font-size: 16px; color: #666; margin-top: 5px;'>日連続で頑張ってるよ！</p></div>", unsafe_allow_html=True)

    st.markdown("---")

    with st.sidebar:
        st.image(thunder_avatar, width=150, caption="美食家サンダー⚡️")
        st.header("👤 ステータス")
        st.success(f"User: {user_id}\nTarget: {user_row['target_weight']}kg")
        
        weight = st.number_input("今の体重 (kg)", 30.0, 150.0, st.session_state['weight'], disabled=profile_locked, key="sidebar_weight")
        height = st.number_input("身長 (cm)", 100.0, 220.0, st.session_state['height'], disabled=profile_locked, key="sidebar_height")
        age = st.number_input("年齢", 15, 100, st.session_state['age'], disabled=profile_locked, key="sidebar_age")
        gender = st.radio("性別", ["女子", "男子"], index=["女子", "男子"].index(st.session_state['gender']), disabled=profile_locked)
        
        st.markdown("---")
        levels = {"1.2：座りっぱなし": 1.2, "1.375：軽い運動": 1.375, "1.55：適度な運動": 1.55, "1.725：活発な運動": 1.725, "1.9：非常に活発": 1.9}
        activity = levels[st.selectbox("生活スタイル", list(levels.keys()))]
        
        if st.button("ログアウト"):
            st.session_state.clear()
            st.rerun()

    # --- 通知・リマインド ---
    target_weight = float(user_row['target_weight'])
    current_weight = weight
    weight_diff = target_weight - current_weight
    days_in_month = 30  # 簡易的に30日
    days_remaining = days_in_month - datetime.now().day + 1
    progress_rate = max(0, min(100, (1 - abs(weight_diff) / 5) * 100))  # 仮の計算

    st.markdown("---")
    with st.container(border=True):
        st.markdown(f"<div style='text-align: center;'><h3 style='color: #2196F3;'>📅 今月の目標確認</h3><p style='font-size: 16px; color: #666;'>目標体重: {target_weight}kg | 現在体重: {current_weight}kg</p><p style='font-size: 18px; color: #ff6b6b; font-weight: bold;'>残り{weight_diff:.1f}kg | 達成率: {progress_rate:.1f}% | 残り{days_remaining}日</p></div>", unsafe_allow_html=True)

    st.markdown("---")

    # --- 5. 計算ロジック ---
    bmr = (447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)) if gender == "女子" else (88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age))
    target_cal = (bmr * activity) - ((weight - float(user_row['target_weight'])) * 7200 / 30)

    # --- 食事履歴の保存・復元 ---
    today = datetime.now().date().isoformat()
    if 'meal_history' not in st.session_state:
        st.session_state['meal_history'] = {}
    if today not in st.session_state['meal_history']:
        st.session_state['meal_history'][today] = {'breakfast': [], 'lunch': []}

    # 次回復元
    b_items = st.session_state['meal_history'][today]['breakfast']
    l_items = st.session_state['meal_history'][today]['lunch']

    col1, col2 = st.columns(2)
    with col1:
        b_items = st.multiselect("朝食", df_menu['display'].tolist() if not df_menu.empty else [], default=b_items)
    with col2:
        l_items = st.multiselect("昼食", df_menu['display'].tolist() if not df_menu.empty else [], default=l_items)

    # 選択を保存
    st.session_state['meal_history'][today]['breakfast'] = b_items
    st.session_state['meal_history'][today]['lunch'] = l_items


    # 選択された朝食と昼食の表示
    if b_items or l_items:
        st.subheader("🍽️ 選択されたメニュー")
        
        col1, col2 = st.columns(2)
        
        # 朝食の表示
        if b_items:
            with col1:
                with st.container(border=True):
                    st.markdown(f"<h3 style='text-align: center; color: #ffa500;'>🌅 朝食</h3>", unsafe_allow_html=True)
                    for item in b_items:
                        st.markdown(f"<p style='text-align: center; color: #666; font-size: 14px; font-weight: bold;'>✓ {item}</p>", unsafe_allow_html=True)
        
        # 昼食の表示
        if l_items:
            with col2:
                with st.container(border=True):
                    st.markdown(f"<h3 style='text-align: center; color: #4CAF50;'>☀️ 昼食</h3>", unsafe_allow_html=True)
                    for item in l_items:
                        st.markdown(f"<p style='text-align: center; color: #666; font-size: 14px; font-weight: bold;'>✓ {item}</p>", unsafe_allow_html=True)


    dinner_cal = target_cal - (df_menu[df_menu['display'].isin(b_items)]['cal'].sum() + df_menu[df_menu['display'].isin(l_items)]['cal'].sum())
    st.metric("今日の残り枠", f"{int(dinner_cal)} kcal")

    # --- 6. 自動挨拶（1回だけ表示！） ---
    st.divider()
    with st.chat_message("assistant", avatar=thunder_avatar):
        if dinner_cal > 500:
            st.write(f"あったまいいね！今日はまだ {int(dinner_cal)}kcal も余裕があるわ。美味しいもの探しに行こうよ！")
        elif dinner_cal > 0:
            st.write(f"今のところ順調ね。夜は控えめな美食を楽しんで！")
        else:
            st.write(f"ちょっと！もうカロリーオーバーよ！明日は火鍋禁止ね！")

    # --- 7. おすすめメニュー表示 ---
    st.subheader("🥢 サンダーさんのおすすめ")
    if not df_menu.empty:
        recs = df_menu[df_menu['cal'] <= dinner_cal].sort_values(by='cal', ascending=False).head(5)
        if not recs.empty:
            cols = st.columns(5, gap="medium")
            for i, (_, row) in enumerate(recs.iterrows()):
                with cols[i]:
                    with st.container(border=True):
                        st.markdown(f"<h3 style='text-align: center;'>🍽️</h3>", unsafe_allow_html=True)
                        st.markdown(f"<p style='text-align: center; font-weight: bold; font-size: 16px;'>{row['store']}</p>", unsafe_allow_html=True)
                        st.markdown(f"<p style='text-align: center; color: #666; font-size: 14px;'>{row['name']}</p>", unsafe_allow_html=True)
                        st.markdown(f"<p style='text-align: center; color: #ff6b6b; font-size: 18px; font-weight: bold;'>✨ {int(row['cal'])} kcal</p>", unsafe_allow_html=True)
                        if st.button("選択する", key=f"rec_{i}", use_container_width=True):
                            st.session_state['selected_dinner'] = row['name']
                            st.session_state['selected_dinner_cal'] = int(row['cal'])
                            st.success(f"「{row['name']}」を夕食に選択しました！")
        else:
            st.write("おすすめメニューが見つかりません。")
    else:
        st.write("メニューが読み込めません。")

    # --- 7.5 朝昼夕の合計摂取カロリー表示 ---
    breakfast_cal = df_menu[df_menu['display'].isin(b_items)]['cal'].sum()
    lunch_cal = df_menu[df_menu['display'].isin(l_items)]['cal'].sum()
    total_cal = breakfast_cal + lunch_cal + st.session_state['selected_dinner_cal']

    st.markdown("---")
    st.subheader("📊 本日の栄養摂取状況")
    with st.container(border=True):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"<div style='text-align: center;'><p style='font-size: 14px; color: #666;'>🌅 朝食</p><p style='font-size: 24px; font-weight: bold; color: #ffa500;'>{int(breakfast_cal)}</p><p style='font-size: 12px; color: #999;'>kcal</p></div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"<div style='text-align: center;'><p style='font-size: 14px; color: #666;'>☀️ 昼食</p><p style='font-size: 24px; font-weight: bold; color: #4CAF50;'>{int(lunch_cal)}</p><p style='font-size: 12px; color: #999;'>kcal</p></div>", unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"<div style='text-align: center;'><p style='font-size: 14px; color: #666;'>🌙 夕食</p><p style='font-size: 24px; font-weight: bold; color: #2196F3;'>{st.session_state['selected_dinner_cal']}</p><p style='font-size: 12px; color: #999;'>kcal</p></div>", unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"<div style='text-align: center;'><p style='font-size: 14px; color: #666;'>✅ 合計</p><p style='font-size: 28px; font-weight: bold; color: #ff6b6b;'>{int(total_cal)}</p><p style='font-size: 12px; color: #999;'>kcal</p></div>", unsafe_allow_html=True)

    # --- 食事履歴ログ ---
    st.markdown("---")
    st.subheader("📝 今日の食事履歴")
    with st.container(border=True):
        if b_items:
            st.markdown("**🌅 朝食:** " + ", ".join(b_items))
        else:
            st.markdown("**🌅 朝食:** 未選択")
        if l_items:
            st.markdown("**☀️ 昼食:** " + ", ".join(l_items))
        else:
            st.markdown("**☀️ 昼食:** 未選択")
        if st.session_state.get('selected_dinner'):
            st.markdown(f"**🌙 夕食:** {st.session_state['selected_dinner']} ({st.session_state['selected_dinner_cal']}kcal)")
        else:
            st.markdown("**🌙 夕食:** 未選択")

    # --- 8. AI相談室 ---
    if user_msg := st.chat_input("美食家サンダーさんに相談"):
        with st.chat_message("assistant", avatar=thunder_avatar):
            prompt = f"あなたは中国の美食を求めて旅する女子大生サンダーさん。口癖『あったまいいね！』。相手{user_id}。残り{int(dinner_cal)}kcal。質問:{user_msg}"
            try:
                response = model.generate_content(prompt)
                st.write(response.text)
            except Exception as e:
                st.error(f"AIエラー: {e}")

    with st.sidebar:
        st.markdown("---")
        st.write("🎵 雷さんのBGM")
        # YouTubeを埋め込む（autoplay=Trueにしてもブラウザの設定で止まることがあるから、再生ボタンを押してね！）
        st.video("https://youtu.be/l7Tr8xb_tFk", format="video/mp4", start_time=0)