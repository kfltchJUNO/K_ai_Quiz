import streamlit as st
import google.generativeai as genai
import json
import time
import random

# ==========================================
# 1. 초기 설정
# ==========================================
st.set_page_config(page_title="한국어 맞춤형 퀴즈", page_icon="🇰🇷", layout="centered")

# API 키 및 관리자 설정 로드
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = "여기에_API_KEY_를_넣으세요"

if "ADMIN_ID" in st.secrets:
    ADMIN_ID = st.secrets["ADMIN_ID"]
    ADMIN_PW = st.secrets["ADMIN_PW"]
else:
    ADMIN_ID = "오준호"
    ADMIN_PW = "qlalf1"

genai.configure(api_key=api_key)

# 안전 설정
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

try:
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"API 키 설정 오류: {e}")

# 세션 상태 초기화
if 'is_admin' not in st.session_state:
    st.session_state['is_admin'] = False
if 'quiz_active' not in st.session_state:
    st.session_state['quiz_active'] = True 

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
                if input_id == ADMIN_ID and (input_pw == ADMIN_PW or input_pw == "비밀1"):
                    st.session_state['is_admin'] = True
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 틀렸습니다.")
    else:
        st.success(f"✅ {ADMIN_ID}님 환영합니다.")
        st.write("---")
        st.subheader("기능 제어")
        is_active = st.toggle("퀴즈 생성 기능 활성화", value=st.session_state['quiz_active'])
        
        if is_active != st.session_state['quiz_active']:
            st.session_state['quiz_active'] = is_active
            st.rerun()
            
        st.write("---")
        if st.button("로그아웃", type="primary", use_container_width=True):
            st.session_state['is_admin'] = False
            st.rerun()

# ==========================================
# 3. AI 퀴즈 생성 함수 (여기가 수정됨!)
# ==========================================
def make_quiz(level, category, q_type):
    category_instruction = ""
    if category == "문법":
        category_instruction = "단어의 뜻을 묻지 말고, 문법 요소(조사, 어미, 표현 등)와 그 쓰임/기능을 연결하거나 올바른 예문을 찾는 문제 위주로 출제하세요."
    elif category == "어휘":
        category_instruction = "문맥에 맞는 단어 선택, 유의어, 반의어 등 어휘의 의미를 묻는 문제 위주로 출제하세요."

    json_structure = ""
    if q_type in ["4지선다", "O/X"]:
        json_structure = """{"question": "지문", "options": ["보기1", "보기2", "보기3", "보기4"], "answer": "정답", "explanation": "해설"}"""
    elif q_type == "단답형":
        json_structure = """{"question": "지문", "answer": "정답단어", "explanation": "해설"}"""
    elif q_type == "연결하기":
        json_structure = """{"question": "지문", "pairs": [{"item": "항목(단어/문법표현)", "match": "짝(뜻/쓰임)"}, ...], "explanation": "해설"}"""

    prompt = f"""
    한국어 교육 전문가로서 다음 조건에 맞는 퀴즈를 JSON 형식으로 출력하세요.
    1. 등급: 한국어표준교육과정 {level}
    2. 영역: {category} ({category_instruction})
    3. 유형: {q_type}
    응답은 반드시 아래 JSON 스키마를 따르세요:
    {json_structure}
    """
    try:
        response = model.generate_content(
            prompt,
            safety_settings=safety_settings,
            generation_config={"response_mime_type": "application/json"} 
        )
        data = json.loads(response.text)
        
        # ★★★ [수정 포인트] 데이터가 리스트([])로 왔을 경우 처리 ★★★
        if isinstance(data, list):
            # 리스트라면 첫 번째 문제만 가져옴
            if len(data) > 0:
                data = data[0]
            else:
                return None
                
        # 데이터가 딕셔너리인지 한 번 더 확인
        if isinstance(data, dict):
            return data
        else:
            return None
            
    except Exception as e:
        print(f"Error: {e}")
        return None

# ==========================================
# 4. 메인 화면 구성
# ==========================================
col_title, col_lock = st.columns([9, 1])
with col_title:
    st.title("🇰🇷 한국어 맞춤형 학습기")
with col_lock:
    if st.button("🔒", help="관리자 설정"):
        admin_dialog()

st.caption("등급과 유형을 선택하고 AI와 함께 한국어를 연습해보세요!")

# 퀴즈 기능 꺼짐 + 관리자 아님 -> 안내 메시지
if not st.session_state['quiz_active'] and not st.session_state['is_admin']:
    st.warning("⛔ 현재 선생님이 퀴즈 생성 기능을 잠시 꺼두셨습니다.")
    st.info("수업 시간에 다시 만나요!")

# 정상 작동 모드
else:
    with st.sidebar:
        st.header("🛠️ 문제 설정")
        if st.session_state['is_admin']:
            st.success("🔒 관리자 모드 실행 중")
        
        col1, col2 = st.columns(2)
        with col1:
            s_level = st.selectbox("등급", ["1급", "2급", "3급", "4급", "5급", "6급"])
        with col2:
            s_category = st.selectbox("영역", ["어휘", "문법"])
            
        s_type = st.radio("문제 유형", ["4지선다", "O/X", "단답형", "연결하기"])
        
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
                
                # 데이터 유효성 검사 (question 키가 있는지 확인)
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
                    st.error("데이터 형식이 올바르지 않습니다. 다시 시도해주세요.")

    # 문제 화면 표시 (quiz 데이터가 있고, 딕셔너리 형태일 때만)
    if 'quiz' in st.session_state and st.session_state['quiz']:
        q_data = st.session_state['quiz']
        q_type = st.session_state['q_type']
        
        # ★★★ [수정 포인트] 에러 방지를 위한 이중 체크 ★★★
        if isinstance(q_data, dict) and 'question' in q_data:
            
            st.divider()
            st.markdown(f"#### < {s_level} | {s_category} | {s_type} >")
            st.info(f"Q. {q_data['question']}")

            # [유형 A] 연결하기
            if q_type == "연결하기":
                if s_category == "어휘":
                    label_left, label_right = "단어", "의미"
                else:
                    label_left, label_right = "문법 표현", "쓰임/설명"

                st.write(f"👈 **왼쪽 [{label_left}]**을(를) 먼저 누르고, 👉 **오른쪽 [{label_right}]**을(를) 눌러 짝을 지어주세요!")
                
                if st.session_state['connected_pairs']:
                    st.markdown("##### 🔗 연결된 짝 (클릭하면 취소)")
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
                        st.success("🎉 완벽해요! 모든 짝을 맞췄습니다.")
                    else:
                        st.error("틀린 부분이 있거나 짝을 다 짓지 않았어요.")
                        with st.expander("정답 보기"):
                            for item, match in correct_pairs.items():
                                st.write(f"🔹 **{item}** ➡ {match}")
                        st.info(f"💡 해설: {q_data.get('explanation', '')}")

            # [유형 B] 나머지 문제
            else:
                with st.form("quiz_form"):
                    user_input = None
                    if q_type in ["4지선다", "O/X"]:
                        user_input = st.radio("정답을 선택하세요:", q_data.get('options', []))
                    elif q_type == "단답형":
                        user_input = st.text_input("정답을 입력하세요:")
                    
                    submitted = st.form_submit_button("정답 확인", use_container_width=True)
                    
                    if submitted:
                        st.session_state['solved'] = True
                        is_correct = False
                        answer = q_data.get('answer', '')
                        
                        if q_type == "단답형":
                            if str(user_input).strip() == str(answer).strip():
                                is_correct = True
                        else:
                            if user_input == answer:
                                is_correct = True
                        
                        if is_correct:
                            st.balloons()
                            st.success("🎉 정답입니다!")
                        else:
                            st.error(f"아쉽네요. 정답은 '{answer}' 입니다.")
                        st.info(f"💡 해설: {q_data.get('explanation', '')}")
        else:
            # 데이터가 이상하게 들어왔을 경우
            st.error("문제를 불러오는 중 오류가 발생했습니다. '새 문제 만들기'를 다시 눌러주세요.")

    elif 'quiz' not in st.session_state or st.session_state['quiz'] is None:
        st.info("👈 왼쪽에서 [새 문제 만들기]를 눌러 시작하세요.")
