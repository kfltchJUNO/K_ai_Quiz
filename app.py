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
# 2. 기능 구현
# ==========================================
def make_quiz(level, type):
    prompt = f"""
    한국어 교육 전문가로서 외국인 학습자를 위한 퀴즈를 하나 만들어줘.
    
    1. 난이도: 한국어표준교육과정 {level}
    2. 유형: {type}
    3. 결과는 반드시 JSON 형식으로만 줘. (마크다운 없이 순수 텍스트로)
    
    [JSON 형식 예시]
    {{
        "question": "문제 지문",
        "options": ["보기1", "보기2", "보기3", "보기4"],
        "answer": "정답(보기 중 하나와 똑같이)",
        "explanation": "해설"
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except Exception as e:
        # 에러가 나면 콘솔에 내용을 출력해줌 (디버깅용)
        print(f"에러 발생: {e}")
        return None

# ==========================================
# 3. 화면 디자인
# ==========================================

st.title("🇰🇷 한국어 실력 쑥쑥 퀴즈")

# 사이드바 설정
with st.sidebar:
    st.header("퀴즈 설정")
    my_level = st.selectbox("레벨 선택", ["1급", "2급", "3급", "4급", "5급", "6급"])
    my_type = st.radio("문제 유형", ["4지선다", "O/X 퀴즈"])
    
    # 버튼 클릭
    if st.button("새 문제 만들기", type="primary"): # type="primary"는 버튼을 강조색으로 보여줌
        
        # 1. 기존 문제 초기화 (화면 깜빡임 방지 및 리셋)
        st.session_state['quiz'] = None
        st.session_state['solved'] = False
        
        # 2. 로딩 표시 시작
        with st.status("Gemini 선생님이 문제를 출제하고 있어요...", expanded=True) as status:
            st.write("📝 난이도를 분석하는 중...")
            time.sleep(0.5) # 휙 지나가지 않게 잠깐 멈춤
            st.write("🧠 적절한 어휘를 고르는 중...")
            
            # AI 함수 호출
            quiz_data = make_quiz(my_level, my_type)
            
            if quiz_data:
                st.session_state['quiz'] = quiz_data
                status.update(label="문제 생성 완료! 아래에서 풀어보세요.", state="complete", expanded=False)
            else:
                status.update(label="문제 생성 실패", state="error")
                st.error("문제를 받아오지 못했습니다. API 키를 확인하거나 잠시 후 다시 시도해주세요.")

# 문제 표시 영역
if 'quiz' in st.session_state and st.session_state['quiz']:
    data = st.session_state['quiz']
    
    st.divider() # 구분선
    st.markdown(f"#### < {my_level} 수준 문제 >", unsafe_allow_html=True)
    
    # 문제 박스 디자인
    st.info(f"Q. {data['question']}")
    
    with st.form("answer_form"):
        user_answer = st.radio("정답을 고르세요:", data['options'])
        submitted = st.form_submit_button("정답 확인")
        
        if submitted:
            st.session_state['solved'] = True
            if user_answer == data['answer']:
                st.balloons() # 정답이면 풍선 날리기 효과
                st.success("🎉 정답입니다! 참 잘했어요.")
            else:
                st.error(f"아쉽네요. 정답은 '{data['answer']}' 입니다.")
            
            with st.expander("💡 해설 보기 (클릭)", expanded=True):
                st.write(data['explanation'])

# 처음에 아무것도 없을 때 안내 문구
elif 'quiz' not in st.session_state or st.session_state['quiz'] is None:

    st.info("👈 왼쪽에서 '새 문제 만들기' 버튼을 눌러주세요.")
