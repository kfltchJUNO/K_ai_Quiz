import streamlit as st
import google.generativeai as genai
import json
import time
import random

# ==========================================
# 1. 설정 영역
# ==========================================

# 배포 환경(Secrets)과 로컬 환경 모두 작동하도록 설정
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    # 로컬 테스트 시 여기에 키 입력
    api_key = "여기에_API_KEY_를_넣으세요"

genai.configure(api_key=api_key)

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
        category_instruction = "단어의 뜻을 묻지 말고, 문법 요소(조사, 어미, 활용 등)의 정확한 쓰임을 묻는 문제 위주로 출제하세요."
    elif category == "어휘":
        category_instruction = "문맥에 맞는 단어 선택, 유의어, 반의어 등 어휘의 의미를 묻는 문제 위주로 출제하세요."

    # 연결하기 유형일 때 pairs의 개수를 4개 정도로 고정하여 게임성을 높임
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
            "question": "문제 지문",
            "answer": "정답 단어",
            "explanation": "해설"
        }
        """
    elif q_type == "연결하기":
        json_format = """
        {
            "question": "다음 단어와 의미를 알맞게 짝지으세요.",
            "pairs": [
                {"item": "단어1", "match": "뜻1"},
                {"item": "단어2", "match": "뜻2"},
                {"item": "단어3", "match": "뜻3"},
                {"item": "단어4", "match": "뜻4"}
            ],
            "explanation": "전체 해설"
        }
        """

    prompt = f"""
    당신은 한국어 교육 전문가입니다.
    
    [출제 조건]
    1. 대상 등급: 한국어표준교육과정 {level}
    2. 학습 영역: {category} ({category_instruction})
    3. 문제 유형: {q_type}
    
    [출력 조건]
    반드시 아래 JSON 형식으로만 출력하세요. (마크다운 없이 순수 텍스트만)
    
    [JSON 형식]
    {json_format}
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        print(f"오류: {e}")
        return None

# ==========================================
# 3. 화면 디자인
# ==========================================

st.set_page_config(page_title="한국어 맞춤형 퀴즈", page_icon="🇰🇷")

st.title("🇰🇷 한국어 맞춤형 학습기")
st.caption("등급과 유형을 선택하고 AI와 함께 한국어를 연습해보세요!")

# --- 사이드바 ---
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
        # 상태 초기화
        st.session_state['quiz'] = None
        st.session_state['solved'] = False
        st.session_state['user_answer'] = None
        
        # 연결하기 게임용 상태 초기화
        st.session_state['connected_pairs'] = {} # 사용자가 연결한 짝 {left: right}
        st.session_state['selected_left'] = None # 현재 선택된 왼쪽 항목
        
        with st.status("문제 생성기가 문제를 만드는 중입니다...", expanded=True) as status:
            time.sleep(0.5)
            quiz_data = make_quiz(s_level, s_category, s_type)
            
            if quiz_data:
                st.session_state['quiz'] = quiz_data
                st.session_state['q_type'] = s_type
                
                # 연결하기 문제라면 보기를 미리 섞어서 저장
                if s_type == "연결하기" and 'pairs' in quiz_data:
                    items = [p['item'] for p in quiz_data['pairs']]
                    matches = [p['match'] for p in quiz_data['pairs']]
                    random.shuffle(matches) # 오른쪽 뜻만 섞음
                    st.session_state['left_items'] = items
                    st.session_state['right_items'] = matches
                
                status.update(label="출제 완료!", state="complete", expanded=False)
            else:
                status.update(label="생성 실패", state="error")
                st.error("문제를 생성하지 못했습니다. 다시 시도해주세요.")

# --- 문제 풀기 영역 ---
if 'quiz' in st.session_state and st.session_state['quiz']:
    q_data = st.session_state['quiz']
    q_type = st.session_state['q_type']
    
    st.divider()
    st.markdown(f"#### < {s_level} | {s_category} | {s_type} >")
    st.info(f"Q. {q_data['question']}")

    # ===============================================
    # [유형 A] 연결하기 (인터랙티브 UI)
    # ===============================================
    if q_type == "연결하기":
        
        st.write("👈 **왼쪽 단어**를 먼저 누르고, 👉 **오른쪽 뜻**을 눌러 짝을 지어주세요!")
        
        # 1. 연결된 목록 보여주기 (결과 화면)
        if st.session_state['connected_pairs']:
            st.markdown("##### 🔗 연결된 짝 (클릭하면 취소)")
            # 연결된 짝들을 버튼으로 보여줌 (누르면 삭제)
            cols = st.columns(2)
            for idx, (l_item, r_item) in enumerate(st.session_state['connected_pairs'].items()):
                if cols[idx % 2].button(f"❌ {l_item} ↔ {r_item}", key=f"del_{l_item}"):
                    del st.session_state['connected_pairs'][l_item]
                    st.rerun() # 화면 갱신
            st.divider()

        # 2. 선택 영역 (2단 컬럼)
        c1, c2 = st.columns(2)
        
        # 왼쪽 기둥: 아직 짝을 못 찾은 단어들
        with c1:
            st.markdown("**[단어]**")
            for item in st.session_state['left_items']:
                # 이미 연결된 건 안 보여줌
                if item not in st.session_state['connected_pairs']:
                    # 내가 방금 클릭한 건지 확인 (색깔 강조)
                    btn_type = "primary" if st.session_state['selected_left'] == item else "secondary"
                    
                    if st.button(item, key=f"left_{item}", type=btn_type, use_container_width=True):
                        st.session_state['selected_left'] = item
                        st.rerun()

        # 오른쪽 기둥: 아직 짝을 못 찾은 뜻들
        with c2:
            st.markdown("**[의미]**")
            # 이미 누군가와 연결된(value에 있는) 뜻은 안 보여줌
            connected_values = st.session_state['connected_pairs'].values()
            
            for match in st.session_state['right_items']:
                if match not in connected_values:
                    if st.button(match, key=f"right_{match}", use_container_width=True):
                        # 왼쪽이 선택된 상태라면 짝짓기 성공!
                        if st.session_state['selected_left']:
                            left = st.session_state['selected_left']
                            st.session_state['connected_pairs'][left] = match
                            st.session_state['selected_left'] = None # 선택 해제
                            st.rerun()
                        else:
                            st.toast("👈 왼쪽 단어를 먼저 선택해주세요!", icon="⚠️")

        st.write("") # 여백
        
        # 3. 제출 버튼 (연결하기용 별도 버튼)
        if st.button("정답 확인하기", type="primary", use_container_width=True):
            st.session_state['solved'] = True
            
            # 채점
            correct_pairs = {p['item']: p['match'] for p in q_data['pairs']}
            user_pairs = st.session_state['connected_pairs']
            
            # 개수 확인 & 내용 확인
            if len(user_pairs) == len(correct_pairs) and user_pairs == correct_pairs:
                st.balloons()
                st.success("🎉 완벽해요! 모든 짝을 맞췄습니다.")
            else:
                st.error("틀린 부분이 있거나 짝을 다 짓지 않았어요.")
                
                # 정답 공개
                with st.expander("정답 보기"):
                    for item, match in correct_pairs.items():
                        st.write(f"🔹 **{item}** ➡ {match}")
                
                # 해설
                st.info(f"💡 해설: {q_data['explanation']}")

    # ===============================================
    # [유형 B] 나머지 문제 (4지선다, OX, 단답형)
    # ===============================================
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

elif 'quiz' not in st.session_state or st.session_state['quiz'] is None:
    st.info("👈 왼쪽에서 [새 문제 만들기]를 눌러 시작하세요.")

