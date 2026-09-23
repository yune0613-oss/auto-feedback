import streamlit as st
import pandas as pd
import json

st.set_page_config(page_title="🌟 자동 피드백 마법사", layout="wide")
st.title("🌟 우리 학원 자동 피드백 마법사")

st.markdown("""
### 1단계: 학원 프로그램 JSON 데이터 붙여넣기
아래 칸에 학원 프로그램에서 복사한 복잡한 괄호 데이터를 통째로 붙여넣어 주세요.
""")
json_input = st.text_area("JSON 데이터 입력칸", height=200)

st.markdown("---")
st.markdown("""
### 2단계: 학생별 채점 결과 엑셀 파일 업로드
학생 이름과 정답 여부(O, X)가 입력된 엑셀 파일을 업로드해주세요.
*   **첫 번째 열(A열)**: 학생 이름
*   **두 번째 열(B열)부터**: 1번, 2번, 3번... 문항의 O/X 결과
(※ 맨 위에 제목 줄이 없어도 알아서 첫 줄부터 학생으로 인식합니다.)
""")

uploaded_file = st.file_uploader("학생 답안 엑셀 파일 선택", type=["xlsx", "xls"])

if st.button("🚀 피드백 텍스트 파일 생성하기", type="primary"):
    if not json_input.strip():
        st.error("JSON 데이터를 먼저 입력해주세요!")
    elif uploaded_file is None:
        st.error("학생 답안 엑셀 파일을 업로드해주세요!")
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
            
            # 2. 학생 데이터 파싱 (엑셀 파일에서 읽기)
            # 엑셀 파일 읽기 (header=None 으로 설정하여 첫 줄부터 데이터로 읽음)
            df_student_input = pd.read_excel(uploaded_file, header=None)
            
            students_list = []
            all_scores = []
            
            for index, row in df_student_input.iterrows():
                name = str(row[0]).strip()
                if pd.isna(name) or name == 'nan' or not name:
                    continue # 이름이 비어있으면 건너뜀
                
                # 1번 열부터 마지막 열까지의 답안 추출 (O, X)
                answers = [str(val).strip().upper() for val in row[1:] if pd.notna(val) and str(val).strip() != 'nan']
                
                # O 개수로 점수 계산
                score = sum(1 for ans in answers if ans == 'O')
                all_scores.append(score)
                
                student_data = {"학생이름": name, "점수": score}
                for i, ans in enumerate(answers):
                    student_data[f"{i+1}번"] = ans
                students_list.append(student_data)
                
            df_a = pd.DataFrame(students_list)
            
            # 3. 피드백 결과 생성 및 텍스트 조합
            all_scores.sort(reverse=True)
            max_score = all_scores[0] if all_scores else 0
            avg_score = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0
            
            final_text_output = "🌟 오늘의 시험 분석 및 학생별 피드백 🌟\n\n"
            
            for index, st_row in df_a.iterrows():
                name = st_row["학생이름"]
                score = st_row["점수"]
                
                report = f"▶ 결과\n{name} : {score} / {total_q}\n★ 반 최고 : {max_score} / {total_q}\n◇ 반 평균 : {avg_score} / {total_q}\n◇ 점수분포 : {', '.join(map(str, all_scores))}\n\n"
                
                wrong_q_nums = []
                chapter_stats = {}
                
                for idx, row in df_q.iterrows():
                    q_num = row["문항번호"]
                    chapter = row["단원명"]
                    ans = st_row.get(f"{q_num}번", "")
                    
                    if ans == 'X':
                        wrong_q_nums.append(str(q_num))
                        chapter_stats[chapter] = chapter_stats.get(chapter, 0) + 1
                        
                report += f"● 오답문항 : {', '.join(wrong_q_nums) if wrong_q_nums else '없음'}\n"
                worst_chapter = max(chapter_stats, key=chapter_stats.get) if chapter_stats else ""
                
                if score == total_q:
                    ai_comment = f"\n[선생님 코멘트]\n어머님, 오늘 {name} 학생은 오답 없이 완벽하게 시험을 마무리했습니다. 그동안 열심히 노력해 준 덕분입니다. 앞으로도 지금처럼 꾸준히 페이스를 유지할 수 있도록 지도하겠습니다. 가정에서도 많은 칭찬 부탁드립니다."
                else:
                    ai_comment = f"\n[선생님 코멘트]\n어머님, 오늘 {name} 학생은 전체적으로 열심히 응시했으나, 특히 '{worst_chapter}' 파트에서 다소 아쉬운 부분이 있었습니다. 다음 시간(또는 클리닉 시간)에는 이 어려워하는 단원의 내용을 꼼꼼히 점검하고 개선 방안을 찾아 약점을 보완할 계획입니다. 이 부분을 잘 채워나가면 다음번엔 훨씬 더 좋은 결과가 있을 거라 믿습니다. 가정에서도 많은 격려와 응원 부탁드립니다."
                    
                report += ai_comment
                
                # 텍스트 파일에 학생 한 명 분량 추가
                final_text_output += f"[{name} 학생 피드백]\n"
                final_text_output += report + "\n"
                final_text_output += "-" * 50 + "\n\n"
            
            # 4. 텍스트 파일 다운로드 제공
            st.success("✨ 분석이 완료되었습니다! 아래 버튼을 눌러 메모장(.txt) 파일을 다운로드하세요.")
            st.download_button(
                label="📥 오늘의_시험분석_피드백.txt 다운로드",
                data=final_text_output,
                file_name="오늘의_시험분석_피드백.txt",
                mime="text/plain"
            )
            
        except Exception as e:
            st.error(f"오류가 발생했습니다. 입력하신 데이터 양식이나 엑셀 파일을 다시 확인해 주세요. (상세 오류: {e})")
