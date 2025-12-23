import streamlit as st
import google.generativeai as genai
import json
import time
import random

# ==========================================
# 1. 초기 설정 & 공유 메모리
# ==========================================
st.set_page_config(page_title="한큐 - 한국어 맞춤형 퀴즈", page_icon="🇰🇷", layout="centered")

@st.cache_resource
class SharedState:
    def __init__(self):
        self.quiz_active = True 

shared_state = SharedState()

# API 키 설정
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    st.error("🚨 API 키를 찾을 수 없습니다!")
    st.info("Streamlit Secrets에 GEMINI_API_KEY를 설정해주세요.")
    st.stop()

# 관리자 설정
if "ADMIN_ID" in st.secrets:
    ADMIN_ID = st.secrets["ADMIN_ID"]
    ADMIN_PW = st.secrets["ADMIN_PW"]
else:
    ADMIN_ID = "admin"
    ADMIN_PW = "1234"

genai.configure(api_key=api_key)

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

try:
    model = genai.GenerativeModel('gemini-flash-latest')
except Exception as e:
    st.error(f"모델 설정 오류: {e}")

if 'is_admin' not in st.session_state:
    st.session_state['is_admin'] = False

# ==========================================
# 2. 모달(Dialog) 및 관리자 기능
# ==========================================
@st.dialog("관리자 설정")
def admin_dialog():
    if not st.session_state['is_admin']:
        st.write("관리자 계정으로 로그인하세요.")
        with st.form("login_form"):
            input_id = st.text_input("아이디")
            input_pw = st.text_input("비밀번호", type="password")
            btn_login = st.form_submit_button("로그인", use_container_width=True)
            
            if btn_login:
                if input_id == ADMIN_ID and (input_pw == ADMIN_PW):
                    st.session_state['is_admin'] = True
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 틀렸습니다.")
    else:
        st.success(f"✅ {ADMIN_ID}님 환영합니다.")
        st.write("---")
        st.subheader("전체 기능 제어")
        
        current_status = shared_state.quiz_active
        is_active = st.toggle("학생들이 퀴즈를 풀 수 있게 하기", value=current_status)
        
        if is_active != current_status:
            shared_state.quiz_active = is_active
            st.rerun()
            
        st.caption("※ 이 스위치를 끄면 접속해 있는 모든 학생의 기능이 정지됩니다.")
            
        st.write("---")
        if st.button("로그아웃", type="primary", use_container_width=True):
            st.session_state['is_admin'] = False
            st.rerun()

# ==========================================
# 3. AI 퀴즈 생성 함수
# ==========================================
def make_quiz(level, category, q_type):
    
    # [수정] 1-2급 난이도 조절 프롬프트 강화
    tone_instruction = ""
    if level in ["1급", "2급"]:
        tone_instruction = """
        [⚠️ 매우 중요: 어휘 난이도 제한]
        1. 문제 지문(question)에 '의미하다', '해당하다', '적절하다' 같은 어려운 한자어 동사를 절대 쓰지 마세요.
        2. 반드시 '뜻', '맞는 것', '고르세요' 같은 기초 어휘만 사용하세요.
        3. 문장은 '~(으)세요'나 '~(이)에요' 체로 끝내고, 복잡한 문법을 피하세요.
        """
    
    category_instruction = ""
    if category == "문법":
        category_instruction = "단어의 뜻을 묻지 말고, 문법 요소(조사, 어미, 표현 등)와 그 쓰임/기능을 연결하거나 올바른 예문을 찾는 문제 위주로 출제하세요."
    elif category == "어휘":
        category_instruction = "문맥에 맞는 단어 선택, 유의어, 반의어 등 어휘의 의미를 묻는 문제 위주로 출제하세요."

    # JSON 구조 설정
    json_structure = ""
    if q_type == "4지선다":
        json_structure = """{"question": "지문", "options": ["보기1", "보기2", "보기3", "보기4"], "answer": "정답", "explanation": "해설"}"""
    elif q_type == "O/X":
        json_structure = """{"question": "맞으면 O, 틀리면 X를 선택하세요.", "options": ["O", "X"], "answer": "O 또는 X", "explanation": "해설"}"""
    elif q_type == "연결하기":
        json_structure = """{"question": "지문", "pairs": [{"item": "항목(단어/문법표현)", "match": "짝(뜻/쓰임)"}, ...], "explanation": "해설"}"""

    prompt = f"""
    한국어 교육 전문가로서 다음 조건에 맞는 퀴즈를 JSON 형식으로 출력하세요.
    1. 등급: 한국어표준교육과정 {level}
    2. 영역: {category} ({category_instruction})
    3. 유형: {q_type}
    
    {tone_instruction}

    응답은 반드시 아래 JSON 스키마를 따르세요:
    {json_structure}
    """
    try:
        response = model.generate_content(
            prompt,
            safety_settings=safety_settings,
            generation_config={"response_mime_type": "application/json"} 
        )
        text = response.text
        # JSON 전처리
        text = text.replace("```json", "").replace("```JSON", "").replace("```", "").strip()
        
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            try:
                decoder = json.JSONDecoder()
                data, _ = decoder.raw_decode(text)
            except:
                start_idx = text.find("{")
                end_idx = text.rfind("}")
                if start_idx != -1 and end_idx != -1:
                    text = text[start_idx : end_idx + 1]
                    data = json.loads(text)
                else:
                    return None

        if isinstance(data, list):
            data = data[0] if len(data) > 0 else None
        
        if isinstance(data, dict):
            if q_type == "O/X":
                data['options'] = ["O", "X"]
            return data
        else:
            return None
            
    except Exception as e:
        st.error(f"오류 발생: {e}")
        return None

# ==========================================
# 4. 메인 화면 구성
# ==========================================
col_title, col_lock = st.columns([9, 1])
with col_title:
    st.title("🇰🇷 한큐 (Han-Q)")
    st.markdown("### 한국어 학습용 AI 무제한 문제 생성기")
with col_lock:
    if st.button("🔒", help="관리자 설정"):
        admin_dialog()

st.caption("등급과 유형을 선택하고 AI와 함께 한국어를 연습해보세요!")

if not shared_state.quiz_active and not st.session_state['is_admin']:
    st.divider()
    st.error("⛔ 현재 퀴즈 생성 기능이 비활성화되어 있습니다.")
    st.info("선생님이 기능을 켜주실 때까지 잠시만 기다려주세요.")
    if st.button("기능이 켜졌는지 확인하기 (새로고침)"):
        st.rerun()

else:
    if not shared_state.quiz_active and st.session_state['is_admin']:
        st.warning("⚠️ 현재 학생들에게는 기능이 꺼져 있습니다. (관리자 권한으로 실행 중)")

    with st.sidebar:
        st.header("🛠️ 문제 설정")
        if st.session_state['is_admin']:
            st.success("🔒 관리자 모드")
        
        col1, col2 = st.columns(2)
        with col1:
            s_level = st.selectbox("등급", ["1급", "2급", "3급", "4급", "5급", "6급"])
        with col2:
            s_category = st.selectbox("영역", ["어휘", "문법"])
            
        if s_level in ["1급", "2급"]:
            available_types = ["4지선다", "O/X"]
        else:
            available_types = ["4지선다", "O/X", "연결하기"]
            
        s_type = st.radio("문제 유형", available_types)
        
        st.divider()
        
        if st.button("새 문제 만들기", type="primary", use_container_width=True):
            st.session_state['quiz'] = None
            st.session_state['solved'] = False
            st.session_state['user_answer'] = None
            st.session_state['connected_pairs'] = {}
            st.session_state['selected_left'] = None 
            
            with st.status("문제 생성기가 문제를 만드는 중입니다...", expanded=True) as status:
                time.sleep(0.5)
                quiz_data = make_quiz(s_level, s_category, s_type)
                
                if quiz_data and 'question' in quiz_data:
                    st.session_state['quiz'] = quiz_data
                    st.session_state['q_type'] = s_type
                    
                    if s_type == "연결하기" and 'pairs' in quiz_data:
                        items = [p['item'] for p in quiz_data['pairs']]
                        matches = [p['match'] for p in quiz_data['pairs']]
                        random.shuffle(matches)
                        st.session_state['left_items'] = items
                        st.session_state['right_items'] = matches
                    
                    status.update(label="출제 완료!", state="complete", expanded=False)
                else:
                    status.update(label="생성 실패", state="error")
                    if not quiz_data:
                         st.error("문제를 받아오지 못했습니다. 다시 시도해주세요.")

        # ==========================================
        # [수정 완료] 후원 및 광고
        # 링크에 특수문자([])를 완전히 제거했습니다.
        # ==========================================
        st.divider()
        st.write("☕ **개발자 응원하기**")
        
        # 1. Buy Me a Coffee (HTML 방식, target="_blank"로 새창 열기 강제)
        st.markdown(
            """
            <a href="[https://buymeacoffee.com/ot.helper](https://buymeacoffee.com/ot.helper)" target="_blank" style="text-decoration:none;">
                <div style="background-color:#FFDD00; color:black; padding:10px 20px; text-align:center; border-radius:10px; font-weight:bold; width:100%; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); cursor:pointer;">
                    ☕ 커피 한 잔 사주기
                </div>
            </a>
            """,
            unsafe_allow_html=True
        )
        
        # 2. 쿠팡 파트너스 (HTML 방식)
        # 중요: href 안에 절대 [ ] 나 ( ) 를 넣지 마세요.
        st.markdown(
            """
            <a href="[https://link.coupang.com/a/dhejus](https://link.coupang.com/a/dhejus)" target="_blank" style="text-decoration:none;">
                <div style="background-color:#E33A3D; color:white; padding:10px 20px; text-align:center; border-radius:10px; font-weight:bold; width:100%; box-shadow: 0 2px 4px rgba(0,0,0,0.1); cursor:pointer;">
                    🚀 한국어 책 구경하기
                </div>
            </a>
            <div style="font-size: 10px; color: #888; text-align: center; margin-top: 5px;">
                "이 포스팅은 쿠팡 파트너스 활동의 일환으로,<br>이에 따른 일정액의 수수료를 제공받습니다."
            </div>
            """,
            unsafe_allow_html=True
        )

    # 문제 화면 표시
    if 'quiz' in st.session_state and st.session_state['quiz']:
        q_data = st.session_state['quiz']
        q_type = st.session_state['q_type']
        
        if isinstance(q_data, dict) and 'question' in q_data:
            st.divider()
            st.markdown(f"#### < {s_level} | {s_category} | {s_type} >")
            st.info(f"Q. {q_data['question']}")

            if q_type == "연결하기":
                if s_category == "어휘":
                    label_left, label_right = "단어", "뜻"
                else:
                    label_left, label_right = "문법 표현", "설명"

                st.write(f"👈 **왼쪽 [{label_left}]**을(를) 먼저 누르고, 👉 **오른쪽 [{label_right}]**을(를) 눌러 짝을 지어주세요!")
                
                if st.session_state['connected_pairs']:
                    st.markdown("##### 🔗 연결된 짝")
                    cols = st.columns(2)
                    for idx, (l_item, r_item) in enumerate(st.session_state['connected_pairs'].items()):
                        if cols[idx % 2].button(f"❌ {l_item} ↔ {r_item}", key=f"del_{l_item}"):
                            del st.session_state['connected_pairs'][l_item]
                            st.rerun()
                    st.divider()

                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**[{label_left}]**")
                    for item in st.session_state['left_items']:
                        if item not in st.session_state['connected_pairs']:
                            btn_type = "primary" if st.session_state['selected_left'] == item else "secondary"
                            if st.button(item, key=f"left_{item}", type=btn_type, use_container_width=True):
                                st.session_state['selected_left'] = item
                                st.rerun()
                with c2:
                    st.markdown(f"**[{label_right}]**")
                    connected_values = st.session_state['connected_pairs'].values()
                    for match in st.session_state['right_items']:
                        if match not in connected_values:
                            if st.button(match, key=f"right_{match}", use_container_width=True):
                                if st.session_state['selected_left']:
                                    left = st.session_state['selected_left']
                                    st.session_state['connected_pairs'][left] = match
                                    st.session_state['selected_left'] = None
                                    st.rerun()
                                else:
                                    st.toast(f"👈 왼쪽 {label_left}을(를) 먼저 선택해주세요!", icon="⚠️")

                st.write("")
                if st.button("정답 확인하기", type="primary", use_container_width=True):
                    st.session_state['solved'] = True
                    correct_pairs = {p['item']: p['match'] for p in q_data.get('pairs', [])}
                    user_pairs = st.session_state['connected_pairs']
                    
                    if len(user_pairs) == len(correct_pairs) and user_pairs == correct_pairs:
                        st.balloons()
                        st.success("🎉 완벽해요!")
                    else:
                        st.error("틀린 부분이 있거나 짝을 다 짓지 않았어요.")
                        with st.expander("정답 보기"):
                            for item, match in correct_pairs.items():
                                st.write(f"🔹 **{item}** ➡ {match}")
                        
                        if s_level not in ["1급", "2급"]:
                            st.info(f"💡 해설: {q_data.get('explanation', '')}")

            else:
                with st.form("quiz_form"):
                    user_input = None
                    options = q_data.get('options', [])
                    
                    if q_type in ["4지선다", "O/X"]:
                        user_input = st.radio("정답을 선택하세요:", options)
                    
                    submitted = st.form_submit_button("정답 확인", use_container_width=True)
                    
                    if submitted:
                        st.session_state['solved'] = True
                        is_correct = False
                        answer = q_data.get('answer', '')
                        
                        if user_input == answer:
                            is_correct = True
                        
                        if is_correct:
                            st.balloons()
                            st.success("🎉 정답입니다!")
                        else:
                            st.error(f"아쉽네요. 정답은 '{answer}' 입니다.")
                        
                        if s_level not in ["1급", "2급"]:
                            st.info(f"💡 해설: {q_data.get('explanation', '')}")
        else:
            st.error("문제를 불러오는 중 오류가 발생했습니다. '새 문제 만들기'를 다시 눌러주세요.")

    elif 'quiz' not in st.session_state or st.session_state['quiz'] is None:
        st.info("👈 왼쪽에서 [새 문제 만들기]를 눌러 시작하세요.")
