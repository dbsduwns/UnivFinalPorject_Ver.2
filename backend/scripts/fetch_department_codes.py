import requests
from bs4 import BeautifulSoup
import sys
import os

# 백엔드 경로 추가 (필요시)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def fetch_department_codes(session_cookie):
    # 쿠키 형식 보정 (JSESSIONID= 이 빠져있고 값만 있는 경우 대응)
    if "=" not in session_cookie:
        session_cookie = f"JSESSIONID={session_cookie}"
        print(f"ℹ️ 쿠키 형식을 보정했습니다: {session_cookie[:20]}...")

    url = "https://app.kangnam.ac.kr/knumis/sbr/sbr3070T.jsp"
    headers = {
        "Cookie": session_cookie,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://app.kangnam.ac.kr/knumis/main/main.jsp",
    }

    print(f"⏳ {url} 에서 학과 목록을 가져오는 중...")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # 인코딩 처리 (KNU는 보통 euc-kr 또는 cp949)
        html = response.content.decode('euc-kr', errors='replace')
        soup = BeautifulSoup(html, "html.parser")
        
        # 학과 선택 select 태그 찾기 (보통 dept_srch 또는 dept_code)
        # sbr3070T.jsp의 소스를 분석해야 정확하지만 일반적인 패턴으로 시도
        select_tag = soup.find("select", {"name": "dept_srch"})
        if not select_tag:
            # 다른 가능성 있는 이름들
            for name in ["dept_code", "stnt_dept", "dept_code1"]:
                select_tag = soup.find("select", {"name": name})
                if select_tag:
                    break
        
        if not select_tag:
            print("❌ 학과 선택(select) 태그를 찾을 수 없습니다. 세션 쿠키가 유효한지 확인해주세요.")
            # 페이지 일부 출력하여 디버깅 도와줌
            print("\n--- 페이지 소스 일부 ---")
            print(html[:500])
            return

        options = select_tag.find_all("option")
        departments = []
        for opt in options:
            code = opt.get("value")
            name = opt.get_text(strip=True)
            if code and code.strip():
                departments.append({"code": code, "name": name})

        print(f"✅ 총 {len(departments)}개의 학과/전공 코드를 찾았습니다.\n")
        
        import json
        output_path = "backend/data/department_codes_all.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(departments, f, ensure_ascii=False, indent=2)
            
        print(f"📂 결과가 저장되었습니다: {output_path}")
        
        # 화면에 일부 출력
        print("\n--- 추출된 코드 (일부) ---")
        for dept in departments[:10]:
            print(f"코드: {dept['code']} | 학과명: {dept['name']}")
        if len(departments) > 10:
            print("...")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python scripts/fetch_department_codes.py \"SESSION_COOKIE\"")
        print("예: python scripts/fetch_department_codes.py \"JSESSIONID=...; SSOGUID=...\"")
    else:
        cookie = sys.argv[1]
        fetch_department_codes(cookie)
