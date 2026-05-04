import csv
import io

from conftest import assert_ok, unique


def test_health_root_and_public_tenant_contract(client, api_base_url):
    health = assert_ok(client.get(f"{api_base_url}/health", timeout=10))
    assert health["data"]["status"] == "healthy"
    assert health["data"]["database"].endswith("auto_test")
    assert client.get(f"{api_base_url}/health", timeout=10).headers["X-Frame-Options"] == "DENY"

    root = assert_ok(client.get(f"{api_base_url}/", timeout=10))
    assert root["data"]["docs"] == "/docs"

    tenant = assert_ok(client.get(f"{api_base_url}/api/tenant-public", timeout=10))
    assert tenant["data"]["code"] == "demo-sx"


def test_chat_rejects_blank_and_overlong_questions(client, api_base_url):
    blank = client.post(f"{api_base_url}/api/chat", json={"question": "   "}, timeout=10)
    assert blank.status_code == 400
    assert blank.json()["success"] is False

    overlong = client.post(f"{api_base_url}/api/chat", json={"question": "x" * 3001}, timeout=10)
    assert overlong.status_code == 422


def test_chat_sanitizes_sensitive_data_and_persists_history(client, api_base_url):
    user_id = unique("history-user")
    raw_id_card = "610103199001011234"
    raw_phone = "13812345678"
    raw_email = "hr@example.com"
    question = f"员工身份证号 {raw_id_card} 手机号 {raw_phone} 邮箱 {raw_email} 可以直接进入知识库吗？"

    payload = assert_ok(
        client.post(
            f"{api_base_url}/api/chat",
            json={"question": question, "user_id": user_id, "user_role": "enterprise_hr"},
            timeout=20,
        )
    )
    data = payload["data"]
    assert data["question_id"]
    assert data["provider"] in {"local_faq", "knowledge_package_disabled", "dify_unavailable"}
    assert "适用角色：企业HR" in data["answer"]

    history = assert_ok(client.get(f"{api_base_url}/api/history", params={"user_id": user_id}, timeout=10))
    assert history["data"]["total"] == 1
    stored_question = history["data"]["list"][0]["question"]
    assert raw_id_card not in stored_question
    assert raw_phone not in stored_question
    assert raw_email not in stored_question
    assert "[身份证号已脱敏]" in stored_question
    assert "[手机号已脱敏]" in stored_question
    assert "[邮箱已脱敏]" in stored_question


def test_history_filters_export_invalid_ids_and_clear(client, api_base_url):
    user_id = unique("export-user")
    for question in ["陕西产假多少天？", "西安劳动仲裁去哪里申请？"]:
        assert_ok(client.post(f"{api_base_url}/api/chat", json={"question": question, "user_id": user_id}, timeout=20))

    filtered = assert_ok(
        client.get(
            f"{api_base_url}/api/history",
            params={"user_id": user_id, "keyword": "仲裁", "page": -1, "page_size": 500},
            timeout=10,
        )
    )
    assert filtered["data"]["page"] == 1
    assert filtered["data"]["page_size"] == 100
    assert filtered["data"]["total"] == 1

    invalid = client.get(f"{api_base_url}/api/history/export", params={"user_id": user_id, "ids": "abc"}, timeout=10)
    assert invalid.status_code == 400

    exported = client.get(f"{api_base_url}/api/history/export", params={"user_id": user_id}, timeout=10)
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/csv")
    rows = list(csv.DictReader(io.StringIO(exported.content.decode("utf-8-sig"))))
    assert len(rows) == 2
    assert {"question", "answer", "provider", "risk_level"}.issubset(rows[0].keys())

    cleared = assert_ok(client.delete(f"{api_base_url}/api/history", params={"user_id": user_id}, timeout=10))
    assert cleared["message"] == "历史记录已清空"
    after_clear = assert_ok(client.get(f"{api_base_url}/api/history", params={"user_id": user_id}, timeout=10))
    assert after_clear["data"]["total"] == 0


def test_recommended_questions_are_seeded_and_tenant_scoped(client, api_base_url):
    payload = assert_ok(client.get(f"{api_base_url}/api/recommended-questions", timeout=10))
    assert len(payload["data"]) >= 4
    assert all("question" in item and "category" in item for item in payload["data"])

    missing = client.get(
        f"{api_base_url}/api/recommended-questions",
        headers={"X-Tenant-Code": "missing-tenant"},
        timeout=10,
    )
    assert missing.status_code == 404
