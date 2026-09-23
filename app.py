import streamlit as st
import pandas as pd
import json
import io

st.set_page_config(page_title="🌟 자동 피드백 마법사", layout="wide")
st.title("🌟 우리 학원 자동 피드백 마법사")

st.markdown("""
### 1단계: 학원 프로그램 JSON 데이터 붙여넣기
아래 칸에 학원 프로그램에서 복사한 복잡한 괄호 데이터를 통째로 붙여넣어 주세요. 에러 없이 한 번에 읽습니다!
""")
json_input = st.text_area("JSON 데이터 입력칸", height=200)

st.markdown("---")
st.markdown("""
### 2단계: 학생별 채점 결과 입력
학생 이름과 정답 여부(O, X)를 아래 예시처럼 적어주세요. 한 줄에 한 명씩 입력하시면 됩니다.
(예시: 김은성, O, X, O, X, O, O, O, O, O, X, O, X, O, X, O, O, X, O, O, X)
""")
student_input = st.text_area("학생 채점 결과 입력칸", height=150, 
                           value="김은성, O, X, O, X, O, O, O, O, O, X, O, X, O, X, O, O, X, O, O, X\n이학생, O, O, O, O, O, O, O, O, O, O, O, O, O, O, O, O, O, O, O, O")

if st.button("🚀 피드백 엑셀 파일 생성하기", type="primary"):
    if not json_input.strip():
        st.error("JSON 데이터를 먼저 입력해주세요!")
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
            
            # 2. 학생 데이터 파싱
            students_list = []
            all_scores = []
            
            lines = [line.strip() for line in student_input.split('\n') if line.strip()]
            for line in lines:
                parts = [p.strip() for p in line.split(',')]
                name = parts[0]
                answers = parts[1:]
                
                score = sum(1 for ans in answers if ans.upper() == 'O')
                all_scores.append(score)
                
                student_data = {"학생이름": name, "점수": score}
                for i, ans in enumerate(answers):
                    student_data[f"{i+1}번"] = ans.upper()
                students_list.append(student_data)
                
            df_a = pd.DataFrame(students_list)
            
            # 3. 피드백 결과 생성
            all_scores.sort(reverse=True)
            max_score = all_scores[0] if all_scores else 0
            avg_score = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0
            
            feedback_list = []
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
                feedback_list.append({"이름": name, "점수": score, "자동 생성 피드백": report})
                
            df_r = pd.DataFrame(feedback_list)
            
            # 4. 엑셀 파일로 변환하여 다운로드 버튼 제공 (수정된 부분)
            output = io.BytesIO()
            with pd.ExcelWriter(output) as writer:
                df_q.to_excel(writer, sheet_name='문항정보', index=False)
                df_a.to_excel(writer, sheet_name='학생답안', index=False)
                df_r.to_excel(writer, sheet_name='피드백결과', index=False)
            
            excel_data = output.getvalue()
            
            st.success("✨ 분석이 완료되었습니다! 아래 버튼을 눌러 엑셀 파일을 다운로드하세요.")
            st.download_button(
                label="📥 오늘의_시험분석_피드백.xlsx 다운로드",
                data=excel_data,
                file_name="오늘의_시험분석_피드백.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        except Exception as e:
            st.error(f"오류가 발생했습니다. 입력하신 데이터 양식을 다시 확인해 주세요. (상세 오류: {e})")
