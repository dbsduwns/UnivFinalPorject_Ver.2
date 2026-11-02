from unittest.mock import MagicMock, Mock, patch

import httpx
import pytest

from app.routers.notice import crawl_notices
from app.services.cloud_run_jobs import JobConfigurationError, start_notice_crawler_job


def test_notice_job_uses_service_identity_and_configured_target(monkeypatch):
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
    monkeypatch.setenv("GCP_REGION", "asia-northeast3")
    monkeypatch.setenv("NOTICE_CRAWLER_JOB", "notice-crawler")

    token_response = Mock()
    token_response.json.return_value = {"access_token": "test-token"}
    token_response.raise_for_status.return_value = None
    run_response = Mock(status_code=200)
    run_response.json.return_value = {"name": "operations/test"}
    run_response.raise_for_status.return_value = None
    client = MagicMock()
    client.get.return_value = token_response
    client.post.return_value = run_response
    client.__enter__.return_value = client
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: client)

    assert start_notice_crawler_job() == "operations/test"
    assert client.get.call_args.kwargs["headers"] == {"Metadata-Flavor": "Google"}
    assert client.post.call_args.args[0] == (
        "https://run.googleapis.com/v2/projects/test-project/locations/asia-northeast3/jobs/notice-crawler:run"
    )
    assert client.post.call_args.kwargs["headers"] == {"Authorization": "Bearer test-token"}
    assert client.post.call_args.kwargs["json"] == {}


def test_missing_job_configuration_does_not_call_google(monkeypatch):
    monkeypatch.delenv("NOTICE_CRAWLER_JOB", raising=False)
    with pytest.raises(JobConfigurationError):
        start_notice_crawler_job()


def test_notice_route_reports_job_start_without_claiming_completion():
    with patch("app.routers.notice.start_notice_crawler_job", return_value="operations/test"):
        response = crawl_notices(current_admin=Mock())

    assert response["status"] == "started"
    assert response["operation"] == "operations/test"
    assert "count" not in response
