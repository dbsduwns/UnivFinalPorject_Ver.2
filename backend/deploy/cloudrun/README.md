# Google Cloud Run 배포 안내

이 구성에서는 FastAPI 애플리케이션을 Cloud Run에서 실행하고, 관계형 데이터는 Supabase PostgreSQL에, RAG 벡터는 Qdrant Cloud에 저장합니다.

## 구성 요소

- Cloud Run: FastAPI, Workers AI 호출, 필요할 때 실행하는 크롤러
- Supabase: PostgreSQL 데이터베이스
- Qdrant Cloud: RAG 문서와 벡터
- Cloudflare Workers AI: Qwen 채팅 응답과 BGE-M3 임베딩

Cloud Run의 파일시스템은 일시적입니다. 인스턴스가 교체되면 실행 중에 기록한 파일이 사라질 수 있습니다. 따라서 PostgreSQL 데이터와 벡터 데이터는 컨테이너 내부에 저장하면 안 됩니다.

## 1. 관리형 서비스 준비

1. Google Cloud 프로젝트를 만들고 결제 계정을 연결합니다.
2. 서울 리전(`asia-northeast3`)을 선택합니다.
3. Cloud Run, Cloud Build, Artifact Registry, Secret Manager API를 사용 설정합니다.
4. 서울 리전에 `knu-campus`라는 Docker Artifact Registry 저장소를 만듭니다.
5. Supabase 프로젝트를 만들고 **Session Pooler** 연결 문자열을 복사합니다.
6. Qdrant Cloud 무료 클러스터를 만들고 API 키를 발급받습니다.

SQLAlchemy에는 TLS를 사용하는 Supabase Session Pooler URL을 지정합니다. 최종 URL은 다음과 같은 형식입니다.

```text
postgresql://postgres.PROJECT_REF:ENCODED_PASSWORD@POOLER_HOST:5432/postgres?sslmode=require
```

비밀번호에 `@`, `:`, `/`, `?`, `#`가 포함되어 있다면 URL 인코딩합니다.

## 2. 로컬 설정 준비

`.env.cloudrun.example`을 `.env.cloudrun`으로 복사하고 실제 값을 입력합니다. 실제 설정 파일은 Git 추적 대상에서 제외되어 있으므로 커밋하지 마세요.

필수 설정값은 다음과 같습니다.

- `DATABASE_URL`
- `SECRET_KEY`
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`
- `QDRANT_URL`
- `QDRANT_API_KEY`

다음 배포 설정값은 변경하지 않습니다.

```text
VECTOR_STORE_PROVIDER=qdrant
LLM_PROVIDER=cloudflare
EMBEDDING_PROVIDER=cloudflare
CLOUDFLARE_CHAT_MODEL=@cf/qwen/qwen3-30b-a3b-fp8
CLOUDFLARE_EMBEDDING_MODEL=@cf/baai/bge-m3
QDRANT_COLLECTION=knu-campus-bge-m3
```

### SECRET_KEY 생성

`SECRET_KEY`는 access token, refresh token, 친구 초대 JWT의 서명과 검증에
사용되는 서버 전용 비밀값입니다. 사람이 직접 정한 문자열을 사용하지 말고,
배포 전에 터미널에서 한 번만 무작위 값을 생성합니다.

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

생성된 값은 로컬 개발이나 migration 실행에 필요할 때만 `.env.cloudrun`에
입력합니다. `.env.cloudrun`은 Git에 커밋하지 않으며, 실제 운영 서비스에는
파일을 업로드하지 않고 아래 6단계의 Secret Manager 값을 연결합니다.

키를 배포할 때마다 새로 생성하지 마세요. 키를 바꾸면 기존 access token,
refresh token, 친구 초대 링크가 모두 무효화되어 사용자가 다시 로그인해야
합니다. 유출이 의심될 때만 새 키를 생성해 교체합니다.

## 3. 기존 PostgreSQL 데이터 이전

Render에서 애플리케이션의 `public` 스키마만 포함하는 덤프를 만듭니다.

```bash
pg_dump "$RENDER_DATABASE_URL" --schema=public --format=custom --no-owner --no-acl --file=render-public.dump
```

덤프를 새 Supabase 데이터베이스에 복원합니다.

```bash
pg_restore --dbname="$SUPABASE_DATABASE_URL" --no-owner --no-acl render-public.dump
```

복원 후 Supabase를 대상으로 `alembic upgrade head`를 실행합니다. 최종 검증이 끝날 때까지 Render를 계속 운영합니다.

## 4. Chroma 문서를 Qdrant로 이전

업데이트된 로컬 의존성을 설치한 뒤 `backend` 디렉터리에서 다음 명령을 실행합니다.

```bash
python scripts/migrate_chroma_to_qdrant.py
```

이 스크립트는 `backend/chroma_db`를 읽고, `.env.cloudrun`에 설정된 Workers AI 임베딩 모델을 사용하며, 고정된 ID로 문서를 추가하거나 갱신합니다. 다시 실행해도 컬렉션 전체를 삭제하지 않고 같은 문서를 갱신합니다.

## 5. Cloud Run 이미지 빌드

`gcloud`에 로그인하고 프로젝트를 선택한 뒤 `backend` 디렉터리에서 다음 명령을 실행합니다.

```bash
gcloud builds submit --config deploy/cloudrun/cloudbuild.yaml .
```

생성되는 이미지 주소는 다음과 같습니다.

```text
asia-northeast3-docker.pkg.dev/PROJECT_ID/knu-campus/knu-campus-api:latest
```

## 6. 비밀값 저장

Google Cloud Secret Manager에 다음 비밀값을 만듭니다. 실제 값은 소스 코드,
`.env.cloudrun.example`, 로그에 기록하지 않습니다.

- `knu-database-url`
- `knu-secret-key`
- `knu-cloudflare-api-token`
- `knu-qdrant-api-key`

서버에서 인증이 필요한 크롤링을 실행한다면 `knu-user-id`와 `knu-password`도 선택적으로 만듭니다.

Cloud Run 실행 서비스 계정에는 필요한 비밀값에 대해서만 `Secret Manager Secret Accessor` 권한을 부여합니다.

### `knu-secret-key` 생성 및 저장

처음 한 번만 Secret Manager 항목을 생성합니다.

```bash
gcloud secrets create knu-secret-key \
  --replication-policy="automatic"
```

이미 항목이 있으면 `create`를 다시 실행하지 않습니다. 터미널에서 생성한
무작위 값을 바로 새 버전으로 저장할 수도 있습니다.

```bash
python -c "import secrets; print(secrets.token_urlsafe(64), end='')" \
  | gcloud secrets versions add knu-secret-key --data-file=-
```

또는 Google Cloud Console에서 `knu-secret-key`를 만든 뒤 생성된 값을 직접
붙여 넣습니다. Cloud Run 실행 서비스 계정에는 다음 권한이 필요합니다.

```text
roles/secretmanager.secretAccessor
```

실제 서비스 계정에 권한을 부여한 뒤 Cloud Run 서비스의 환경변수 연결에서
다음처럼 설정합니다.

```text
SECRET_KEY=knu-secret-key:latest
```

이 설정은 `SECRET_KEY`에 문자열 `knu-secret-key`를 넣는 것이 아니라,
Secret Manager의 최신 버전 값을 Cloud Run 컨테이너의 `SECRET_KEY` 환경변수로
주입한다는 뜻입니다. Cloud Run 콘솔의 **서비스 수정 → 변수 및 보안 비밀 →
보안 비밀 참조**에서 연결하거나 다음 명령을 사용할 수 있습니다.

```bash
gcloud run services update knu-campus-api \
  --region=asia-northeast3 \
  --update-secrets=SECRET_KEY=knu-secret-key:latest
```

키를 교체할 때는 새 버전을 추가한 뒤 새 Cloud Run revision을 배포합니다.
교체 직후 기존 사용자는 다시 로그인해야 합니다.

## 7. 데이터베이스 마이그레이션 실행

같은 이미지로 일회성 Cloud Run Job을 만듭니다. 실행 명령은 다음과 같이 설정합니다.

```text
alembic
```

인수는 다음과 같이 설정합니다.

```text
upgrade,head
```

`knu-database-url` 비밀값을 `DATABASE_URL`에 연결하고 Job을 한 번 실행합니다. 성공 여부를 확인한 뒤 웹 서비스를 배포합니다.

## 8. 웹 서비스 배포

Cloud Run에서 다음 값을 사용합니다.

- 서비스 이름: `knu-campus-api`
- 리전: `asia-northeast3`(서울)
- 인증: 인증되지 않은 호출 허용
- CPU: 1
- 메모리: 2 GiB
- 최소 인스턴스: 0
- 최대 인스턴스: 1
- 동시 요청 수: 20
- 요청 제한 시간: 300초
- 컨테이너 포트: 8080

다음 일반 환경변수를 설정합니다.

```text
VECTOR_STORE_PROVIDER=qdrant
LLM_PROVIDER=cloudflare
EMBEDDING_PROVIDER=cloudflare
CLOUDFLARE_ACCOUNT_ID=<Cloudflare 계정 ID>
CLOUDFLARE_CHAT_MODEL=@cf/qwen/qwen3-30b-a3b-fp8
CLOUDFLARE_EMBEDDING_MODEL=@cf/baai/bge-m3
QDRANT_COLLECTION=knu-campus-bge-m3
QDRANT_URL=<Qdrant 클러스터 URL>
APP_SCHEME=knu
```

다음 비밀값을 환경변수에 연결합니다.

```text
DATABASE_URL=knu-database-url:latest
SECRET_KEY=knu-secret-key:latest
CLOUDFLARE_API_TOKEN=knu-cloudflare-api-token:latest
QDRANT_API_KEY=knu-qdrant-api-key:latest
```

## 일일 크롤러와 알림

API 이미지로 일일 크롤러용 Cloud Run Job을 만듭니다. 실행 명령을 `python`, 인수를 `scripts/run_daily_crawlers.py`로 설정합니다. API 서비스와 동일한 데이터베이스, AI, 크롤러 비밀값을 제공합니다.

Cloud Scheduler는 관리자 전용 `/crawl` API 경로를 호출하는 대신 이 Job을 실행해야 합니다. Job은 공지사항, 식단, 셔틀 크롤러를 순서대로 실행합니다. 새 데이터나 변경된 데이터가 있을 때만 푸시 알림을 보내므로 변경이 없는 실행에서는 알림을 보내지 않습니다. Scheduler 서비스 계정에는 이 Job을 실행할 권한만 부여합니다.

## 관리자 웹의 공지 수집 버튼

관리자 웹의 공지 수집 버튼은 `POST /api/notices/crawl`을 호출합니다. API 서비스가 관리자 권한을 확인한 뒤 **공지 전용 Cloud Run Job**의 실행을 요청합니다. 이 요청의 성공은 Job이 시작되었다는 뜻이며, 공지 수집 완료를 뜻하지 않습니다. 완료 여부와 오류는 Cloud Run Job 실행 내역 및 로그에서 확인합니다. Vercel에는 Google Cloud 인증 정보를 넣지 않습니다.

1. API 이미지로 공지 전용 Cloud Run Job을 만듭니다. 명령은 `python`, 인수는 `scripts/run_notice_crawler.py`입니다. 일일 크롤러 Job과 동일하게 데이터베이스, AI, Qdrant 환경변수와 비밀값을 설정합니다. 이 Job에는 Cloud Scheduler를 연결하지 않습니다.
2. API **서비스**의 실행 서비스 계정에 공지 전용 Job에 대한 `Cloud Run Invoker`(`roles/run.invoker`) 권한을 부여합니다. 일일 크롤러 Job이나 프로젝트 전체에 권한을 줄 필요는 없습니다.
3. API 서비스에 아래 일반 환경변수를 설정하고 새 버전을 배포합니다. `NOTICE_CRAWLER_JOB`에는 1단계에서 만든 Job의 실제 이름을 입력합니다.

   ```text
   GCP_PROJECT_ID=실제_프로젝트_ID
   GCP_REGION=asia-northeast3
   NOTICE_CRAWLER_JOB=notice-crawler
   ```

4. 관리자 웹에서 버튼을 눌러 시작 메시지가 표시되는지 확인하고, Cloud Run에서 해당 Job의 실행 및 로그를 확인합니다. API 서비스가 Google Cloud 안에서 실행되어야 서비스 계정의 액세스 토큰을 받을 수 있습니다.

## Supabase 학칙·규정 적재

AI 챗봇은 학칙·규정 조항을 PostgreSQL에서 직접 읽습니다. 이 데이터는 Qdrant 인덱스 및 일일 공지사항·식단·셔틀 크롤러와 별도로 관리합니다. 대학의 공개 규정 페이지는 크롤러용 로그인 정보가 필요하지 않습니다.

1. 위 5단계에 따라 업데이트된 `Dockerfile.cloudrun` 이미지를 빌드합니다.
2. 해당 이미지에서 `alembic upgrade head` Cloud Run Job을 실행해 Supabase에 `regulation_articles` 테이블을 만듭니다.
3. 같은 이미지로 일회성 Cloud Run Job을 만듭니다. 실행 명령은 `python`이고, 인수는 아래의 세 값을 순서대로 각각 입력합니다. 모듈 이름은 `app.crawlers.rules_crawler`이며 `app.crawlers.rules.crawler`가 아닙니다. Secret Manager의 `knu-database-url`만 `DATABASE_URL`에 연결합니다. Job을 실행해 규정 수, 조항 수, 현재 데이터베이스 크기, 보수적으로 계산한 추가 저장량을 확인합니다. 시험 실행에서는 DB 데이터를 변경하지 않습니다.

   ```text
   -m
   app.crawlers.rules_crawler
   --dry-run
   ```

4. 시험 실행에 성공하면 Job 인수에서 `--dry-run`을 제거하고 한 번 실행합니다. 이 Job은 고정된 출처 키를 기준으로 조항을 추가하거나 갱신합니다. 대학의 규정이 개정되면 다시 실행할 수 있으며, 매일 실행하는 Scheduler 설정은 필요하지 않습니다.
5. 업데이트된 API 이미지를 배포해 `ai_chat`이 새 테이블을 읽도록 합니다. "졸업에 관한 학칙 알려줘"라고 질문하고 Cloud Run 로그에 `Supabase 학칙·규정 Context 추가`가 기록되는지 확인합니다.

Supabase 무료 플랜에는 데이터베이스 용량 500 MB가 포함됩니다. 크롤러는 저장 전에 `pg_database_size(current_database())`로 확인한 현재 사용량에, 수집한 UTF-8 본문 크기의 4배를 더해 예상 용량을 계산합니다. 보수적으로 설정한 450 MB 안전선에 도달할 것으로 예상되면 적재를 중단합니다. 트랜잭션의 변경 사항을 반영한 뒤에도 용량을 다시 검사하며, 안전선에 도달했다면 롤백합니다. 시험 실행에서 안전선 이상으로 표시된다면 실제 저장 Job을 실행하지 마세요.

## 9. 트래픽 전환 전 검증

생성된 Cloud Run URL에서 다음 경로를 확인합니다.

```text
/health
/health/db
/docs
/api/ai/chat/demo
```

로그인, 커뮤니티 신고와 차단, AI 채팅 내역, 공지사항, 식단, 셔틀 데이터도 확인합니다. 모든 검증을 통과한 뒤에만 모바일 앱의 운영 API URL을 변경합니다.

## 현재 파일시스템 제약

기존 셔틀 PDF 정적 파일은 이미지에 포함되어 있습니다. 새로 크롤링한 셔틀 PDF는 Cloud Run의 일시적 파일시스템에 기록되므로 인스턴스가 재시작되면 사라질 수 있습니다. 운영 환경에서 서버 측 셔틀 크롤러에 의존하기 전에 새 PDF 업로드 대상을 Google Cloud Storage로 옮기세요.

## 학사일정 동기화

다음 명령으로 공식 학부 학사일정 페이지의 내용을 설정된 Qdrant 컬렉션에 동기화할 수 있습니다.

```text
python scripts/sync_academic_calendar.py
```

이 Job은 화면에 표시된 모든 월별 표를 크롤링하고, 연도를 넘어가는 날짜 범위를 변환한 뒤, 고정된 ID로 각 일정을 추가하거나 갱신합니다. 성공적으로 반영한 후에는 `metadata.source`가 `학사일정`인 오래된 Qdrant 문서를 제거합니다. 따라서 여러 번 실행해도 같은 일정이 중복으로 생성되지 않습니다.

운영 환경에서는 같은 컨테이너 이미지로 다음 Cloud Run Job을 만듭니다.

```text
command: python
arguments: scripts/sync_academic_calendar.py
```

API 서비스와 동일한 Cloudflare 임베딩 및 Qdrant 환경변수와 비밀값을 Job에 제공합니다. Cloud Scheduler에서 `Asia/Seoul` 시간대로 매주 실행하고, 대학에서 학사일정 개정을 발표한 뒤에도 수동으로 실행합니다.

Qdrant에 저장하지 않고 파싱 결과만 확인하려면 다음 명령을 실행합니다.

```text
python scripts/sync_academic_calendar.py --dry-run
```
