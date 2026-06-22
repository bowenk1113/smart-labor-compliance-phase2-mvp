from conftest import assert_ok  # 导入当前模块运行所依赖的工具或类型


def test_request_body_size_limit_and_security_headers(client, api_base_url):  # 定义业务处理函数 test_request_body_size_limit_and_security_headers
    response = client.post(  # 保存当前分支生成的响应对象
        f"{api_base_url}/api/chat",  # 设置 post 的 字段
        data="x" * 9000,  # 设置 post 的 data
        headers={"Content-Type": "application/json", "X-Tenant-Code": "demo-sx"},  # 设置 post 的 Content-Type
        timeout=10,  # 设置 post 的 timeout
    )  # 结束 post 的定义或组装
    assert response.status_code == 413  # 执行当前业务步骤并推进后续处理
    assert response.json()["detail"] == "请求体过大"  # 执行当前业务步骤并推进后续处理

    health = client.get(f"{api_base_url}/health", timeout=10)  # 更新当前逻辑中的 health
    assert health.headers["X-Content-Type-Options"] == "nosniff"  # 执行当前业务步骤并推进后续处理
    assert health.headers["X-Frame-Options"] == "DENY"  # 执行当前业务步骤并推进后续处理
    assert health.headers["Referrer-Policy"] == "no-referrer"  # 执行当前业务步骤并推进后续处理
    assert health.headers["Cache-Control"] == "no-store"  # 执行当前业务步骤并推进后续处理


def test_service_status_hides_secret_values(client, api_base_url, super_headers):  # 定义业务处理函数 test_service_status_hides_secret_values
    payload = assert_ok(client.get(f"{api_base_url}/api/admin/service-status", headers=super_headers, timeout=10))  # 组装发往外部问答服务的请求载荷
    data = payload["data"]  # 整理当前接口最终要返回的数据结构
    assert data["database"]["name"].endswith("auto_test")  # 执行当前业务步骤并推进后续处理
    rendered = str(data)  # 更新当前逻辑中的 rendered
    assert "Admin@123456" not in rendered  # 执行当前业务步骤并推进后续处理
    assert "Tenant@123456" not in rendered  # 执行当前业务步骤并推进后续处理
    assert "dify_api_key" not in rendered.lower()  # 执行当前业务步骤并推进后续处理


def test_stop_generation_without_registered_task_is_safe(client, api_base_url):  # 定义业务处理函数 test_stop_generation_without_registered_task_is_safe
    payload = assert_ok(  # 组装发往外部问答服务的请求载荷
        client.post(  # 设置 assert_ok 的 字段
            f"{api_base_url}/api/chat/stop",  # 设置 assert_ok 的 字段
            json={"generation_id": "not-registered", "tenant_code": "demo-sx"},  # 设置 assert_ok 的 generation id
            timeout=10,  # 设置 assert_ok 的 timeout
        )  # 结束 assert_ok 的定义或组装
    )  # 结束 assert_ok 的定义或组装
    assert payload["data"]["stopped"] is False  # 执行当前业务步骤并推进后续处理

