# Google Cloud Run deployment

This deployment keeps the FastAPI application on Cloud Run, stores relational
data in Supabase PostgreSQL, and stores RAG vectors in Qdrant Cloud.

## Target layout

- Cloud Run: FastAPI, Workers AI calls, and on-demand crawlers
- Supabase: PostgreSQL
- Qdrant Cloud: RAG documents and vectors
- Cloudflare Workers AI: Qwen chat completion and BGE-M3 embeddings

Cloud Run has an ephemeral filesystem. Files written after startup can disappear
when an instance is replaced. PostgreSQL and vector data therefore must not be
stored in the container.

## 1. Create the managed services

1. Create a Google Cloud project and attach a billing account.
2. Select the Seoul region (`asia-northeast3`).
3. Enable Cloud Run, Cloud Build, Artifact Registry, and Secret Manager APIs.
4. Create a Docker Artifact Registry repository named `knu-campus` in Seoul.
5. Create a Supabase project and copy its **Session Pooler** connection string.
6. Create a Qdrant Cloud free cluster and create an API key.

For SQLAlchemy, use the Supabase Session Pooler URL with TLS enabled. The final
URL should resemble:

```text
postgresql://postgres.PROJECT_REF:ENCODED_PASSWORD@POOLER_HOST:5432/postgres?sslmode=require
```

If the password contains `@`, `:`, `/`, `?`, or `#`, URL-encode it.

## 2. Prepare local configuration

Copy `.env.cloudrun.example` to `.env.cloudrun` and fill in the real values.
The real file is ignored by Git. Never commit it.

Required values:

- `DATABASE_URL`
- `SECRET_KEY`
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`
- `QDRANT_URL`
- `QDRANT_API_KEY`

Keep these deployment values unchanged:

```text
VECTOR_STORE_PROVIDER=qdrant
LLM_PROVIDER=cloudflare
EMBEDDING_PROVIDER=cloudflare
CLOUDFLARE_CHAT_MODEL=@cf/qwen/qwen3-30b-a3b-fp8
CLOUDFLARE_EMBEDDING_MODEL=@cf/baai/bge-m3
QDRANT_COLLECTION=knu-campus-bge-m3
```

## 3. Move the existing PostgreSQL data

Create a dump from Render that contains only the application's `public` schema:

```bash
pg_dump "$RENDER_DATABASE_URL" --schema=public --format=custom --no-owner --no-acl --file=render-public.dump
```

Restore it into the new Supabase database:

```bash
pg_restore --dbname="$SUPABASE_DATABASE_URL" --no-owner --no-acl render-public.dump
```

Run `alembic upgrade head` against Supabase after the restore. Keep Render online
until the final verification is complete.

## 4. Move Chroma documents to Qdrant

Install the updated local requirements, then run from the `backend` directory:

```bash
python scripts/migrate_chroma_to_qdrant.py
```

The script reads `backend/chroma_db`, uses the Workers AI embedding model configured
in `.env.cloudrun`, and upserts the documents with deterministic IDs. Running it
again updates the same points instead of intentionally deleting the collection.

## 5. Build the Cloud Run image

Authenticate `gcloud`, select the project, and run from `backend`:

```bash
gcloud builds submit --config deploy/cloudrun/cloudbuild.yaml .
```

The resulting image is:

```text
asia-northeast3-docker.pkg.dev/PROJECT_ID/knu-campus/knu-campus-api:latest
```

## 6. Store secrets

Create these secrets in Google Cloud Secret Manager. Paste each value through the
Console so it does not become part of source control:

- `knu-database-url`
- `knu-secret-key`
- `knu-cloudflare-api-token`
- `knu-qdrant-api-key`

Optionally create `knu-user-id` and `knu-password` when server-side crawling is
needed.

Grant the Cloud Run runtime service account `Secret Manager Secret Accessor` for
only these secrets.

## 7. Run database migrations

Create a one-off Cloud Run Job from the same image. Configure the command as:

```text
alembic
```

and the arguments as:

```text
upgrade,head
```

Map the `knu-database-url` secret to `DATABASE_URL`, execute the job once, and
confirm that it succeeds before deploying the web service.

## 8. Deploy the web service

Use these Cloud Run settings:

- Service name: `knu-campus-api`
- Region: `asia-northeast3` (Seoul)
- Authentication: Allow unauthenticated invocations
- CPU: 1
- Memory: 2 GiB
- Minimum instances: 0
- Maximum instances: 1
- Concurrency: 20
- Request timeout: 300 seconds
- Container port: 8080

Set these ordinary environment variables:

```text
VECTOR_STORE_PROVIDER=qdrant
LLM_PROVIDER=cloudflare
EMBEDDING_PROVIDER=cloudflare
CLOUDFLARE_ACCOUNT_ID=your Cloudflare account ID
CLOUDFLARE_CHAT_MODEL=@cf/qwen/qwen3-30b-a3b-fp8
CLOUDFLARE_EMBEDDING_MODEL=@cf/baai/bge-m3
QDRANT_COLLECTION=knu-campus-bge-m3
QDRANT_URL=your Qdrant cluster URL
APP_SCHEME=knu
```

Map secrets to these environment variables:

```text
DATABASE_URL=knu-database-url:latest
SECRET_KEY=knu-secret-key:latest
CLOUDFLARE_API_TOKEN=knu-cloudflare-api-token:latest
QDRANT_API_KEY=knu-qdrant-api-key:latest
```

## Daily crawler notifications

Create a Cloud Run Job from the API image for the daily crawlers. Set its command
to `python` and its arguments to `scripts/run_daily_crawlers.py`, then give the
job the same database, AI, and crawler secrets as the API service.

Cloud Scheduler should execute this Job, rather than call the administrator-only
`/crawl` API routes. The Job runs the notice, menu, and shuttle crawlers in
sequence. A push notification is sent only when a crawler finds and saves new
or changed data, preventing notifications for runs with no updates. Give the
Scheduler service account permission to execute only this Job.

## 9. Verify before switching traffic

Check these endpoints on the generated Cloud Run URL:

```text
/health
/health/db
/docs
/api/ai/chat/demo
```

Then verify login, community reports and blocks, AI chat history, notices, menus,
and shuttle data. Only update the mobile application's production API URL after
all checks pass.

## Current filesystem limitation

Existing static shuttle PDFs are included in the image. A newly crawled shuttle
PDF is written to Cloud Run's ephemeral filesystem and can disappear after a
restart. Move new PDF uploads to Google Cloud Storage before relying on the
server-side shuttle crawler in production.

## Academic calendar synchronization

The official undergraduate academic-calendar page can be synchronized to the
configured Qdrant collection with:

```text
python scripts/sync_academic_calendar.py
```

The job crawls every displayed monthly table, converts ranges that cross a year
boundary, and upserts every event with a deterministic ID. After a successful
upsert it removes obsolete Qdrant points whose `metadata.source` is `학사일정`.
Repeated executions therefore do not create duplicates.

For production, create a Cloud Run Job from the same container image with:

```text
command: python
arguments: scripts/sync_academic_calendar.py
```

Give the job the same Cloudflare embedding and Qdrant environment variables and
secrets as the API service. Trigger it weekly with Cloud Scheduler using the
`Asia/Seoul` time zone, and also run it manually after the university announces
an academic-calendar revision.

To validate parsing without writing to Qdrant, run:

```text
python scripts/sync_academic_calendar.py --dry-run
```
