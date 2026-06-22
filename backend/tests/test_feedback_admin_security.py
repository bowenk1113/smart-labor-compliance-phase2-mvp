from conftest import assert_ok, unique  # 导入当前模块运行所依赖的工具或类型


def _create_chat(client, api_base_url, user_id):  # 定义业务处理函数 _create_chat
    payload = assert_ok(  # 组装发往外部问答服务的请求载荷
        client.post(  # 设置 assert_ok 的 字段
            f"{api_base_url}/api/chat",  # 设置 assert_ok 的 字段
            json={"question": "员工身份证号 610103199001011234 能否直接进入知识库？", "user_id": user_id},  # 设置 assert_ok 的 问题内容
            timeout=20,  # 设置 assert_ok 的 timeout
        )  # 结束 assert_ok 的定义或组装
    )  # 结束 assert_ok 的定义或组装
    return payload["data"]["question_id"]  # 返回当前分支整理好的结果


def test_feedback_lifecycle_and_remark_sanitization(client, api_base_url, tenant_headers):  # 定义业务处理函数 test_feedback_lifecycle_and_remark_sanitization
    user_id = unique("feedback-user")  # 规范化本次问答对应的用户标识
    question_id = _create_chat(client, api_base_url, user_id)  # 更新当前逻辑中的 关联问答 ID

    created = assert_ok(  # 更新当前逻辑中的 created
        client.post(  # 设置 assert_ok 的 字段
            f"{api_base_url}/api/feedback",  # 设置 assert_ok 的 字段
            json={  # 设置 assert_ok 的 json
                "question_id": question_id,  # 填充返回或配置中的 关联问答 ID 字段
                "user_id": user_id,  # 填充返回或配置中的 用户 ID 字段
                "is_helpful": False,  # 填充返回或配置中的 是否有帮助 字段
                "remark": "请联系 13812345678 或 hr@example.com 复核",  # 填充返回或配置中的 备注 字段
            },  # 结束 json 的定义或组装
            timeout=10,  # 设置 assert_ok 的 timeout
        )  # 结束 assert_ok 的定义或组装
    )  # 结束 assert_ok 的定义或组装
    feedback_id = created["data"]["id"]  # 更新当前逻辑中的 feedback id

    feedbacks = assert_ok(  # 更新当前逻辑中的 feedbacks
        client.get(f"{api_base_url}/api/admin/feedbacks", headers=tenant_headers, params={"is_helpful": False}, timeout=10)  # 设置 assert_ok 的 是否有帮助
    )  # 结束 assert_ok 的定义或组装
    row = next(item for item in feedbacks["data"]["list"] if item["id"] == feedback_id)  # 更新当前逻辑中的 row
    assert "13812345678" not in row["remark"]  # 执行当前业务步骤并推进后续处理
    assert "hr@example.com" not in row["remark"]  # 执行当前业务步骤并推进后续处理
    assert "[手机号已脱敏]" in row["remark"]  # 执行当前业务步骤并推进后续处理
    assert "[邮箱已脱敏]" in row["remark"]  # 执行当前业务步骤并推进后续处理

    updated = assert_ok(  # 更新当前逻辑中的 updated
        client.put(  # 设置 assert_ok 的 字段
            f"{api_base_url}/api/admin/feedbacks/{feedback_id}",  # 设置 assert_ok 的 字段
            headers=tenant_headers,  # 设置 assert_ok 的 headers
            json={"status": "resolved"},  # 设置 assert_ok 的 状态
            timeout=10,  # 设置 assert_ok 的 timeout
        )  # 结束 assert_ok 的定义或组装
    )  # 结束 assert_ok 的定义或组装
    assert updated["message"] == "反馈更新成功"  # 执行当前业务步骤并推进后续处理

    invalid = client.put(  # 更新当前逻辑中的 invalid
        f"{api_base_url}/api/admin/feedbacks/{feedback_id}",  # 设置 put 的 字段
        headers=tenant_headers,  # 设置 put 的 headers
        json={"status": "closed"},  # 设置 put 的 状态
        timeout=10,  # 设置 put 的 timeout
    )  # 结束 put 的定义或组装
    assert invalid.status_code == 400  # 执行当前业务步骤并推进后续处理


def test_feedback_rejects_cross_tenant_or_missing_question(client, api_base_url):  # 定义业务处理函数 test_feedback_rejects_cross_tenant_or_missing_question
    missing = client.post(  # 更新当前逻辑中的 missing
        f"{api_base_url}/api/feedback",  # 设置 post 的 字段
        json={"question_id": 99999999, "is_helpful": True},  # 设置 post 的 关联问答 ID
        timeout=10,  # 设置 post 的 timeout
    )  # 结束 post 的定义或组装
    assert missing.status_code == 404  # 执行当前业务步骤并推进后续处理

    bad_tenant = client.post(  # 更新当前逻辑中的 bad tenant
        f"{api_base_url}/api/feedback",  # 设置 post 的 字段
        json={"tenant_code": "not-exists", "is_helpful": True},  # 设置 post 的 tenant code
        timeout=10,  # 设置 post 的 timeout
    )  # 结束 post 的定义或组装
    assert bad_tenant.status_code == 404  # 执行当前业务步骤并推进后续处理


def test_admin_authentication_boundaries(client, api_base_url, tenant_headers):  # 定义业务处理函数 test_admin_authentication_boundaries
    unauthenticated = client.get(f"{api_base_url}/api/admin/faqs", timeout=10)  # 更新当前逻辑中的 unauthenticated
    assert unauthenticated.status_code == 401  # 执行当前业务步骤并推进后续处理

    malformed = client.get(f"{api_base_url}/api/admin/verify-token", headers={"Authorization": "Bearer"}, timeout=10)  # 更新当前逻辑中的 malformed
    assert malformed.status_code == 401  # 执行当前业务步骤并推进后续处理

    wrong_scheme = client.get(f"{api_base_url}/api/admin/verify-token", headers={"Authorization": "Basic abc"}, timeout=10)  # 更新当前逻辑中的 wrong scheme
    assert wrong_scheme.status_code == 401  # 执行当前业务步骤并推进后续处理

    bad_login = client.post(  # 更新当前逻辑中的 bad login
        f"{api_base_url}/api/admin/login",  # 设置 post 的 字段
        json={"username": "admin", "password": "wrong"},  # 设置 post 的 username
        timeout=10,  # 设置 post 的 timeout
    )  # 结束 post 的定义或组装
    assert bad_login.status_code == 401  # 执行当前业务步骤并推进后续处理

    verified = assert_ok(client.get(f"{api_base_url}/api/admin/verify-token", headers=tenant_headers, timeout=10))  # 更新当前逻辑中的 verified
    assert verified["data"]["username"] == "tenant_admin"  # 执行当前业务步骤并推进后续处理
    assert "password" not in verified["data"]  # 执行当前业务步骤并推进后续处理


def test_tenant_admin_cannot_cross_tenant_or_create_super_admin(client, api_base_url, super_headers, tenant_headers):  # 定义业务处理函数 test_tenant_admin_cannot_cross_tenant_or_create_super_admin
    tenant_code = unique("tenant")  # 更新当前逻辑中的 tenant code
    created = assert_ok(  # 更新当前逻辑中的 created
        client.post(  # 设置 assert_ok 的 字段
            f"{api_base_url}/api/admin/tenants",  # 设置 assert_ok 的 字段
            headers=super_headers,  # 设置 assert_ok 的 headers
            json={"code": tenant_code, "name": "自动化边界租户"},  # 设置 assert_ok 的 code
            timeout=10,  # 设置 assert_ok 的 timeout
        )  # 结束 assert_ok 的定义或组装
    )  # 结束 assert_ok 的定义或组装
    other_tenant_id = created["data"]["id"]  # 更新当前逻辑中的 other tenant id

    forbidden = client.get(  # 更新当前逻辑中的 forbidden
        f"{api_base_url}/api/admin/faqs",  # 设置 get 的 字段
        headers=tenant_headers,  # 设置 get 的 headers
        params={"tenant_id": other_tenant_id},  # 设置 get 的 租户 ID
        timeout=10,  # 设置 get 的 timeout
    )  # 结束 get 的定义或组装
    assert forbidden.status_code == 403  # 执行当前业务步骤并推进后续处理

    create_super = client.post(  # 更新当前逻辑中的 create super
        f"{api_base_url}/api/admin/admins",  # 设置 post 的 字段
        headers=tenant_headers,  # 设置 post 的 headers
        json={"username": unique("bad-super"), "password": "Password@123", "role": "super_admin"},  # 设置 post 的 username
        timeout=10,  # 设置 post 的 timeout
    )  # 结束 post 的定义或组装
    assert create_super.status_code == 403  # 执行当前业务步骤并推进后续处理


def test_viewer_role_is_read_only_for_faq_source_feedback_and_package_modules(client, api_base_url, tenant_headers):  # 定义业务处理函数 test_viewer_role_is_read_only_for_faq_source_feedback_and_package_modules
    username = unique("viewer")  # 更新当前逻辑中的 username
    created = assert_ok(  # 更新当前逻辑中的 created
        client.post(  # 设置 assert_ok 的 字段
            f"{api_base_url}/api/admin/admins",  # 设置 assert_ok 的 字段
            headers=tenant_headers,  # 设置 assert_ok 的 headers
            json={"username": username, "password": "Password@123", "role": "viewer"},  # 设置 assert_ok 的 username
            timeout=10,  # 设置 assert_ok 的 timeout
        )  # 结束 assert_ok 的定义或组装
    )  # 结束 assert_ok 的定义或组装
    assert created["data"]["role"] == "viewer"  # 执行当前业务步骤并推进后续处理

    login = client.post(  # 更新当前逻辑中的 login
        f"{api_base_url}/api/admin/login",  # 设置 post 的 字段
        json={"username": username, "password": "Password@123", "tenant_code": "demo-sx"},  # 设置 post 的 username
        timeout=10,  # 设置 post 的 timeout
    )  # 结束 post 的定义或组装
    assert login.status_code == 200, login.text  # 执行当前业务步骤并推进后续处理
    viewer_headers = {"Authorization": f"Bearer {login.json()['access_token']}", "X-Tenant-Code": "demo-sx"}  # 更新当前逻辑中的 viewer headers

    allowed_logs = client.get(f"{api_base_url}/api/admin/logs", headers=viewer_headers, timeout=10)  # 更新当前逻辑中的 allowed logs
    assert allowed_logs.status_code == 200  # 执行当前业务步骤并推进后续处理

    forbidden_calls = [  # 更新当前逻辑中的 forbidden calls
        ("get", "/api/admin/faqs", None),  # 补充列表中的 ("get", "/api/admin/faqs", None) 项
        ("post", "/api/admin/faqs", {"question": "viewer faq", "answer": "no"}),  # 补充列表中的 问题内容 项
        ("get", "/api/admin/sources", None),  # 补充列表中的 ("get", "/api/admin/sources", None) 项
        ("post", "/api/admin/sources", {"title": "viewer source", "url": "https://example.com"}),  # 补充列表中的 标题 项
        ("get", "/api/admin/feedbacks", None),  # 补充列表中的 ("get", "/api/admin/feedbacks", None) 项
        ("get", "/api/admin/knowledge-packages", None),  # 补充列表中的 ("get", "/api/admin/knowledge-packages", None) 项
        ("get", "/api/admin/test-questions", None),  # 补充列表中的 ("get", "/api/admin/test-questions", None) 项
    ]  # 结束 forbidden_calls 的定义或组装
    for method, path, json_body in forbidden_calls:  # 遍历当前集合中的每一项并逐个处理
        response = getattr(client, method)(f"{api_base_url}{path}", headers=viewer_headers, json=json_body, timeout=10)  # 保存当前分支生成的响应对象
        assert response.status_code == 403, f"{method.upper()} {path} returned {response.status_code}: {response.text}"  # 执行当前业务步骤并推进后续处理

