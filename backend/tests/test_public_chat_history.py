import csv  # 导入 CSV 读写工具，供导入导出接口复用
import io  # 导入内存流工具，便于处理上传与下载内容

from conftest import assert_ok, unique  # 导入当前模块运行所依赖的工具或类型


def test_health_root_and_public_tenant_contract(client, api_base_url):  # 定义业务处理函数 test_health_root_and_public_tenant_contract
    health = assert_ok(client.get(f"{api_base_url}/health", timeout=10))  # 更新当前逻辑中的 health
    assert health["data"]["status"] == "healthy"  # 执行当前业务步骤并推进后续处理
    assert health["data"]["database"].endswith("auto_test")  # 执行当前业务步骤并推进后续处理
    assert client.get(f"{api_base_url}/health", timeout=10).headers["X-Frame-Options"] == "DENY"  # 执行当前业务步骤并推进后续处理

    root = assert_ok(client.get(f"{api_base_url}/", timeout=10))  # 更新当前逻辑中的 root
    assert root["data"]["docs"] == "/docs"  # 执行当前业务步骤并推进后续处理

    tenant = assert_ok(client.get(f"{api_base_url}/api/tenant-public", timeout=10))  # 保存当前请求实际使用的租户对象
    assert tenant["data"]["code"] == "demo-sx"  # 执行当前业务步骤并推进后续处理


def test_chat_rejects_blank_and_overlong_questions(client, api_base_url):  # 定义业务处理函数 test_chat_rejects_blank_and_overlong_questions
    blank = client.post(f"{api_base_url}/api/chat", json={"question": "   "}, timeout=10)  # 更新当前逻辑中的 blank
    assert blank.status_code == 400  # 执行当前业务步骤并推进后续处理
    assert blank.json()["success"] is False  # 执行当前业务步骤并推进后续处理

    overlong = client.post(f"{api_base_url}/api/chat", json={"question": "x" * 3001}, timeout=10)  # 更新当前逻辑中的 overlong
    assert overlong.status_code == 422  # 执行当前业务步骤并推进后续处理


def test_chat_sanitizes_sensitive_data_and_persists_history(client, api_base_url):  # 定义业务处理函数 test_chat_sanitizes_sensitive_data_and_persists_history
    user_id = unique("history-user")  # 规范化本次问答对应的用户标识
    raw_id_card = "610103199001011234"  # 更新当前逻辑中的 raw id card
    raw_phone = "13812345678"  # 更新当前逻辑中的 raw phone
    raw_email = "hr@example.com"  # 更新当前逻辑中的 raw email
    question = f"员工身份证号 {raw_id_card} 手机号 {raw_phone} 邮箱 {raw_email} 可以直接进入知识库吗？"  # 清洗并保存用户提交的问题文本

    payload = assert_ok(  # 组装发往外部问答服务的请求载荷
        client.post(  # 设置 assert_ok 的 字段
            f"{api_base_url}/api/chat",  # 设置 assert_ok 的 字段
            json={"question": question, "user_id": user_id, "user_role": "enterprise_hr"},  # 设置 assert_ok 的 问题内容
            timeout=20,  # 设置 assert_ok 的 timeout
        )  # 结束 assert_ok 的定义或组装
    )  # 结束 assert_ok 的定义或组装
    data = payload["data"]  # 整理当前接口最终要返回的数据结构
    assert data["question_id"]  # 执行当前业务步骤并推进后续处理
    assert data["provider"] in {"local_faq", "knowledge_package_disabled", "dify_unavailable"}  # 执行当前业务步骤并推进后续处理
    assert "适用角色：企业HR" in data["answer"]  # 执行当前业务步骤并推进后续处理

    history = assert_ok(client.get(f"{api_base_url}/api/history", params={"user_id": user_id}, timeout=10))  # 更新当前逻辑中的 历史上下文
    assert history["data"]["total"] == 1  # 执行当前业务步骤并推进后续处理
    stored_question = history["data"]["list"][0]["question"]  # 更新当前逻辑中的 stored question
    assert raw_id_card not in stored_question  # 执行当前业务步骤并推进后续处理
    assert raw_phone not in stored_question  # 执行当前业务步骤并推进后续处理
    assert raw_email not in stored_question  # 执行当前业务步骤并推进后续处理
    assert "[身份证号已脱敏]" in stored_question  # 执行当前业务步骤并推进后续处理
    assert "[手机号已脱敏]" in stored_question  # 执行当前业务步骤并推进后续处理
    assert "[邮箱已脱敏]" in stored_question  # 执行当前业务步骤并推进后续处理


def test_history_filters_export_invalid_ids_and_clear(client, api_base_url):  # 定义业务处理函数 test_history_filters_export_invalid_ids_and_clear
    user_id = unique("export-user")  # 规范化本次问答对应的用户标识
    for question in ["陕西产假多少天？", "西安劳动仲裁去哪里申请？"]:  # 遍历当前集合中的每一项并逐个处理
        assert_ok(client.post(f"{api_base_url}/api/chat", json={"question": question, "user_id": user_id}, timeout=20))  # 执行当前业务步骤并推进后续处理

    filtered = assert_ok(  # 更新当前逻辑中的 filtered
        client.get(  # 设置 assert_ok 的 字段
            f"{api_base_url}/api/history",  # 设置 assert_ok 的 字段
            params={"user_id": user_id, "keyword": "仲裁", "page": -1, "page_size": 500},  # 设置 assert_ok 的 用户 ID
            timeout=10,  # 设置 assert_ok 的 timeout
        )  # 结束 assert_ok 的定义或组装
    )  # 结束 assert_ok 的定义或组装
    assert filtered["data"]["page"] == 1  # 执行当前业务步骤并推进后续处理
    assert filtered["data"]["page_size"] == 100  # 执行当前业务步骤并推进后续处理
    assert filtered["data"]["total"] == 1  # 执行当前业务步骤并推进后续处理

    invalid = client.get(f"{api_base_url}/api/history/export", params={"user_id": user_id, "ids": "abc"}, timeout=10)  # 更新当前逻辑中的 invalid
    assert invalid.status_code == 400  # 执行当前业务步骤并推进后续处理

    exported = client.get(f"{api_base_url}/api/history/export", params={"user_id": user_id}, timeout=10)  # 更新当前逻辑中的 exported
    assert exported.status_code == 200  # 执行当前业务步骤并推进后续处理
    assert exported.headers["content-type"].startswith("text/csv")  # 执行当前业务步骤并推进后续处理
    rows = list(csv.DictReader(io.StringIO(exported.content.decode("utf-8-sig"))))  # 更新当前逻辑中的 rows
    assert len(rows) == 2  # 执行当前业务步骤并推进后续处理
    assert {"question", "answer", "provider", "risk_level"}.issubset(rows[0].keys())  # 执行当前业务步骤并推进后续处理

    cleared = assert_ok(client.delete(f"{api_base_url}/api/history", params={"user_id": user_id}, timeout=10))  # 更新当前逻辑中的 cleared
    assert cleared["message"] == "历史记录已清空"  # 执行当前业务步骤并推进后续处理
    after_clear = assert_ok(client.get(f"{api_base_url}/api/history", params={"user_id": user_id}, timeout=10))  # 更新当前逻辑中的 after clear
    assert after_clear["data"]["total"] == 0  # 执行当前业务步骤并推进后续处理


def test_recommended_questions_are_seeded_and_tenant_scoped(client, api_base_url):  # 定义业务处理函数 test_recommended_questions_are_seeded_and_tenant_scoped
    payload = assert_ok(client.get(f"{api_base_url}/api/recommended-questions", timeout=10))  # 组装发往外部问答服务的请求载荷
    assert len(payload["data"]) >= 4  # 执行当前业务步骤并推进后续处理
    assert all("question" in item and "category" in item for item in payload["data"])  # 执行当前业务步骤并推进后续处理

    missing = client.get(  # 更新当前逻辑中的 missing
        f"{api_base_url}/api/recommended-questions",  # 设置 get 的 字段
        headers={"X-Tenant-Code": "missing-tenant"},  # 设置 get 的 X-Tenant-Code
        timeout=10,  # 设置 get 的 timeout
    )  # 结束 get 的定义或组装
    assert missing.status_code == 404  # 执行当前业务步骤并推进后续处理
