# KNU Campus 관리자 웹

Vercel에서 정적 사이트로 배포하는 관리자 전용 웹입니다. `config.js`의 `ADMIN_API_URL`을 공개 API 주소로 설정한 뒤 `frontend/admin-web`을 Vercel 프로젝트의 Root Directory로 지정하세요.

관리자 로그인 뒤 받은 액세스 토큰은 브라우저 탭 세션에만 보관됩니다. 서버는 모든 `/api/admin/*` 요청에서 토큰과 관리자 권한을 다시 검증합니다.

현재 화면은 공지, 커뮤니티, 데이터 수집, 회원 관리에 연결됩니다. 통계 상세, AI 문의 모니터링, 수집 이력은 API 확장 대상이며 화면에는 의도적으로 노출하지 않습니다.
