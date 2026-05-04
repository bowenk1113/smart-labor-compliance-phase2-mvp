from conftest import assert_ok


def test_request_body_size_limit_and_security_headers(client, api_base_url):
    response = client.post(
        f"{api_base_url}/api/chat",
        data="x" * 9000,
        headers={"Content-Type": "application/json", "X-Tenant-Code": "demo-sx"},
        timeout=10,
    )
    assert response.status_code == 413
    assert response.json()["detail"] == "请求体过大"

    health = client.get(f"{api_base_url}/health", timeout=10)
    assert health.headers["X-Content-Type-Options"] == "nosniff"
    assert health.headers["X-Frame-Options"] == "DENY"
    assert health.headers["Referrer-Policy"] == "no-referrer"
    assert health.headers["Cache-Control"] == "no-store"


def test_service_status_hides_secret_values(client, api_base_url, super_headers):
    payload = assert_ok(client.get(f"{api_base_url}/api/admin/service-status", headers=super_headers, timeout=10))
    data = payload["data"]
    assert data["database"]["name"].endswith("auto_test")
    rendered = str(data)
    assert "Admin@123456" not in rendered
    assert "Tenant@123456" not in rendered
    assert "dify_api_key" not in rendered.lower()


def test_stop_generation_without_registered_task_is_safe(client, api_base_url):
    payload = assert_ok(
        client.post(
            f"{api_base_url}/api/chat/stop",
            json={"generation_id": "not-registered", "tenant_code": "demo-sx"},
            timeout=10,
        )
    )
    assert payload["data"]["stopped"] is False

