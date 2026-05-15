import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
from datetime import datetime
from dotenv import load_dotenv

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

# --- 2. データ管理関数 ---
USER_FILE = "user_settings.csv"
MENU_FILE = "dinner_list.csv"

def get_all_users():
    cols = ["user_id", "password", "target_weight", "height", "weight", "age", "gender", "profile_saved_date", "last_update", "consecutive_days"]
    if os.path.exists(USER_FILE):
        try:
            df = pd.read_csv(USER_FILE)
            for c in cols:
                if c not in df.columns:
                    df[c] = None
            return df
        except:
            return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def safe_float(value, default=0.0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except:
        return default

def safe_int(value, default=0):
    try:
        if pd.isna(value):
            return default
        return int(float(value))
    except:
        return default

def inject_responsive_css():
    css = """
    <style>
    /* 全体の余白を調整 */
    .main .block-container {
        padding-top: 1rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    @media (max-width: 900px) {
        section[data-testid="stSidebar"], section[data-testid="stApp"] .block-container {
            width: 100% !important;
            max-width: 100% !important;
            position: relative !important;
            margin: 0 auto !important;
        }

        div[data-testid="stSidebar"] {
            min-width: 0 !important;
        }

        button, input, select, textarea {
            width: 100% !important;
            min-width: 0 !important;
            box-sizing: border-box !important;
        }

        .stButton > button {
            padding: 0.9rem 1rem !important;
            font-size: 1rem !important;
        }

        .stTextInput>div, .stNumberInput>div, .stSelectbox>div, .stRadio>div,
        .stTextInput, .stNumberInput, .stSelectbox, .stRadio,
        .stMarkdown, .stInfo, .stSuccess, .stWarning, .stError {
            width: 100% !important;
            max-width: 100% !important;
        }

        .stMarkdown p, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
            font-size: 1rem !important;
            line-height: 1.5 !important;
        }

        .stSidebar .css-1avgm1g,
        .stSidebar .css-1d391kg,
        .stSidebar .css-1n2mwow {
            flex-direction: column !important;
            width: 100% !important;
        }

        .css-1n2mwow > div,
        .css-1d391kg > div,
        .css-1avgm1g > div {
            width: 100% !important;
            min-width: 0 !important;
        }

        .css-10trblm, .css-1lcbmhc {
            width: 100% !important;
        }

        .css-1q8dd3e {
            grid-template-columns: 1fr !important;
        }
    }
    """
    st.markdown(css, unsafe_allow_html=True)


def save_user(user_id, password, target_weight=None, consecutive_days=None, height=None, weight=None, age=None, gender=None, profile_saved_date=None):
    df = get_all_users()
    u_str = str(user_id)
    if profile_saved_date is None and (height is not None or weight is not None or age is not None or gender is not None):
        profile_saved_date = datetime.now().strftime("%Y-%m-%d")

    if u_str in df['user_id'].astype(str).values:
        idx = df[df['user_id'].astype(str) == u_str].index[0]
        if password: df.at[idx, 'password'] = password
        if target_weight is not None:
            df.at[idx, 'target_weight'] = target_weight
            df.at[idx, 'last_update'] = datetime.now().strftime("%Y-%m-%d")
        if consecutive_days is not None:
            df.at[idx, 'consecutive_days'] = consecutive_days
        if height is not None:
            df.at[idx, 'height'] = height
        if weight is not None:
            df.at[idx, 'weight'] = weight
        if age is not None:
            df.at[idx, 'age'] = age
        if gender is not None:
            df.at[idx, 'gender'] = gender
        if profile_saved_date is not None:
            df.at[idx, 'profile_saved_date'] = profile_saved_date
    else:
        new_row = pd.DataFrame({
            "user_id": [user_id],
            "password": [password],
            "target_weight": [target_weight],
            "height": [height],
            "weight": [weight],
            "age": [age],
            "gender": [gender],
            "profile_saved_date": [profile_saved_date or datetime.now().strftime("%Y-%m-%d")],
            "last_update": [datetime.now().strftime("%Y-%m-%d")],
            "consecutive_days": [consecutive_days or 1]
        })
        df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(USER_FILE, index=False)

PROFILE_EXPIRE_DAYS = 30

def is_profile_locked(user_row):
    saved_date = user_row.get('profile_saved_date')
    if pd.isna(saved_date) or not saved_date:
        return False
    try:
        saved_date = datetime.strptime(str(saved_date), "%Y-%m-%d").date()
        return (datetime.now().date() - saved_date).days < PROFILE_EXPIRE_DAYS
    except:
        return False

def reset_basic_info_on_month_start(user_id):
    if datetime.now().day != 1:
        return
    df = get_all_users()
    u_str = str(user_id)
    if u_str not in df['user_id'].astype(str).values:
        return
    idx = df[df['user_id'].astype(str) == u_str].index[0]
    df.at[idx, 'target_weight'] = pd.NA
    df.at[idx, 'last_update'] = datetime.now().strftime("%Y-%m-%d")
    df.to_csv(USER_FILE, index=False)

def calculate_consecutive_days(user_id):
    df = get_all_users()
    u_str = str(user_id)
    if u_str not in df['user_id'].astype(str).values:
        return 1
    
    idx = df[df['user_id'].astype(str) == u_str].index[0]
    last_update_str = df.at[idx, 'last_update']
    current_consecutive = df.at[idx, 'consecutive_days']
    
    if pd.isna(last_update_str) or pd.isna(current_consecutive):
        return 1
    
    try:
        last_update = datetime.strptime(last_update_str, "%Y-%m-%d").date()
        today = datetime.now().date()
        
        if (today - last_update).days == 1:
            # 連続
            return int(current_consecutive) + 1
        elif (today - last_update).days == 0:
            # 同じ日
            return int(current_consecutive)
        else:
            # 連続切れ
            return 1
    except:
        return 1

@st.cache_data
def load_menu():
    try:
        df_m = pd.read_csv(MENU_FILE, header=None).iloc[:, :5]
        df_m.columns = ['id', 'store', 'name', 'genre', 'cal']
        df_m['cal'] = pd.to_numeric(df_m['cal'], errors='coerce').fillna(0)
        df_m['display'] = df_m['store'] + " - " + df_m['name'] + " (" + df_m['cal'].astype(int).astype(str) + "kcal)"
        return df_m
    except:
        return pd.DataFrame()

def show_auth_screen():
    # --- 3. 画面制御ロジック ---
    if 'is_logged_in' not in st.session_state:
        st.session_state['is_logged_in'] = False
    if 'show_register' not in st.session_state:
        st.session_state['show_register'] = False
    if 'selected_dinner' not in st.session_state:
        st.session_state['selected_dinner'] = None
    if 'selected_dinner_cal' not in st.session_state:
        st.session_state['selected_dinner_cal'] = 0

    # A. ログイン・登録画面
    if not st.session_state['is_logged_in']:
        if st.session_state['show_register']:
            # 📝 新規会員登録画面
            st.markdown("<div style='text-align: center;'><h1 style='color: #ff6b6b;'>📝 新規会員登録</h1></div>", unsafe_allow_html=True)
            
            with st.container(border=True):
                st.markdown("<p style='text-align: center; color: #666; font-size: 14px;'>新しくアカウントを作成してサンダーさんと一緒にダイエットを始めましょう！</p>", unsafe_allow_html=True)
                st.markdown("")
                
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    n_id = st.text_input("希望ID", key="reg_id", placeholder="ユーザーID")
                    n_pw = st.text_input("パスワード", type="password", key="reg_pw", placeholder="パスワード")
                    
                    st.markdown("")
                    col_a, col_b = st.columns(2)
                    
                    with col_a:
                        if st.button("📝 登録", use_container_width=True):
                            if n_id and n_pw:
                                save_user(n_id, n_pw)
                                st.success("登録完了！🥢 さあ、始めましょう！")
                                st.session_state['show_register'] = False
                                st.rerun()
                            else:
                                st.error("IDとパスワードを入力してね！")
                    
                    with col_b:
                        if st.button("🔙 戻る", use_container_width=True):
                            st.session_state['show_register'] = False
                            st.rerun()
        else:
            # 🔐 ログイン画面
            st.markdown("<div style='text-align: center;'><h1 style='color: #2196F3;'>🔐 今日からあなたもライエット</h1></div>", unsafe_allow_html=True)
            
            with st.container(border=True):
                st.markdown("<p style='text-align: center; color: #666; font-size: 14px;'>美食家サンダーさんとの美食ダイエットの冒険へようこそ！</p>", unsafe_allow_html=True)
                st.markdown("")
                
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    l_id = st.text_input("ユーザーID", key="login_id", placeholder="IDを入力")
                    l_pw = st.text_input("パスワード", type="password", key="login_pw", placeholder="パスワードを入力")
                    
                    st.markdown("")
                    if st.button("🔓 ログイン", use_container_width=True):
                        df = get_all_users()
                        match = df[(df['user_id'].astype(str) == l_id) & (df['password'].astype(str) == l_pw)]
                        
                        if not match.empty:
                            user_info = match.iloc[0]
                            reset_basic_info_on_month_start(l_id)
                            
                            # 連続ログイン日数を計算
                            consecutive_days = calculate_consecutive_days(l_id)
                            save_user(l_id, user_info['password'], user_info['target_weight'], consecutive_days)
                            
                            st.session_state['height'] = safe_float(user_info.get('height', 160.0), 160.0)
                            st.session_state['weight'] = safe_float(user_info.get('weight', 55.0), 55.0)
                            st.session_state['age'] = safe_int(user_info.get('age', 20), 20)
                            st.session_state['gender'] = user_info.get('gender', "女子")
                            
                            st.session_state['is_logged_in'] = True
                            st.session_state['current_user'] = l_id
                            
                            st.success(f"ログイン成功！おかえりなさい、{l_id}さん 🥢")
                            st.rerun()
                        else: 
                            st.error("IDまたはパスワードが間違っています！")
                    
                    st.markdown("")
                    if st.button("✨ 新規登録はこちら", use_container_width=True):
                        st.session_state['show_register'] = True
                        st.rerun()
import streamlit as st
import extra_streamlit_components as stx
from datetime import datetime, timedelta
import time

cookie_manager = stx.CookieManager()

def main():
    # ログイン状態の確認（スピナー付き）
    if "logged_in" not in st.session_state:
        with st.spinner("ログイン情報を確認中..."):
            time.sleep(0.5) 
            saved_user = cookie_manager.get(cookie="username")
            if saved_user:
                st.session_state.logged_in = True
                st.session_state.username = saved_user
            else:
                st.session_state.logged_in = False

    if not st.session_state.get("logged_in"):
        user_input = st.text_input("ユーザー名を入力")
        if st.button("ログイン"):
            if user_input:
                # --- ここがポイント！ ---
                # 30日後の日時を計算
                expires_date = datetime.now() + timedelta(days=30)
                
                # Cookieに保存（expires_atに日時オブジェクトを渡す）
                cookie_manager.set(
                    "username", 
                    user_input, 
                    expires_at=expires_date  # 30日後に設定
                )
                
                st.session_state.logged_in = True
                st.session_state.username = user_input
                st.rerun()
    else:
        st.write(f"ログイン中: {st.session_state.username}")
        if st.button("ログアウト"):
            cookie_manager.delete("username")
            st.session_state.clear()
            st.rerun()

if __name__ == "__main__":
    main()
