import streamlit as st
import pandas as pd
import json
import google.generativeai as genai
import time

# ==========================================
# 🔑 구글 인공지능 API 설정 (발급받으신 최신 키 입력)
# ==========================================
genai.configure(api_key="AQ.Ab8RN6KnQiUT3P2OLXoVHtYR7TD--dJCjmFAliUIRARhyq9f3A")
model = genai.GenerativeModel('gemini-1.5-flash')

st.set_page_config(page_title="🌟 찐! AI 자동 피드백 마법사", layout="wide")

# --- 앱 내장 메모리 (반 관리 템플릿) ---
if 'class_templates' not in st.session_state:
    st.session_state.class_templates = {
        "공통수학1 기본 월금반": "박선규 / 꼼꼼하지만 속도가 약간 느림 / 시간 분배 연습 강조\n박선우 / 심화 문제에 지레 겁을 먹음 / 칭찬과 격려 위주의 상담 선호\n김은성 / 성격이 급해 연산 실수가 잦음 / 오답노트 철저히",
        "중3-1 심화 화목반": "김학생 / 선행이 잘 되어 있음 / 고등 과정 연계 짚어주기\n이학생 / 계산 실수가 잦음 / 반복 훈련 원하심"
    }

# 사이드바: 반 템플릿 관리
with st.sidebar:
    st.header("⚙️ 우리 학원 반 관리")
    st.write("이곳에서 반을 추가, 수정, 삭제하세요.")
    new_class_name = st.text_input("반 이름 입력")
    new_class_traits = st.text_area("학생 성향 (이름 / 성향 / 어머님니즈)", height=150)
    if st.button("💾 반 저장하기"):
        if new_class_name.strip():
            st.session_state.class_templates[new_class_name] = new_class_traits
            st.success(f"'{new_class_name}' 저장 완료!")
            
    st.markdown("---")
    if st.session_state.class_templates:
        class_to_delete = st.selectbox("삭제할 반 선택", list(st.session_state.class_templates.keys()))
        if st.button("❌ 선택한 반 삭제"):
            if class_to_delete in st.session_state.class_templates:
                del st.session_state.class_templates[class_to_delete]
                st.rerun()

# --- 메인 화면 ---
st.title("🌟 AI 맞춤형 학원 피드백 마법사")

st.markdown("### 1단계: 학원 프로그램 JSON 데이터 붙여넣기")
json_input = st.text_area("JSON 데이터 입력칸", height=150)

st.markdown("### 2단계: 학생별 채점 결과 엑셀 파일 업로드")
uploaded_file = st.file_uploader("학생 답안 엑셀 파일 선택", type=["xlsx", "xls"])

sheet_name = None
if uploaded_file is not None:
    xls = pd.ExcelFile(uploaded_file)
    sheet_names = [sheet for sheet in xls.sheet_names if "기본값" not in sheet]
    if sheet_names:
        sheet_name = st.selectbox("📝 피드백을 생성할 회차(시트)를 선택하세요", sheet_names)

st.markdown("### 3단계: 피드백을 만들 반 선택")
options = ["직접 입력"] + list(st.session_state.class_templates.keys())
selected_class = st.selectbox("🎯 반을 선택하세요", options)

if selected_class == "직접 입력":
    class_name = st.text_input("새로운 반 이름을 입력하세요")
    default_traits = "이름 / 학생성향 / 어머님성향\n"
else:
    class_name = selected_class
    default_traits = st.session_state.class_templates[selected_class]

traits_input = st.text_area("학생 성향 확인 (수정 가능)", height=150, value=default_traits)

if st.button("🚀 AI가 분석한 완벽한 피드백 생성하기", type="primary"):
    if json_input and uploaded_file and sheet_name and class_name:
        try:
            with st.spinner("🧠 AI가 학생별 성향과 난이도, 단원 특성을 심층 분석하여 코멘트를 작성 중입니다..."):
                data = json.loads(json_input)
                df_q = pd.DataFrame([
                    {"문항번호": p["problem_no"], "단원명": p["curriculum"]["middle_unit_name"], "난이도": p["difficulty"]["level"]} 
                    for p in data.get("problems", [])
                ])
                total_q = len(df_q)
                
                traits_dict = {}
                for line in traits_input.strip().split('\n'):
                    if not line.strip() or "이름 / 학생성향" in line: continue
                    parts = [p.strip() for p in line.split('/')]
                    if len(parts) >= 2:
                        traits_dict[parts[0]] = {"student": parts[1], "parent": parts[2] if len(parts)>2 else ""}

                df_student_input = pd.read_excel(uploaded_file, sheet_name=sheet_name, skiprows=8)
                
                students_list = []
                all_scores = []
                
                bigo_col = next((col for col in df_student_input.columns if '비고' in str(col)), None)
                
                for index, row in df_student_input.iterrows():
                    name = str(row.get('이름', '')).strip()
                    if not name or name in ['계', '평균', 'nan']: continue
                    
                    status = ""
                    if bigo_col and pd.notna(row[bigo_col]):
                        val = str(row[bigo_col]).strip()
                        if any(x in val for x in ['동영상', '결석', '결시']): status = val
                    
                    answers = [str(row[col]).strip().upper() for col in df_student_input.columns if str(col).isdigit()]
                    
                    if status:
                        students_list.append({"학생이름": name, "상태": status, "점수": 0})
                    else:
                        score = sum(1 for ans in answers if ans == 'O')
                        all_scores.append(score)
                        students_list.append({"학생이름": name, "상태": "", "점수": score, "answers": answers})
                
                df_a = pd.DataFrame(students_list)
                all_scores.sort(reverse=True)
                max_score = all_scores[0] if all_scores else 0
                avg_score = round(sum(all_scores)/len(all_scores), 1) if all_scores else 0
                
                final_text_output = f"🌟 {class_name} 오늘의 시험 분석 및 학생별 피드백 🌟\n\n"
                
                for index, st_row in df_a.iterrows():
                    name = st_row["학생이름"]
                    status = st_row["상태"]
                    
                    if status:
                        final_text_output += f"[{name} 학생 피드백]\n▶ 결과\n{name} : {status} / {total_q}\n★ 반 최고 : {max_score} / {total_q}\n◇ 반 평균 : {avg_score} / {total_q}\n◇ 점수분포 : {', '.join(map(str, all_scores))}\n" + "-"*50 + "\n\n"
                    else:
                        score = st_row["점수"]
                        answers = st_row["answers"]
                        s_trait = traits_dict.get(name, {}).get("student", "성실하게 수업에 참여함")
                        p_trait = traits_dict.get(name, {}).get("parent", "꾸준한 지도")
                        
                        report = f"▶ 결과\n{name} : {score} / {total_q}\n★ 반 최고 : {max_score} / {total_q}\n◇ 반 평균 : {avg_score} / {total_q}\n◇ 점수분포 : {', '.join(map(str, all_scores))}\n\n"
                        
                        wrong_q_nums = []
                        chapter_stats = {}
                        
                        for idx, row in df_q.iterrows():
                            if idx < len(answers) and answers[idx] == 'X':
                                wrong_q_nums.append(str(row["문항번호"]))
                                chapter_stats[row["단원명"]] = chapter_stats.get(row["단원명"], 0) + 1
                                
                        report += f"● 오답문항 : {', '.join(wrong_q_nums) if wrong_q_nums else '없음'}\n"
                        worst_chapter = max(chapter_stats, key=chapter_stats.get) if chapter_stats else "없음"
                        
                        # --- 인공지능이 논리적 오류를 검수하며 작성하는 스마트 코멘트 ---
                        ai_prompt = f"""
                        당신은 다정하고 입체적으로 학생을 분석하는 전문 수학 학원 강사입니다. 학부모님께 보낼 피드백 코멘트를 1문단으로 작성하세요.
                        - 학생 이름: {name}
                        - 시험 점수: {score} / {total_q}
                        - 가장 많이 틀린 취약 단원: {worst_chapter}
                        - 학생 평소 성향: {s_trait}
                        - 학부모 니즈: {p_trait}

                        [작성 규칙]
                        1. 학생의 평소 성향과 취약 단원의 난이도/성격을 논리적으로 연결하세요. (예: 성향이 '심화 문제에 겁먹음'인데 취약 단원이 '다항식의 연산'처럼 단순하고 쉬운 단원이라면, 심화에 대한 두려움 때문이 아니라 단순 연산 실수나 방심으로 인한 오답이라고 명확히 분석하세요.)
                        2. 어려워하는 부분에 대한 향후 개선 방안(클리닉, 오답노트 점검 등)을 구체적으로 제시하세요.
                        3. 학부모의 니즈를 반영하고 긍정적인 기대와 응원으로 따뜻하게 마무리하세요.
                        4. '[선생님 코멘트]' 라는 제목으로 시작하세요.
                        """
                        try:
                            response = model.generate_content(ai_prompt)
                            ai_comment = "\n" + response.text
                            time.sleep(1) 
                        except Exception as e:
                            ai_comment = f"\n[선생님 코멘트]\n어머님, 오늘 {name} 학생은 '{worst_chapter}' 파트에서 아쉬운 부분이 있었습니다. 성향을 반영하여 꼼꼼히 보완하겠습니다."
                            
                        report += ai_comment
                        final_text_output += f"[{name} 학생 피드백]\n{report}\n" + "-"*50 + "\n\n"
                
                st.success("✨ AI 분석이 완료되었습니다! 텍스트 파일을 다운로드하세요.")
                st.download_button(label=f"📥 {class_name}_{sheet_name}_AI피드백.txt", data=final_text_output, file_name=f"{class_name}_{sheet_name}_AI피드백.txt", mime="text/plain")
        except Exception as e:
            st.error(f"오류가 발생했습니다. 입력 데이터를 확인해주세요: {e}")
