import streamlit as st
import pandas as pd
import json

st.set_page_config(page_title="🌟 자동 피드백 마법사", layout="wide")
st.title("🌟 우리 학원 자동 피드백 마법사 (맞춤 엑셀 & 시트 선택)")

st.markdown("""
### 1단계: 학원 프로그램 JSON 데이터 붙여넣기
""")
json_input = st.text_area("JSON 데이터 입력칸", height=150)

st.markdown("---")
st.markdown("""
### 2단계: 학생별 채점 결과 엑셀 파일 업로드
선생님이 쓰시는 회차별 엑셀 파일을 그대로 업로드해주세요. 
""")
uploaded_file = st.file_uploader("학생 답안 엑셀 파일 선택", type=["xlsx", "xls"])

# 엑셀 파일이 업로드되면 시트 이름을 자동으로 읽어와서 선택 상자(selectbox)를 만듭니다.
sheet_name = None
if uploaded_file is not None:
    try:
        # 엑셀 파일의 모든 시트 이름을 읽어옵니다.
        xls = pd.ExcelFile(uploaded_file)
        sheet_names = xls.sheet_names
        
        # 사용자가 시트를 선택할 수 있도록 합니다.
        sheet_name = st.selectbox("📝 피드백을 생성할 엑셀 시트(회차)를 선택하세요", sheet_names)
    except Exception as e:
        st.error(f"엑셀 파일을 읽는 중 오류가 발생했습니다: {e}")

st.markdown("---")
st.markdown("""
### 3단계: 반 이름 및 맞춤 성향 입력
""")
class_name = st.text_input("반 이름을 입력하세요 (예: 공통수학1 기본 화목반)")
traits_input = st.text_area("학생 및 학부모 성향 입력 (선택사항)", height=150,
                            value="김은성 / 성격이 급해 연산 실수가 잦음 / 꼼꼼한 풀이 과정 지도를 원하심\n박선우 / 심화 문제에 지레 겁을 먹음 / 칭찬과 격려 위주의 상담 선호",
                            help="이름 / 학생성향 / 어머님성향 순서로 슬래시(/)로 구분해서 적어주세요.")

if st.button("🚀 맞춤형 반별 피드백 생성하기", type="primary"):
    if not json_input.strip():
        st.error("JSON 데이터를 먼저 입력해주세요!")
    elif uploaded_file is None:
        st.error("학생 답안 엑셀 파일을 업로드해주세요!")
    elif sheet_name is None:
        st.error("엑셀 시트를 선택해주세요!")
    else:
        try:
            # 1. JSON 데이터 파싱
            data = json.loads(json_input)
            problems = data.get("problems", [])
            
            q_info = []
            for p in problems:
                q_info.append({
                    "문항번호": p["problem_no"],
                    "과정": p["grade_semester"],
                    "단원명": p["curriculum"]["middle_unit_name"],
                    "유형명": p["problem_type"]["type_name"],
                    "난이도": p["difficulty"]["level"]
                })
            df_q = pd.DataFrame(q_info)
            total_q = len(df_q)
            
            # 2. 성향 데이터 파싱
            traits_dict = {}
            for line in traits_input.strip().split('\n'):
                if not line.strip(): continue
                parts = [p.strip() for p in line.split('/')]
                if len(parts) >= 3:
                    traits_dict[parts[0]] = {"student": parts[1], "parent": parts[2]}
                elif len(parts) == 2:
                    traits_dict[parts[0]] = {"student": parts[1], "parent": ""}
            
            # 3. 실전 엑셀 양식 데이터 파싱 (선택한 시트 사용)
            # skiprows=8 을 하면 1~9번째 줄(인덱스 0~8)을 무시하고 실제 헤더(이름, 학교, 1, 2...)가 있는 10번째 줄을 읽습니다.
            df_student_input = pd.read_excel(uploaded_file, sheet_name=sheet_name, skiprows=8)
            
            students_list = []
            all_scores = []
            
            for index, row in df_student_input.iterrows():
                # '이름' 열에서 이름을 가져옴 (C열에 해당)
                if '이름' not in df_student_input.columns:
                     st.error("선택하신 시트에 '이름' 열이 없습니다. 올바른 회차 시트를 선택했는지 확인해주세요.")
                     break
                     
                name = str(row['이름']).strip()
                # 이름이 비어있거나 '계', '평균' 등의 통계행이면 건너뜀
                if pd.isna(name) or name == 'nan' or not name or name in ['계', '평균']:
                    continue
                
                # 숫자로 된 컬럼 이름(1, 2, 3...)만 답안 열로 간주하여 추출
                answers = []
                for col in df_student_input.columns:
                    if str(col).isdigit():
                        val = row[col]
                        ans = str(val).strip().upper() if pd.notna(val) else ""
                        answers.append(ans)
                
                # O 개수로 점수 계산
                score = sum(1 for ans in answers if ans == 'O')
                all_scores.append(score)
                
                student_data = {"학생이름": name, "점수": score, "answers": answers}
                students_list.append(student_data)
                
            df_a = pd.DataFrame(students_list)
            
            # 4. 피드백 결과 생성 및 텍스트 조합
            all_scores.sort(reverse=True)
            max_score = all_scores[0] if all_scores else 0
            avg_score = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0
            
            final_title = f"🌟 {class_name} 오늘의 시험 분석 및 학생별 피드백 ({sheet_name}) 🌟" if class_name else f"🌟 오늘의 시험 분석 및 학생별 피드백 ({sheet_name}) 🌟"
            final_text_output = final_title + "\n\n"
            
            for index, st_row in df_a.iterrows():
                name = st_row["학생이름"]
                score = st_row["점수"]
                answers = st_row["answers"]
                
                # 성향 가져오기 (없으면 기본값)
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
                
                # 성향을 반영한 스마트 코멘트 조립
                if score == total_q:
                    ai_comment = f"\n[선생님 코멘트]\n어머님, 오늘 {name} 학생은 오답 없이 완벽하게 시험을 마무리했습니다. 평소 '{s_trait}' 특징을 칭찬하고 더욱 발전시키겠습니다. 어머님께서 중요하게 생각하시는 '{p_trait}' 부분도 학원에서 신경 써서 지도 중이니 가정에서도 많은 칭찬 부탁드립니다."
                else:
                    ai_comment = f"\n[선생님 코멘트]\n어머님, 오늘 {name} 학생은 전체적으로 열심히 응시했으나, 특히 '{worst_chapter}' 파트에서 아쉬운 부분이 있었습니다. 이번 오답은 {name} 학생이 평소 '{s_trait}' 측면과도 연관이 있어 보입니다. 어머님께서 강조하셨던 '{p_trait}' 방향에 맞춰 다음 클리닉 시간에 이 단원을 꼼꼼히 점검하고 약점을 보완하겠습니다. 많은 격려 부탁드립니다."
                    
                report += ai_comment
                
                final_text_output += f"[{name} 학생 피드백]\n"
                final_text_output += report + "\n"
                final_text_output += "-" * 50 + "\n\n"
            
            st.success("✨ 분석이 완료되었습니다! 아래 버튼을 눌러 메모장(.txt) 파일을 다운로드하세요.")
            st.download_button(
                label="📥 반별_맞춤형_피드백.txt 다운로드",
                data=final_text_output,
                file_name=f"{class_name}_{sheet_name}_피드백.txt" if class_name else f"맞춤형_{sheet_name}_피드백.txt",
                mime="text/plain"
            )
            
        except Exception as e:
            st.error(f"오류가 발생했습니다. 입력 양식이나 엑셀 파일을 다시 확인해 주세요. (상세 오류: {e})")
