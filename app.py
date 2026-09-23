import streamlit as st
import pandas as pd
import json

st.set_page_config(page_title="🌟 자동 피드백 마법사", layout="wide")

# --- 앱 내장 메모리 (세션 상태) 활용 ---
# 초기 반 세팅 (앱을 처음 열었을 때 기본적으로 있는 반)
if 'class_templates' not in st.session_state:
    st.session_state.class_templates = {
        "공통수학1 기본 월금반": "박선규 / 꼼꼼하지만 속도가 약간 느림 / 시간 분배 연습 강조\n박선우 / 심화 문제에 지레 겁을 먹음 / 칭찬과 격려 위주의 상담 선호\n김은성 / 성격이 급해 연산 실수가 잦음 / 오답노트 철저히\n장주하 / 기본기가 좋음 / 응용 문제 도전 필요",
        "중3-1 심화 화목반": "김학생 / 선행이 잘 되어 있음 / 고등 과정 연계 짚어주기\n이학생 / 계산 실수가 잦음 / 반복 훈련 원하심"
    }

# ==========================================
# ⚙️ 왼쪽 사이드바: 템플릿 관리 메뉴
# ==========================================
with st.sidebar:
    st.header("⚙️ 우리 학원 반 관리")
    st.write("이곳에서 자유롭게 반을 추가, 수정, 삭제하세요.")
    
    st.markdown("---")
    st.subheader("➕ 새 반 추가 / 기존 반 수정")
    st.write("※ 기존에 있는 반 이름을 똑같이 적고 내용을 쓰면 내용이 수정(덮어쓰기) 됩니다.")
    new_class_name = st.text_input("반 이름 입력")
    new_class_traits = st.text_area("학생 성향 입력 (이름 / 성향 / 어머님니즈)", height=150)
    
    if st.button("💾 반 저장하기"):
        if new_class_name.strip() != "":
            st.session_state.class_templates[new_class_name] = new_class_traits
            st.success(f"'{new_class_name}' 저장 완료!")
        else:
            st.error("반 이름을 입력하세요.")
            
    st.markdown("---")
    st.subheader("🗑️ 기존 반 삭제")
    if st.session_state.class_templates:
        class_to_delete = st.selectbox("삭제할 반 선택", list(st.session_state.class_templates.keys()))
        if st.button("❌ 선택한 반 삭제"):
            if class_to_delete in st.session_state.class_templates:
                del st.session_state.class_templates[class_to_delete]
                st.success(f"'{class_to_delete}' 삭제 완료!")
                st.rerun() # 화면 새로고침
    else:
        st.write("저장된 반이 없습니다.")

# ==========================================
# 🌟 메인 화면: 피드백 생성
# ==========================================
st.title("🌟 우리 학원 자동 피드백 마법사")

st.markdown("### 1단계: 학원 프로그램 JSON 데이터 붙여넣기")
json_input = st.text_area("JSON 데이터 입력칸", height=150)

st.markdown("---")
st.markdown("### 2단계: 학생별 채점 결과 엑셀 파일 업로드")
uploaded_file = st.file_uploader("학생 답안 엑셀 파일 선택", type=["xlsx", "xls"])

sheet_name = None
if uploaded_file is not None:
    try:
        xls = pd.ExcelFile(uploaded_file)
        # '기본값'이라는 글자가 포함되지 않은 시트(회차)만 필터링합니다.
        sheet_names = [sheet for sheet in xls.sheet_names if "기본값" not in sheet]
        
        if not sheet_names:
            st.warning("업로드된 파일에 회차 시트가 없습니다.")
        else:
            sheet_name = st.selectbox("📝 피드백을 생성할 회차(시트)를 선택하세요", sheet_names)
    except Exception as e:
        st.error(f"엑셀 파일을 읽는 중 오류가 발생했습니다: {e}")

st.markdown("---")
st.markdown("### 3단계: 피드백을 만들 반 선택")

options = ["직접 입력"] + list(st.session_state.class_templates.keys())
selected_class = st.selectbox("🎯 반을 선택하세요", options)

if selected_class == "직접 입력":
    class_name = st.text_input("새로운 반 이름을 입력하세요")
    default_traits = "이름 / 학생성향 / 어머님성향\n"
else:
    class_name = selected_class
    default_traits = st.session_state.class_templates[selected_class]

traits_input = st.text_area("학생 성향 확인 (이번 피드백에만 일회성으로 수정 가능)", height=150, value=default_traits)

if st.button("🚀 선택한 반 피드백 텍스트 생성하기", type="primary"):
    if not json_input.strip():
        st.error("JSON 데이터를 먼저 입력해주세요!")
    elif uploaded_file is None:
        st.error("학생 답안 엑셀 파일을 업로드해주세요!")
    elif sheet_name is None:
        st.error("엑셀 시트를 선택해주세요!")
    elif not class_name.strip():
        st.error("반 이름을 입력하거나 선택해주세요!")
    else:
        try:
            # 1. JSON 데이터 파싱
            data = json.loads(json_input)
            problems = data.get("problems", [])
            
            q_info = []
            for p in problems:
                q_info.append({
                    "문항번호": p["problem_no"],
                    "단원명": p["curriculum"]["middle_unit_name"]
                })
            df_q = pd.DataFrame(q_info)
            total_q = len(df_q)
            
            # 2. 성향 데이터 파싱
            traits_dict = {}
            for line in traits_input.strip().split('\n'):
                if not line.strip() or "이름 / 학생성향" in line: continue
                parts = [p.strip() for p in line.split('/')]
                if len(parts) >= 3:
                    traits_dict[parts[0]] = {"student": parts[1], "parent": parts[2]}
                elif len(parts) == 2:
                    traits_dict[parts[0]] = {"student": parts[1], "parent": ""}
            
            # 3. 실전 엑셀 파싱 (비고란 확인 포함)
            df_student_input = pd.read_excel(uploaded_file, sheet_name=sheet_name, skiprows=8)
            
            students_list = []
            all_scores = []
            
            bigo_col = None
            for col in df_student_input.columns:
                if '비고' in str(col):
                    bigo_col = col
                    break
            
            for index, row in df_student_input.iterrows():
                if '이름' not in df_student_input.columns:
                     st.error("선택하신 시트에 '이름' 열이 없습니다.")
                     break
                     
                name = str(row['이름']).strip()
                if pd.isna(name) or name == 'nan' or not name or name in ['계', '평균']:
                    continue
                
                status = ""
                if bigo_col and pd.notna(row[bigo_col]):
                    val = str(row[bigo_col]).strip()
                    if any(x in val for x in ['동영상', '결석', '결시']):
                        status = val
                
                answers = []
                for col in df_student_input.columns:
                    if str(col).isdigit():
                        val = row[col]
                        ans = str(val).strip().upper() if pd.notna(val) else ""
                        answers.append(ans)
                
                if status:
                    student_data = {"학생이름": name, "상태": status, "answers": [], "점수": 0}
                    students_list.append(student_data)
                else:
                    score = sum(1 for ans in answers if ans == 'O')
                    all_scores.append(score)
                    student_data = {"학생이름": name, "상태": "", "점수": score, "answers": answers}
                    students_list.append(student_data)
                
            df_a = pd.DataFrame(students_list)
            
            # 4. 통계 계산 
            all_scores.sort(reverse=True)
            max_score = all_scores[0] if all_scores else 0
            avg_score = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0
            
            # 5. 텍스트 조합
            final_title = f"🌟 {class_name} 오늘의 시험 분석 및 학생별 피드백 ({sheet_name}) 🌟"
            final_text_output = final_title + "\n\n"
            
            for index, st_row in df_a.iterrows():
                name = st_row["학생이름"]
                status = st_row["상태"]
                
                if status:
                    report = f"▶ 결과\n{name} : {status} / {total_q}\n★ 반 최고 : {max_score} / {total_q}\n◇ 반 평균 : {avg_score} / {total_q}\n◇ 점수분포 : {', '.join(map(str, all_scores))}\n"
                    final_text_output += f"[{name} 학생 피드백]\n"
                    final_text_output += report + "\n"
                    final_text_output += "-" * 50 + "\n\n"
                    
                else:
                    score = st_row["점수"]
                    answers = st_row["answers"]
                    
                    s_trait = traits_dict.get(name, {}).get("student", "성실하게 수업에 참여함")
                    p_trait = traits_dict.get(name, {}).get("parent", "꾸준한 지도")
                    
                    report = f"▶ 결과\n{name} : {score} / {total_q}\n★ 반 최고 : {max_score} / {total_q}\n◇ 반 평균 : {avg_score} / {total_q}\n◇ 점수분포 : {', '.join(map(str, all_scores))}\n\n"
                    
                    wrong_q_nums = []
                    chapter_stats = {}
                    
                    for idx, row in df_q.iterrows():
                        if idx < len(answers):
                            if answers[idx] == 'X':
                                wrong_q_nums.append(str(row["문항번호"]))
                                chapter_stats[row["단원명"]] = chapter_stats.get(row["단원명"], 0) + 1
                                
                    report += f"● 오답문항 : {', '.join(wrong_q_nums) if wrong_q_nums else '없음'}\n"
                    worst_chapter = max(chapter_stats, key=chapter_stats.get) if chapter_stats else ""
                    
                    if score == total_q:
                        ai_comment = f"\n[선생님 코멘트]\n어머님, 오늘 {name} 학생은 오답 없이 완벽하게 시험을 마무리했습니다. 평소 '{s_trait}' 특징을 칭찬하고 더욱 발전시키겠습니다. 어머님께서 중요하게 생각하시는 '{p_trait}' 부분도 학원에서 신경 써서 지도 중이니 가정에서도 많은 칭찬 부탁드립니다."
                    else:
                        ai_comment = f"\n[선생님 코멘트]\n어머님, 오늘 {name} 학생은 전체적으로 열심히 응시했으나, 특히 '{worst_chapter}' 파트에서 아쉬운 부분이 있었습니다. 이번 오답은 {name} 학생이 평소 '{s_trait}' 측면과도 연관이 있어 보입니다. 어머님께서 강조하셨던 '{p_trait}' 방향에 맞춰 다음 클리닉 시간에 이 단원을 꼼꼼히 점검하고 약점을 보완하겠습니다. 많은 격려 부탁드립니다."
                        
                    report += ai_comment
                    
                    final_text_output += f"[{name} 학생 피드백]\n"
                    final_text_output += report + "\n"
                    final_text_output += "-" * 50 + "\n\n"
            
            st.success("✨ 분석이 완료되었습니다! 아래 버튼을 눌러 파일을 다운로드하세요.")
            st.download_button(
                label=f"📥 {class_name}_{sheet_name}_피드백.txt 다운로드",
                data=final_text_output,
                file_name=f"{class_name}_{sheet_name}_피드백.txt",
                mime="text/plain"
            )
            
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
