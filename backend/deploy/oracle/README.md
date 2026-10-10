# Oracle VM deployment

이 구성은 Oracle Ampere A1 VM 한 대에서 FastAPI, PostgreSQL, Chroma,
Playwright 크롤러와 HTTPS 프록시를 함께 실행한다.

## 권장 VM

- Shape: `VM.Standard.A1.Flex`
- CPU/RAM: 2 OCPU / 12 GB
- Image: Ubuntu 24.04 ARM64
- Boot volume: 100 GB
- 공개 포트: TCP 22, 80, 443과 UDP 443
- 비공개 포트: PostgreSQL 5432, FastAPI 8000

Oracle 네트워크 보안 목록과 Ubuntu 방화벽 양쪽에서 80/443을 허용한다.
5432와 8000은 외부에 공개하지 않는다.

## 서버 준비

Ubuntu에 Docker Engine과 Docker Compose 플러그인을 설치한 뒤 저장소를
복제한다. `backend` 디렉터리에서 환경 파일을 만든다.

```bash
cp .env.oracle.example .env.oracle
chmod 600 .env.oracle
```

`.env.oracle`에 실제 도메인, DB 비밀번호, JWT 비밀키, Gemini API 키와
학교 포털 정보를 입력한다. 비밀번호에 `@`, `:`, `/`, `%` 같은 문자가
들어가면 `DATABASE_URL` 안의 비밀번호는 URL 인코딩해야 한다.

도메인의 A 레코드는 VM 공인 IP를 가리켜야 한다. Caddy가 첫 실행 때
TLS 인증서를 자동 발급한다.

## 첫 실행과 점검

```bash
docker compose --env-file .env.oracle -f docker-compose.oracle.yml build
docker compose --env-file .env.oracle -f docker-compose.oracle.yml up -d db api
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/health/db
docker compose --env-file .env.oracle -f docker-compose.oracle.yml up -d caddy
curl https://YOUR_DOMAIN/health
```

API 컨테이너는 시작할 때 `alembic upgrade head`를 실행한다. AI 임베딩
모델은 첫 AI 요청 때 내려받아 `huggingface_cache` 볼륨에 보관한다. 첫
응답만 평소보다 오래 걸릴 수 있다.

서버 이미지는 `requirements.server.txt`만 설치한다. 로컬 개발 환경을
그대로 기록한 `requirements.txt`에서 서버가 사용하지 않는 Docker SDK,
Kubernetes SDK, 데이터 분석 패키지를 제외해 ARM 빌드 크기와 설치 시간을
줄였다.

배포 후 ARM 아키텍처, PostgreSQL, Chroma, PyTorch와 Playwright Chromium을
한 번에 점검한다.

```bash
chmod +x deploy/oracle/verify.sh deploy/oracle/backup.sh
deploy/oracle/verify.sh
```

Gemini 호출과 실제 RAG 초기화까지 확인하려면 다음처럼 실행한다.

```bash
VERIFY_AI=1 deploy/oracle/verify.sh
```

## Render 데이터 이전

Render의 PostgreSQL External Database URL을 `RENDER_DATABASE_URL`로
설정한 환경에서 custom-format 백업을 만든다. URL과 백업 파일에는 사용자
데이터가 포함되므로 Git에 추가하지 않는다.

```bash
docker run --rm -e RENDER_DATABASE_URL postgres:15-bookworm \
  sh -c 'pg_dump "$RENDER_DATABASE_URL" --format=custom --no-owner' \
  > render.dump
```

Oracle VM으로 `render.dump`를 복사하고 API를 잠시 중지한 다음 복원한다.

```bash
docker compose --env-file .env.oracle -f docker-compose.oracle.yml stop api
docker compose --env-file .env.oracle -f docker-compose.oracle.yml exec -T db \
  pg_restore --clean --if-exists --no-owner \
  -U knu_app -d knudb < render.dump
docker compose --env-file .env.oracle -f docker-compose.oracle.yml up -d api
```

`POSTGRES_USER`나 `POSTGRES_DB` 값을 바꿨다면 복원 명령에도 같은 값을
사용한다. 복원 후 `/health/db`, 로그인, 신고/차단, 채팅, AI 대화를 실제로
확인하기 전에는 Render를 종료하지 않는다.

## Chroma와 정적 파일 이전

현재 사용 중인 `backend/chroma_db`와 `backend/static`을 Oracle VM의
`backend` 디렉터리로 복사한다. 이 두 디렉터리는 컨테이너에 bind mount되어
재배포 후에도 유지된다.

```bash
rsync -av chroma_db/ USER@VM_IP:/path/to/project/backend/chroma_db/
rsync -av static/ USER@VM_IP:/path/to/project/backend/static/
```

## 운영 백업

`deploy/oracle/backup.sh`를 cron으로 매일 실행한다. 백업은 VM 외부에도
주기적으로 복사해야 한다. Oracle 무료 VM은 비활성 상태로 판단되면 회수될
수 있으므로 VM 내부 사본만으로는 충분하지 않다.

## 최종 전환

1. Oracle 주소로 전체 기능을 점검한다.
2. Expo의 `EXPO_PUBLIC_API_URL`을 Oracle HTTPS 주소로 변경해 빌드한다.
3. 짧은 점검 시간 동안 Render 쓰기를 중단하고 최종 DB 덤프를 복원한다.
4. DNS/API 주소를 Oracle로 전환한다.
5. 최소 며칠간 Render를 유지한 뒤 백업을 확인하고 종료한다.
