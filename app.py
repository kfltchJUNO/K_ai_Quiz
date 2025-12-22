import streamlit as st
import google.generativeai as genai
import json
import time

# ==========================================
# 1. 설정 영역
# ==========================================

# 배포된 환경(Secrets)인지 로컬 환경인지 확인하여 키 설정
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    # 로컬에서 테스트할 때만 쓰는 키 (배포할 땐 비워두셔도 됩니다)
    api_key = "여기에_API_KEY_를_넣으세요" 

# 구글 제미나이 설정
genai.configure(api_key=api_key)

try:
    model = genai.GenerativeModel('gemini-flash-latest')
except Exception as e:
    st.error(f"API 키 설정에 문제가 있습니다: {e}")

# ==========================================
# 2. 기능 구현 (AI 프롬프트 엔지니어링)
# ==========================================
def make_quiz(level, category, q_type):
    
    # 유형별로 AI에게 요청할 데이터 포맷을 다르게 지정
    json_format = ""
    if q_type in ["4지선다", "O/X"]:
        json_format = """
        {
            "question": "문제 지문",
            "options": ["보기1", "보기2", "보기3", "보기4"], 
            "answer": "정답(보기와 동일한 텍스트)",
            "explanation": "해설"
        }
        """
    elif q_type == "단답형":
        json_format = """
        {
            "question": "문제 지문 (예: 빈칸 채우기 등)",
            "answer": "정답 단어 (핵심 키워드)",
            "explanation": "해설"
        }
        """
    elif q_type == "연결하기":
        json_format = """
        {
            "question": "다음 단어와 의미를 알맞게 연결하세요.",
            "pairs": [
                {"item": "항목1(단어)", "match": "짝1(뜻)"},
                {"item": "항목2(단어)", "match": "짝2(뜻)"},
                {"item": "항목3(단어)", "match": "짝3(뜻)"}
            ],
            "explanation": "전체 해설"
        }
        """

    prompt = f"""
    당신은 한국어 교육 전문가입니다. 외국인 학습자를 위한 문제를 출제해주세요.
    
    1. 대상 등급: 한국어표준교육과정 {level}
    2. 학습 영역: {category} (문법 또는 어휘 위주)
    3. 문제 유형: {q_type}
    
    [출력 조건]
    반드시 아래 JSON 형식으로만 출력하세요. (마크다운, ```json 태그 포함 금지. 순수 텍스트만)
    
    [JSON 형식]
    {json_format}
    """
    
    try:
        response = model.generate_content(prompt)
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_text)
        return data
    except Exception as e:
        print(f"오류: {e}")
        return None

# ==========================================
# 3. 화면 디자인
# ==========================================

st.set_page_config(page_title="한국어 맞춤형 퀴즈", page_icon="🇰🇷")

st.title("🇰🇷 한국어 맞춤형 학습기")
st.caption("등급, 영역, 유형을 선택하여 나만의 문제를 풀어보세요!")

# --- 사이드바 설정 ---
with st.sidebar:
    st.header("🛠️ 문제 설정")
    
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
        st.session_state['user_answer'] = None # 사용자 답 초기화
        
        # ★ 요청하신 대로 로딩 멘트 변경 ★
        with st.status("문제 생성기가 문제를 만드는 중입니다...", expanded=True) as status:
            st.write(f"📊 난이도: {s_level}")
            st.write(f"📚 영역: {s_category} / {s_type}")
            time.sleep(0.5)
            
            quiz_data = make_quiz(s_level, s_category, s_type)
            
            if quiz_data:
                st.session_state['quiz'] = quiz_data
                st.session_state['q_type'] = s_type # 현재 문제 유형 저장
                status.update(label="출제 완료!", state="complete", expanded=False)
            else:
                status.update(label="생성 실패", state="error")
                st.error("다시 시도해주세요.")

# --- 문제 풀기 화면 ---
if 'quiz' in st.session_state and st.session_state['quiz']:
    q_data = st.session_state['quiz']
    q_type = st.session_state['q_type']
    
    st.divider()
    
    # 등급/영역 배지 표시
    st.markdown(f"#### < {s_level} | {s_category} | {s_type} >")
    
    # 문제 출력
    st.info(f"Q. {q_data['question']}")
    
    # --- 유형별 UI 분기 처리 ---
    with st.form("answer_form"):
        user_input = None
        is_correct = False
        
        # 1. 객관식 / OX
        if q_type in ["4지선다", "O/X"]:
            user_input = st.radio("정답을 선택하세요:", q_data['options'])
        
        # 2. 단답형
        elif q_type == "단답형":
            user_input = st.text_input("정답을 입력하세요 (단어):")
            
        # 3. 연결하기 (매칭 게임)
        elif q_type == "연결하기":
            st.write("왼쪽 단어에 맞는 뜻을 오른쪽에서 골라주세요.")
            
            # 짝 데이터 가져오기
            pairs = q_data['pairs']
            
            # 오른쪽 보기(뜻) 리스트 만들기 (섞기 전 원본)
            correct_matches = [p['match'] for p in pairs]
            
            # 세션 스테이트에 섞인 보기가 없으면 생성 (새로고침 시 유지 위해)
            if 'shuffled_options' not in st.session_state or st.session_state['quiz'] != q_data:
                shuffled = correct_matches.copy()
                random.shuffle(shuffled)
                st.session_state['shuffled_options'] = shuffled
            
            options_display = ["선택하세요"] + st.session_state['shuffled_options']
            
            # 사용자 선택 저장할 딕셔너리
            user_selections = {}
            
            for p in pairs:
                col_a, col_b = st.columns([1, 2])
                with col_a:
                    st.markdown(f"**{p['item']}**") # 왼쪽 단어
                with col_b:
                    # 각 단어마다 selectbox 생성
                    choice = st.selectbox(
                        f"{p['item']}의 뜻", 
                        options_display, 
                        key=f"match_{p['item']}", 
                        label_visibility="collapsed"
                    )
                    user_selections[p['item']] = choice
            
            user_input = user_selections # 전체 선택 결과를 정답 체크용으로 넘김

        # 제출 버튼
        submitted = st.form_submit_button("정답 확인", use_container_width=True)
        
        if submitted:
            st.session_state['solved'] = True
            
            # 정답 채점 로직
            if q_type in ["4지선다", "O/X"]:
                if user_input == q_data['answer']:
                    is_correct = True
                    
            elif q_type == "단답형":
                # 공백 제거 후 비교
                if user_input.strip() == q_data['answer'].strip():
                    is_correct = True
                    
            elif q_type == "연결하기":
                # 모든 짝이 맞는지 확인
                all_match = True
                for p in q_data['pairs']:
                    if user_input[p['item']] != p['match']:
                        all_match = False
                        break
                if all_match:
                    is_correct = True

            # 결과 메시지 출력
            if is_correct:
                st.balloons()
                st.success("🎉 정답입니다! 훌륭해요.")
            else:
                st.error("아쉽네요. 다시 한번 확인해보세요!")
                # 틀렸을 때 정답 공개
                if q_type == "연결하기":
                    st.write("---")
                    st.write("**[정답 연결]**")
                    for p in q_data['pairs']:
                        st.write(f"🔹 {p['item']} ➡ {p['match']}")
                else:
                    st.write(f"👉 정답은 **'{q_data['answer']}'** 입니다.")
            
            # 해설 박스
            with st.expander("💡 상세 해설 보기", expanded=True):
                st.write(q_data['explanation'])

elif 'quiz' not in st.session_state or st.session_state['quiz'] is None:
    st.info("👈 왼쪽 사이드바에서 설정을 마치고 [새 문제 만들기]를 눌러주세요.")
