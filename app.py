import streamlit as st
import google.generativeai as genai
import json
import time
import random

# ==========================================
# 1. 설정 영역 (비밀번호 & API 키 관리)
# ==========================================

# 1) API 키 설정
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = "여기에_API_KEY_를_넣으세요" # 로컬 테스트용

# 2) 관리자 ID/PW 설정 (없으면 기본값 사용 - 보안 주의!)
if "ADMIN_ID" in st.secrets:
    ADMIN_ID = st.secrets["ADMIN_ID"]
    ADMIN_PW = st.secrets["ADMIN_PW"]

genai.configure(api_key=api_key)

# 안전 설정
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

try:
    model = genai.GenerativeModel('gemini-flash-latest')
except Exception as e:
    st.error(f"API 키 설정 오류: {e}")

# ==========================================
# 2. 기능 구현 (AI)
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
        return json.loads(response.text)
    except Exception as e:
        return None

# ==========================================
# 3. 화면 디자인
# ==========================================

st.set_page_config(page_title="한국어 맞춤형 퀴즈", page_icon="🇰🇷")

# 세션 상태 초기화 (관리자 로그인 여부, 퀴즈 활성화 여부)
if 'is_admin' not in st.session_state:
    st.session_state['is_admin'] = False
if 'quiz_active' not in st.session_state:
    st.session_state['quiz_active'] = True # 기본값: 퀴즈 켜짐

st.title("🇰🇷 한국어 맞춤형 학습기")

# --- 사이드바 ---
with st.sidebar:
    # 1. 관리자 패널
    with st.expander("🔒 관리자 로그인", expanded=not st.session_state['is_admin']):
        if not st.session_state['is_admin']:
            input_id = st.text_input("아이디")
            input_pw = st.text_input("비밀번호", type="password")
            
            if st.button("로그인"):
                # 비밀번호 체크: qlalf1 또는 비밀1 (한글 타자 허용)
                if input_id == ADMIN_ID and (input_pw == ADMIN_PW or input_pw == "비밀1"):
                    st.session_state['is_admin'] = True
                    st.success("로그인 성공!")
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 틀렸습니다.")
        else:
            st.success(f"관리자({ADMIN_ID})님 환영합니다.")
            
            # 퀴즈 기능 ON/OFF 토글
            is_active = st.checkbox("퀴즈 생성 기능 켜기", value=st.session_state['quiz_active'])
            st.session_state['quiz_active'] = is_active
            
            if st.button("로그아웃"):
                st.session_state['is_admin'] = False
                st.rerun()
    
    st.divider()
    
    # 2. 퀴즈 설정 (사용자용)
    st.header("🛠️ 문제 설정")
    
    col1, col2 = st.columns(2)
    with col1:
        s_level = st.selectbox("등급", ["1급", "2급", "3급", "4급", "5급", "6급"])
    with col2:
        s_category = st.selectbox("영역", ["어휘", "문법"])
        
    s_type = st.radio("문제 유형", ["4지선다", "O/X", "단답형", "연결하기"])
    
    st.divider()
    
    # [핵심] 관리자가 기능을 껐는지 확인
    if st.session_state['quiz_active']:
        if st.button("새 문제 만들기", type="primary", use_container_width=True):
            st.session_state['quiz'] = None
            st.session_state['solved'] = False
            st.session_state['user_answer'] = None
            st.session_state['connected_pairs'] = {}
            st.session_state['selected_left'] = None 
            
            with st.status("문제 생성기가 문제를 만드는 중입니다...", expanded=True) as status:
                time.sleep(0.5)
                quiz_data = make_quiz(s_level, s_category, s_type)
                
                if quiz_data:
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
                    st.error("오류가 발생했습니다. 다시 시도해주세요.")
    else:
        st.warning("⛔ 현재 선생님이 퀴즈 생성 기능을 잠시 꺼두셨습니다.")

# --- 문제 풀기 영역 ---
# 퀴즈가 활성화되어 있고 데이터가 있을 때만 표시
if st.session_state['quiz_active'] and 'quiz' in st.session_state and st.session_state['quiz']:
    q_data = st.session_state['quiz']
    q_type = st.session_state['q_type']
    
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
            correct_pairs = {p['item']: p['match'] for p in q_data['pairs']}
            user_pairs = st.session_state['connected_pairs']
            
            if len(user_pairs) == len(correct_pairs) and user_pairs == correct_pairs:
                st.balloons()
                st.success("🎉 완벽해요! 모든 짝을 맞췄습니다.")
            else:
                st.error("틀린 부분이 있거나 짝을 다 짓지 않았어요.")
                with st.expander("정답 보기"):
                    for item, match in correct_pairs.items():
                        st.write(f"🔹 **{item}** ➡ {match}")
                st.info(f"💡 해설: {q_data['explanation']}")

    # [유형 B] 나머지 문제
    else:
        with st.form("quiz_form"):
            user_input = None
            if q_type in ["4지선다", "O/X"]:
                user_input = st.radio("정답을 선택하세요:", q_data['options'])
            elif q_type == "단답형":
                user_input = st.text_input("정답을 입력하세요:")
            
            submitted = st.form_submit_button("정답 확인", use_container_width=True)
            
            if submitted:
                st.session_state['solved'] = True
                is_correct = False
                if q_type == "단답형":
                    if str(user_input).strip() == str(q_data['answer']).strip():
                        is_correct = True
                else:
                    if user_input == q_data['answer']:
                        is_correct = True
                
                if is_correct:
                    st.balloons()
                    st.success("🎉 정답입니다!")
                else:
                    st.error(f"아쉽네요. 정답은 '{q_data['answer']}' 입니다.")
                st.info(f"💡 해설: {q_data['explanation']}")

elif not st.session_state['quiz_active']:
    st.info("👋 지금은 퀴즈 시간이 아닙니다. 선생님이 기능을 켜주실 때까지 기다려주세요.")
elif 'quiz' not in st.session_state or st.session_state['quiz'] is None:
    st.info("👈 왼쪽에서 [새 문제 만들기]를 눌러 시작하세요.")
