from io import BytesIO  # 导入当前模块运行所依赖的工具或类型

from conftest import assert_ok, unique  # 导入当前模块运行所依赖的工具或类型


def test_disabled_knowledge_package_short_circuits_external_and_local_faq(client, api_base_url, tenant_headers):  # 定义业务处理函数 test_disabled_knowledge_package_short_circuits_external_and_local_faq
    packages = assert_ok(client.get(f"{api_base_url}/api/admin/knowledge-packages", headers=tenant_headers, timeout=10))  # 更新当前逻辑中的 packages
    package_ids = [item["id"] for item in packages["data"]["list"]]  # 更新当前逻辑中的 package ids

    for package_id in package_ids:  # 遍历当前集合中的每一项并逐个处理
        assert_ok(  # 执行当前业务步骤并推进后续处理
            client.put(  # 执行当前业务步骤并推进后续处理
                f"{api_base_url}/api/admin/knowledge-packages/{package_id}/status",  # 执行当前业务步骤并推进后续处理
                headers=tenant_headers,  # 准备当前响应或外部请求需要的 HTTP 头
                json={"status": "disabled"},  # 更新当前逻辑中的 json
                timeout=10,  # 更新当前逻辑中的 timeout
            )  # 执行当前业务步骤并推进后续处理
        )  # 执行当前业务步骤并推进后续处理

    user_id = unique("disabled-package")  # 规范化本次问答对应的用户标识
    response = assert_ok(  # 保存当前分支生成的响应对象
        client.post(  # 设置 assert_ok 的 字段
            f"{api_base_url}/api/chat",  # 设置 assert_ok 的 字段
            json={"question": "陕西产假多少天？", "user_id": user_id},  # 设置 assert_ok 的 问题内容
            timeout=20,  # 设置 assert_ok 的 timeout
        )  # 结束 assert_ok 的定义或组装
    )  # 结束 assert_ok 的定义或组装
    assert response["data"]["provider"] == "knowledge_package_disabled"  # 执行当前业务步骤并推进后续处理
    assert "知识包已停用" in response["data"]["answer"]  # 执行当前业务步骤并推进后续处理

    for package_id in package_ids:  # 遍历当前集合中的每一项并逐个处理
        assert_ok(  # 执行当前业务步骤并推进后续处理
            client.put(  # 执行当前业务步骤并推进后续处理
                f"{api_base_url}/api/admin/knowledge-packages/{package_id}/status",  # 执行当前业务步骤并推进后续处理
                headers=tenant_headers,  # 准备当前响应或外部请求需要的 HTTP 头
                json={"status": "active"},  # 更新当前逻辑中的 json
                timeout=10,  # 更新当前逻辑中的 timeout
            )  # 执行当前业务步骤并推进后续处理
        )  # 执行当前业务步骤并推进后续处理


def test_source_duplicate_guard_is_tenant_scoped(client, api_base_url, super_headers, tenant_headers):  # 定义业务处理函数 test_source_duplicate_guard_is_tenant_scoped
    source_code = unique("TENANT_SRC")  # 更新当前逻辑中的 资料编码
    title = f"{source_code} 同名来源"  # 更新当前逻辑中的 标题
    url = f"https://example.com/{source_code}"  # 更新当前逻辑中的 链接地址

    demo_source = assert_ok(  # 更新当前逻辑中的 demo source
        client.post(  # 设置 assert_ok 的 字段
            f"{api_base_url}/api/admin/sources",  # 设置 assert_ok 的 字段
            headers=tenant_headers,  # 设置 assert_ok 的 headers
            json={"source_code": source_code, "title": title, "url": url, "issuer": "自动化测试"},  # 设置 assert_ok 的 资料编码
            timeout=10,  # 设置 assert_ok 的 timeout
        )  # 结束 assert_ok 的定义或组装
    )  # 结束 assert_ok 的定义或组装
    assert demo_source["data"]["source_code"] == source_code  # 执行当前业务步骤并推进后续处理

    other_code = unique("tenant-edge")  # 更新当前逻辑中的 other code
    tenant = assert_ok(  # 保存当前请求实际使用的租户对象
        client.post(  # 设置 assert_ok 的 字段
            f"{api_base_url}/api/admin/tenants",  # 设置 assert_ok 的 字段
            headers=super_headers,  # 设置 assert_ok 的 headers
            json={  # 设置 assert_ok 的 json
                "code": other_code,  # 填充返回或配置中的 code 字段
                "name": "自动化跨租户来源",  # 填充返回或配置中的 名称 字段
                "admin_username": f"{other_code}_admin",  # 填充返回或配置中的 admin username 字段
                "admin_password": "Password@123",  # 填充返回或配置中的 admin password 字段
            },  # 结束 json 的定义或组装
            timeout=10,  # 设置 assert_ok 的 timeout
        )  # 结束 assert_ok 的定义或组装
    )  # 结束 assert_ok 的定义或组装

    other_source = assert_ok(  # 更新当前逻辑中的 other source
        client.post(  # 设置 assert_ok 的 字段
            f"{api_base_url}/api/admin/sources",  # 设置 assert_ok 的 字段
            headers=super_headers,  # 设置 assert_ok 的 headers
            params={"tenant_id": tenant["data"]["id"]},  # 设置 assert_ok 的 租户 ID
            json={"source_code": source_code, "title": title, "url": url, "issuer": "自动化测试"},  # 设置 assert_ok 的 资料编码
            timeout=10,  # 设置 assert_ok 的 timeout
        )  # 结束 assert_ok 的定义或组装
    )  # 结束 assert_ok 的定义或组装
    assert other_source["data"]["tenant_id"] == tenant["data"]["id"]  # 执行当前业务步骤并推进后续处理


def test_upload_size_limit_removes_oversized_file(client, api_base_url, tenant_headers):  # 定义业务处理函数 test_upload_size_limit_removes_oversized_file
    response = client.post(  # 保存当前分支生成的响应对象
        f"{api_base_url}/api/admin/sources/upload",  # 设置 post 的 字段
        headers=tenant_headers,  # 设置 post 的 headers
        files={"file": ("large.pdf", BytesIO(b"x" * 70000), "application/pdf")},  # 设置 post 的 file
        timeout=10,  # 设置 post 的 timeout
    )  # 结束 post 的定义或组装
    assert response.status_code == 413  # 执行当前业务步骤并推进后续处理


def test_dify_stream_parser_handles_message_workflow_and_invalid_lines(api_base_url, monkeypatch):  # 定义业务处理函数 test_dify_stream_parser_handles_message_workflow_and_invalid_lines
    import os  # 导入当前模块运行所依赖的工具或类型

    os.environ["DB_NAME"] = "employment_slc_auto_test"  # 执行当前业务步骤并推进后续处理
    from app.database import SessionLocal  # 导入数据库依赖与全局运行配置
    from app.models import Tenant  # 导入当前业务会读写的 ORM 模型
    from app.services import dify_service  # 导入外部问答或种子数据相关服务
    from app.services.dify_service import ComplianceAnswerService  # 导入外部问答或种子数据相关服务

    class FakeResponse:  # 定义业务类 FakeResponse
        def iter_lines(self, decode_unicode=True):  # 定义业务处理函数 iter_lines
            lines = [  # 更新当前逻辑中的 lines
                'data: {"event":"message","task_id":"task-1","conversation_id":"conv-1","message_id":"msg-1","answer":"第一段"}',  # 补充列表中的 event 项
                "data: not-json",  # 补充列表中的 data 项
                'event: ping',  # 补充列表中的 event 项
                'data: {"event":"message","answer":"第二段"}',  # 补充列表中的 event 项
                'data: {"event":"message_end","metadata":{"retriever_resources":[{"document_name":"来源A","content":"摘要"}]}}',  # 补充列表中的 event 项
            ]  # 结束 lines 的定义或组装
            yield from lines  # 把当前结果交给 FastAPI 依赖或生成器继续消费

    with SessionLocal() as db:  # 执行当前业务步骤并推进后续处理
        tenant = db.query(Tenant).filter(Tenant.code == "demo-sx").first()  # 构造当前业务的基础数据库查询对象
        service = ComplianceAnswerService(db, tenant)  # 实例化统一问答服务，优先走 Dify 再回退本地 FAQ
        parsed = service._consume_dify_stream(FakeResponse(), "gen-edge", "key", "user")  # 更新当前逻辑中的 parsed

    assert parsed["answer"] == "第一段第二段"  # 执行当前业务步骤并推进后续处理
    assert parsed["conversation_id"] == "conv-1"  # 执行当前业务步骤并推进后续处理
    assert parsed["metadata"]["retriever_resources"][0]["document_name"] == "来源A"  # 执行当前业务步骤并推进后续处理

    class StopResponse:  # 定义业务类 StopResponse
        status_code = 204  # 更新当前逻辑中的 status code
        text = ""  # 把文件字节内容解码成可解析的文本

    monkeypatch.setattr(dify_service.requests, "post", lambda *args, **kwargs: StopResponse())  # 执行当前业务步骤并推进后续处理
    assert ComplianceAnswerService.stop_generation("gen-edge") is True  # 执行当前业务步骤并推进后续处理

    class WorkflowResponse:  # 定义业务类 WorkflowResponse
        def iter_lines(self, decode_unicode=True):  # 定义业务处理函数 iter_lines
            yield 'data: {"event":"workflow_finished","data":{"outputs":{"answer":"工作流最终回答"}}}'  # 把当前结果交给 FastAPI 依赖或生成器继续消费

    with SessionLocal() as db:  # 执行当前业务步骤并推进后续处理
        tenant = db.query(Tenant).filter(Tenant.code == "demo-sx").first()  # 构造当前业务的基础数据库查询对象
        service = ComplianceAnswerService(db, tenant)  # 实例化统一问答服务，优先走 Dify 再回退本地 FAQ
        workflow = service._consume_dify_stream(WorkflowResponse(), None, "key", "user")  # 更新当前逻辑中的 workflow
    assert workflow["answer"] == "工作流最终回答"  # 执行当前业务步骤并推进后续处理


def test_dify_answer_risk_level_takes_precedence_over_question_estimate(api_base_url):  # 定义业务处理函数 test_dify_answer_risk_level_takes_precedence_over_question_estimate
    import os  # 导入当前模块运行所依赖的工具或类型

    os.environ["DB_NAME"] = "employment_slc_auto_test"  # 执行当前业务步骤并推进后续处理
    from app.database import SessionLocal  # 导入数据库依赖与全局运行配置
    from app.models import Tenant  # 导入当前业务会读写的 ORM 模型
    from app.services.dify_service import ComplianceAnswerService  # 导入外部问答或种子数据相关服务

    with SessionLocal() as db:  # 执行当前业务步骤并推进后续处理
        tenant = db.query(Tenant).filter(Tenant.code == "demo-sx").first()  # 构造当前业务的基础数据库查询对象
        service = ComplianceAnswerService(db, tenant)  # 实例化统一问答服务，优先走 Dify 再回退本地 FAQ

        assert service._estimate_risk("公司不发工资怎么办") == "low"  # 执行当前业务步骤并推进后续处理
        assert service._risk_from_answer("风险等级：高\n\n结论：公司拖欠工资属于严重风险。") == "high"  # 执行当前业务步骤并推进后续处理
        assert service._risk_from_answer("初步风险等级为：中风险。建议复核。") == "medium"  # 执行当前业务步骤并推进后续处理
        assert service._risk_from_answer("风险等级：low") == "low"  # 执行当前业务步骤并推进后续处理
