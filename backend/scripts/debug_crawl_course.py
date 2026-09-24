import sys
import os
import requests
from bs4 import BeautifulSoup

# 백엔드 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.crawlers.course_crawler import crawl_course_list_html, parse_course_list_html

def debug_crawl(session_cookie, year="2026", semester="2"):
    # 1. 쿠키 포맷 보정
    if "=" not in session_cookie:
        session_cookie = f"JSESSIONID={session_cookie}"
        print(f"ℹ️ 쿠키에 'JSESSIONID='를 자동으로 추가했습니다: {session_cookie[:25]}...")

    # 2. 테스트할 학과 (소프트웨어전공: 5446)
    dept_code = "5446"
    dept_name = "소프트웨어전공"

    print(f"\n==========================================")
    print(f"[디버그 테스트] 연도: {year}, 학기: {semester}, 학과: {dept_name}({dept_code})")
    print(f"==========================================")

    # 3. 요청 시도
    for grad in ["H1", "H2", "H3", "H4"]:
        print(f"\n--- 학년 {grad} 테스트 ---")
        try:
            html = crawl_course_list_html(
                session_cookie=session_cookie,
                year=year,
                semester=semester,
                department_code=dept_code,
                student_number="202104255",
                student_grade="4",
                student_department_code="5446",
                fact_code="5444",
                fact_srch="5446",
                grad_area1=grad,
            )

            # 서버 응답 분석
            if "로그인" in html or "logout" in html or "시간이 만료" in html or "경과하였습니다" in html:
                print("[-] [경고] 서버 응답: 세션이 만료되었거나 로그인이 유효하지 않습니다!")
                print("응답 내용 일부:\n", html[:300])
                return

            courses = parse_course_list_html(html, department=dept_name)
            print(f"결과: {len(courses)}개 과목 파싱됨.")

            if courses:
                print("[+] 첫 번째 과목 샘플:", courses[0]["name"], courses[0]["subject_code"], courses[0]["professor"])
            else:
                # 파싱이 0개일 때 응답 HTML의 주요 부분을 확인
                soup = BeautifulSoup(html, "html.parser")
                title = soup.select_one("h5")
                title_text = title.get_text(strip=True) if title else "제목 없음"
                tables = soup.select("table")
                print(f"   [*] HTML 제목: {title_text}, 발견된 테이블 수: {len(tables)}, HTML 길이: {len(html)} 글자")
                
                # 안내 메시지가 있는지 확인
                no_data = soup.select_one("td")
                if no_data:
                    print(f"   [*] 본문 텍스트: {no_data.get_text(strip=True)[:100]}")

        except Exception as e:
            print(f"[-] 오류 발생: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python scripts/debug_crawl_course.py \"SESSION_COOKIE\" [YEAR] [SEMESTER]")
        print("예시: python scripts/debug_crawl_course.py \"ABC...\" 2026 2")
    else:
        cookie = sys.argv[1]
        y = sys.argv[2] if len(sys.argv) > 2 else "2026"
        s = sys.argv[3] if len(sys.argv) > 3 else "2"
        debug_crawl(cookie, y, s)
