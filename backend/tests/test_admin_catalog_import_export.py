import csv  # 导入 CSV 读写工具，供导入导出接口复用
import io  # 导入内存流工具，便于处理上传与下载内容

from conftest import assert_ok, unique  # 导入当前模块运行所依赖的工具或类型


def test_faq_crud_duplicate_upsert_import_export_and_batch(client, api_base_url, tenant_headers):  # 定义业务处理函数 test_faq_crud_duplicate_upsert_import_export_and_batch
    faq_code = unique("FAQAUTO")  # 更新当前逻辑中的 FAQ 编码
    created = assert_ok(  # 更新当前逻辑中的 created
        client.post(  # 设置 assert_ok 的 字段
            f"{api_base_url}/api/admin/faqs",  # 设置 assert_ok 的 字段
            headers=tenant_headers,  # 设置 assert_ok 的 headers
            json={  # 设置 assert_ok 的 json
                "faq_code": faq_code,  # 填充返回或配置中的 FAQ 编码 字段
                "question": f"{faq_code} 试用期工资是否能低于最低工资？",  # 填充返回或配置中的 问题内容 字段
                "answer": "不能低于当地最低工资标准。",  # 填充返回或配置中的 回答内容 字段
                "category": "工资",  # 填充返回或配置中的 分类 字段
                "risk_level": "high",  # 填充返回或配置中的 风险等级 字段
                "keywords": ["试用期", "最低工资"],  # 填充返回或配置中的 关键字 字段
            },  # 结束 json 的定义或组装
            timeout=10,  # 设置 assert_ok 的 timeout
        )  # 结束 assert_ok 的定义或组装
    )  # 结束 assert_ok 的定义或组装
    faq_id = created["data"]["id"]  # 更新当前逻辑中的 faq id

    duplicate = assert_ok(  # 更新当前逻辑中的 duplicate
        client.post(  # 设置 assert_ok 的 字段
            f"{api_base_url}/api/admin/faqs",  # 设置 assert_ok 的 字段
            headers=tenant_headers,  # 设置 assert_ok 的 headers
            json={  # 设置 assert_ok 的 json
                "faq_code": faq_code,  # 填充返回或配置中的 FAQ 编码 字段
                "question": f"{faq_code} 试用期工资是否能低于最低工资？",  # 填充返回或配置中的 问题内容 字段
                "answer": "重复导入时应覆盖更新。",  # 填充返回或配置中的 回答内容 字段
                "category": "工资",  # 填充返回或配置中的 分类 字段
            },  # 结束 json 的定义或组装
            timeout=10,  # 设置 assert_ok 的 timeout
        )  # 结束 assert_ok 的定义或组装
    )  # 结束 assert_ok 的定义或组装
    assert duplicate["data"]["id"] == faq_id  # 执行当前业务步骤并推进后续处理
    assert "覆盖更新" in duplicate["message"]  # 执行当前业务步骤并推进后续处理

    listed = assert_ok(  # 更新当前逻辑中的 listed
        client.get(f"{api_base_url}/api/admin/faqs", headers=tenant_headers, params={"keyword": faq_code}, timeout=10)  # 设置 assert_ok 的 keyword
    )  # 结束 assert_ok 的定义或组装
    assert listed["data"]["total"] == 1  # 执行当前业务步骤并推进后续处理

    csv_body = "faq_code,question,answer,category,risk_level\nAUTO_IMPORT,自动导入FAQ问题,自动导入FAQ答案,社保,medium\n,Bad row,,,\n"  # 更新当前逻辑中的 csv body
    imported = assert_ok(  # 更新当前逻辑中的 imported
        client.post(  # 设置 assert_ok 的 字段
            f"{api_base_url}/api/admin/faqs/import",  # 设置 assert_ok 的 字段
            headers=tenant_headers,  # 设置 assert_ok 的 headers
            files={"file": ("faqs.csv", csv_body.encode("utf-8-sig"), "text/csv")},  # 设置 assert_ok 的 file
            timeout=10,  # 设置 assert_ok 的 timeout
        )  # 结束 assert_ok 的定义或组装
    )  # 结束 assert_ok 的定义或组装
    assert imported["data"]["imported"] >= 1  # 执行当前业务步骤并推进后续处理
    assert imported["data"]["skipped"] == 1  # 执行当前业务步骤并推进后续处理

    exported = client.get(f"{api_base_url}/api/admin/faqs/export", headers=tenant_headers, timeout=10)  # 更新当前逻辑中的 exported
    assert exported.status_code == 200  # 执行当前业务步骤并推进后续处理
    rows = list(csv.DictReader(io.StringIO(exported.content.decode("utf-8-sig"))))  # 更新当前逻辑中的 rows
    assert any(row["faq_code"] == faq_code for row in rows)  # 执行当前业务步骤并推进后续处理

    invalid_batch = client.post(  # 更新当前逻辑中的 invalid batch
        f"{api_base_url}/api/admin/faqs/batch",  # 设置 post 的 字段
        headers=tenant_headers,  # 设置 post 的 headers
        json={"ids": [faq_id], "action": "set_risk", "risk_level": "critical"},  # 设置 post 的 ids
        timeout=10,  # 设置 post 的 timeout
    )  # 结束 post 的定义或组装
    assert invalid_batch.status_code == 400  # 执行当前业务步骤并推进后续处理

    batch = assert_ok(  # 更新当前逻辑中的 batch
        client.post(  # 设置 assert_ok 的 字段
            f"{api_base_url}/api/admin/faqs/batch",  # 设置 assert_ok 的 字段
            headers=tenant_headers,  # 设置 assert_ok 的 headers
            json={"ids": [faq_id], "action": "set_risk", "risk_level": "low"},  # 设置 assert_ok 的 ids
            timeout=10,  # 设置 assert_ok 的 timeout
        )  # 结束 assert_ok 的定义或组装
    )  # 结束 assert_ok 的定义或组装
    assert batch["data"]["affected"] == 1  # 执行当前业务步骤并推进后续处理


def test_source_upload_crud_review_guards_import_export_and_batch(client, api_base_url, tenant_headers):  # 定义业务处理函数 test_source_upload_crud_review_guards_import_export_and_batch
    missing_path = client.post(  # 更新当前逻辑中的 missing path
        f"{api_base_url}/api/admin/sources",  # 设置 post 的 字段
        headers=tenant_headers,  # 设置 post 的 headers
        json={"title": "无来源路径"},  # 设置 post 的 标题
        timeout=10,  # 设置 post 的 timeout
    )  # 结束 post 的定义或组装
    assert missing_path.status_code == 422  # 执行当前业务步骤并推进后续处理

    bad_upload = client.post(  # 更新当前逻辑中的 bad upload
        f"{api_base_url}/api/admin/sources/upload",  # 设置 post 的 字段
        headers=tenant_headers,  # 设置 post 的 headers
        files={"file": ("evil.exe", b"no", "application/octet-stream")},  # 设置 post 的 file
        timeout=10,  # 设置 post 的 timeout
    )  # 结束 post 的定义或组装
    assert bad_upload.status_code == 400  # 执行当前业务步骤并推进后续处理

    upload = assert_ok(  # 更新当前逻辑中的 upload
        client.post(  # 设置 assert_ok 的 字段
            f"{api_base_url}/api/admin/sources/upload",  # 设置 assert_ok 的 字段
            headers=tenant_headers,  # 设置 assert_ok 的 headers
            files={"file": ("../../policy.pdf", b"policy", "application/pdf")},  # 设置 assert_ok 的 file
            timeout=10,  # 设置 assert_ok 的 timeout
        )  # 结束 assert_ok 的定义或组装
    )  # 结束 assert_ok 的定义或组装
    assert upload["data"]["local_file"].startswith("tenant_")  # 执行当前业务步骤并推进后续处理
    assert ".." not in upload["data"]["local_file"]  # 执行当前业务步骤并推进后续处理

    source_code = unique("SRCAUTO")  # 更新当前逻辑中的 资料编码
    created = assert_ok(  # 更新当前逻辑中的 created
        client.post(  # 设置 assert_ok 的 字段
            f"{api_base_url}/api/admin/sources",  # 设置 assert_ok 的 字段
            headers=tenant_headers,  # 设置 assert_ok 的 headers
            json={  # 设置 assert_ok 的 json
                "source_code": source_code,  # 填充返回或配置中的 资料编码 字段
                "title": f"{source_code} 陕西政策来源",  # 填充返回或配置中的 标题 字段
                "url": f"https://example.com/{source_code}",  # 填充返回或配置中的 链接地址 字段
                "issuer": "自动化测试",  # 填充返回或配置中的 issuer 字段
                "review_status": "待人工复核",  # 填充返回或配置中的 review status 字段
            },  # 结束 json 的定义或组装
            timeout=10,  # 设置 assert_ok 的 timeout
        )  # 结束 assert_ok 的定义或组装
    )  # 结束 assert_ok 的定义或组装
    source_id = created["data"]["id"]  # 更新当前逻辑中的 source id

    reviewed = assert_ok(  # 更新当前逻辑中的 reviewed
        client.put(  # 设置 assert_ok 的 字段
            f"{api_base_url}/api/admin/sources/{source_id}",  # 设置 assert_ok 的 字段
            headers=tenant_headers,  # 设置 assert_ok 的 headers
            json={"review_status": "已复核"},  # 设置 assert_ok 的 review status
            timeout=10,  # 设置 assert_ok 的 timeout
        )  # 结束 assert_ok 的定义或组装
    )  # 结束 assert_ok 的定义或组装
    assert reviewed["data"]["reviewed_at"]  # 执行当前业务步骤并推进后续处理
    assert reviewed["data"]["reviewed_by"]  # 执行当前业务步骤并推进后续处理

    locked = client.put(  # 更新当前逻辑中的 locked
        f"{api_base_url}/api/admin/sources/{source_id}",  # 设置 put 的 字段
        headers=tenant_headers,  # 设置 put 的 headers
        json={"title": "已复核后不应编辑"},  # 设置 put 的 标题
        timeout=10,  # 设置 put 的 timeout
    )  # 结束 put 的定义或组装
    assert locked.status_code == 400  # 执行当前业务步骤并推进后续处理

    csv_body = "source_code,title,url,issuer,review_status\nSRC_IMPORT,CSV来源,https://example.com/src-import,自动化测试,待人工复核\n,Bad,,,\n"  # 更新当前逻辑中的 csv body
    imported = assert_ok(  # 更新当前逻辑中的 imported
        client.post(  # 设置 assert_ok 的 字段
            f"{api_base_url}/api/admin/sources/import",  # 设置 assert_ok 的 字段
            headers=tenant_headers,  # 设置 assert_ok 的 headers
            files={"file": ("sources.csv", csv_body.encode("utf-8-sig"), "text/csv")},  # 设置 assert_ok 的 file
            timeout=10,  # 设置 assert_ok 的 timeout
        )  # 结束 assert_ok 的定义或组装
    )  # 结束 assert_ok 的定义或组装
    assert imported["data"]["imported"] >= 1  # 执行当前业务步骤并推进后续处理
    assert imported["data"]["skipped"] == 1  # 执行当前业务步骤并推进后续处理

    non_csv = client.post(  # 更新当前逻辑中的 non csv
        f"{api_base_url}/api/admin/sources/import",  # 设置 post 的 字段
        headers=tenant_headers,  # 设置 post 的 headers
        files={"file": ("sources.txt", b"title,url\nbad,https://example.com", "text/plain")},  # 设置 post 的 file
        timeout=10,  # 设置 post 的 timeout
    )  # 结束 post 的定义或组装
    assert non_csv.status_code == 400  # 执行当前业务步骤并推进后续处理

    exported = client.get(f"{api_base_url}/api/admin/sources/export", headers=tenant_headers, timeout=10)  # 更新当前逻辑中的 exported
    assert exported.status_code == 200  # 执行当前业务步骤并推进后续处理
    assert "source_code" in exported.content.decode("utf-8-sig").splitlines()[0]  # 执行当前业务步骤并推进后续处理

    batch_missing = client.post(  # 更新当前逻辑中的 batch missing
        f"{api_base_url}/api/admin/sources/batch",  # 设置 post 的 字段
        headers=tenant_headers,  # 设置 post 的 headers
        json={"ids": [], "action": "delete"},  # 设置 post 的 ids
        timeout=10,  # 设置 post 的 timeout
    )  # 结束 post 的定义或组装
    assert batch_missing.status_code == 400  # 执行当前业务步骤并推进后续处理


def test_knowledge_packages_status_import_export_batch_and_test_questions(client, api_base_url, tenant_headers):  # 定义业务处理函数 test_knowledge_packages_status_import_export_batch_and_test_questions
    packages = assert_ok(client.get(f"{api_base_url}/api/admin/knowledge-packages", headers=tenant_headers, timeout=10))  # 更新当前逻辑中的 packages
    assert packages["data"]["total"] >= 1  # 执行当前业务步骤并推进后续处理
    package_id = packages["data"]["list"][0]["id"]  # 更新当前逻辑中的 package id

    invalid_status = client.put(  # 更新当前逻辑中的 invalid status
        f"{api_base_url}/api/admin/knowledge-packages/{package_id}/status",  # 设置 put 的 字段
        headers=tenant_headers,  # 设置 put 的 headers
        json={"status": "archived"},  # 设置 put 的 状态
        timeout=10,  # 设置 put 的 timeout
    )  # 结束 put 的定义或组装
    assert invalid_status.status_code == 400  # 执行当前业务步骤并推进后续处理

    updated = assert_ok(  # 更新当前逻辑中的 updated
        client.put(  # 设置 assert_ok 的 字段
            f"{api_base_url}/api/admin/knowledge-packages/{package_id}/status",  # 设置 assert_ok 的 字段
            headers=tenant_headers,  # 设置 assert_ok 的 headers
            json={"status": "active"},  # 设置 assert_ok 的 状态
            timeout=10,  # 设置 assert_ok 的 timeout
        )  # 结束 assert_ok 的定义或组装
    )  # 结束 assert_ok 的定义或组装
    assert updated["message"] == "状态更新成功"  # 执行当前业务步骤并推进后续处理

    csv_body = "name,region,version,status,categories\n自动化知识包,陕西,v-test,active,社保|工资\n"  # 更新当前逻辑中的 csv body
    imported = assert_ok(  # 更新当前逻辑中的 imported
        client.post(  # 设置 assert_ok 的 字段
            f"{api_base_url}/api/admin/knowledge-packages/import",  # 设置 assert_ok 的 字段
            headers=tenant_headers,  # 设置 assert_ok 的 headers
            files={"file": ("packages.csv", csv_body.encode("utf-8-sig"), "text/csv")},  # 设置 assert_ok 的 file
            timeout=10,  # 设置 assert_ok 的 timeout
        )  # 结束 assert_ok 的定义或组装
    )  # 结束 assert_ok 的定义或组装
    assert imported["data"]["imported"] >= 1  # 执行当前业务步骤并推进后续处理

    exported = client.get(f"{api_base_url}/api/admin/knowledge-packages/export", headers=tenant_headers, timeout=10)  # 更新当前逻辑中的 exported
    assert exported.status_code == 200  # 执行当前业务步骤并推进后续处理
    assert "knowledge-packages.csv" in exported.headers.get("content-disposition", "")  # 执行当前业务步骤并推进后续处理

    test_questions = assert_ok(client.get(f"{api_base_url}/api/admin/test-questions", headers=tenant_headers, timeout=10))  # 更新当前逻辑中的 test questions
    assert test_questions["data"]["total"] >= 4  # 执行当前业务步骤并推进后续处理

