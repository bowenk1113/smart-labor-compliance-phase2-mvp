import os  # 导入当前模块运行所依赖的工具或类型
import socket  # 导入当前模块运行所依赖的工具或类型
import subprocess  # 导入当前模块运行所依赖的工具或类型
import sys  # 导入当前模块运行所依赖的工具或类型
import time  # 导入时间工具，统计耗时或生成时间戳
from pathlib import Path  # 导入路径处理工具，定位本地文件与目录

import pymysql  # 导入当前模块运行所依赖的工具或类型
import pytest  # 导入当前模块运行所依赖的工具或类型
import requests  # 导入 HTTP 客户端，调用外部 Dify 或 RAGFlow 服务


BACKEND_ROOT = Path(__file__).resolve().parents[1]  # 更新当前逻辑中的 BACKEND ROOT
TEST_DB_NAME = os.getenv("SLC_TEST_DB_NAME", "employment_slc_auto_test")  # 更新当前逻辑中的 TEST DB NAME
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")  # 更新当前逻辑中的 DB HOST
DB_PORT = int(os.getenv("DB_PORT", "3306"))  # 更新当前逻辑中的 DB PORT
DB_USER = os.getenv("DB_USER", "root")  # 更新当前逻辑中的 DB USER
DB_PASSWORD = os.getenv("DB_PASSWORD", "infini_rag_flow")  # 更新当前逻辑中的 DB PASSWORD

if "test" not in TEST_DB_NAME.lower():  # 根据当前条件决定是否进入对应业务分支
    raise RuntimeError("Refusing to run destructive test setup without a test database name.")  # 执行当前控制流分支

os.environ.setdefault("DB_HOST", DB_HOST)  # 仅在系统环境未覆盖时写入 .env 中的配置值
os.environ.setdefault("DB_PORT", str(DB_PORT))  # 仅在系统环境未覆盖时写入 .env 中的配置值
os.environ.setdefault("DB_USER", DB_USER)  # 仅在系统环境未覆盖时写入 .env 中的配置值
os.environ.setdefault("DB_PASSWORD", DB_PASSWORD)  # 仅在系统环境未覆盖时写入 .env 中的配置值
os.environ.setdefault("DB_NAME", TEST_DB_NAME)  # 仅在系统环境未覆盖时写入 .env 中的配置值
os.environ.setdefault("AUTO_SEED", "true")  # 仅在系统环境未覆盖时写入 .env 中的配置值
os.environ.setdefault("DIFY_API_KEY", "")  # 仅在系统环境未覆盖时写入 .env 中的配置值
os.environ.setdefault("RAGFLOW_API_KEY", "")  # 仅在系统环境未覆盖时写入 .env 中的配置值
os.environ.setdefault("RATE_LIMIT_MAX_REQUESTS", "10000")  # 仅在系统环境未覆盖时写入 .env 中的配置值
os.environ.setdefault("MAX_REQUEST_BYTES", "8192")  # 仅在系统环境未覆盖时写入 .env 中的配置值
os.environ.setdefault("MAX_UPLOAD_BYTES", "65536")  # 仅在系统环境未覆盖时写入 .env 中的配置值


def _drop_test_database() -> None:  # 定义业务处理函数 _drop_test_database
    connection = pymysql.connect(  # 更新当前逻辑中的 connection
        host=DB_HOST,  # 设置 connect 的 host
        port=DB_PORT,  # 设置 connect 的 port
        user=DB_USER,  # 设置 connect 的 user
        password=DB_PASSWORD,  # 设置 connect 的 password
        charset="utf8mb4",  # 设置 connect 的 charset
        connect_timeout=10,  # 设置 connect 的 connect timeout
    )  # 结束 connect 的定义或组装
    try:  # 尝试执行可能依赖外部服务或数据库的逻辑
        with connection.cursor() as cursor:  # 执行当前业务步骤并推进后续处理
            cursor.execute(f"DROP DATABASE IF EXISTS `{TEST_DB_NAME.replace('`', '``')}`")  # 执行当前业务步骤并推进后续处理
        connection.commit()  # 执行当前业务步骤并推进后续处理
    finally:  # 无论成功失败都执行资源释放或收尾逻辑
        connection.close()  # 执行当前业务步骤并推进后续处理


def _free_port() -> int:  # 定义业务处理函数 _free_port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:  # 执行当前业务步骤并推进后续处理
        sock.bind(("127.0.0.1", 0))  # 执行当前业务步骤并推进后续处理
        return sock.getsockname()[1]  # 返回当前分支整理好的结果


@pytest.fixture(scope="session")  # 为后续函数或类声明附加装饰器配置
def api_base_url():  # 定义业务处理函数 api_base_url
    _drop_test_database()  # 执行当前业务步骤并推进后续处理
    port = _free_port()  # 更新当前逻辑中的 port
    env = os.environ.copy()  # 更新当前逻辑中的 env
    env.update(  # 执行当前业务步骤并推进后续处理
        {  # 执行当前业务步骤并推进后续处理
            "DB_NAME": TEST_DB_NAME,  # 执行当前业务步骤并推进后续处理
            "AUTO_SEED": "true",  # 执行当前业务步骤并推进后续处理
            "DIFY_API_KEY": "",  # 执行当前业务步骤并推进后续处理
            "RAGFLOW_API_KEY": "",  # 执行当前业务步骤并推进后续处理
            "RATE_LIMIT_MAX_REQUESTS": "10000",  # 执行当前业务步骤并推进后续处理
            "MAX_REQUEST_BYTES": "8192",  # 执行当前业务步骤并推进后续处理
            "MAX_UPLOAD_BYTES": "65536",  # 执行当前业务步骤并推进后续处理
            "PYTHONUNBUFFERED": "1",  # 执行当前业务步骤并推进后续处理
        }  # 执行当前业务步骤并推进后续处理
    )  # 执行当前业务步骤并推进后续处理
    process = subprocess.Popen(  # 更新当前逻辑中的 process
        [  # 设置 Popen 的 字段
            sys.executable,  # 设置 Popen 的 字段
            "-m",  # 设置 Popen 的 字段
            "uvicorn",  # 设置 Popen 的 字段
            "app.main:app",  # 设置 Popen 的 字段
            "--host",  # 设置 Popen 的 字段
            "127.0.0.1",  # 设置 Popen 的 字段
            "--port",  # 设置 Popen 的 字段
            str(port),  # 设置 Popen 的 字段
            "--log-level",  # 设置 Popen 的 字段
            "warning",  # 设置 Popen 的 字段
        ],  # 设置 Popen 的 字段
        cwd=BACKEND_ROOT,  # 设置 Popen 的 cwd
        env=env,  # 设置 Popen 的 env
        stdout=subprocess.PIPE,  # 设置 Popen 的 stdout
        stderr=subprocess.STDOUT,  # 设置 Popen 的 stderr
        text=True,  # 设置 Popen 的 text
    )  # 结束 Popen 的定义或组装
    base_url = f"http://127.0.0.1:{port}"  # 更新当前逻辑中的 base url
    try:  # 尝试执行可能依赖外部服务或数据库的逻辑
        deadline = time.time() + 45  # 更新当前逻辑中的 deadline
        last_error = ""  # 更新当前逻辑中的 last error
        while time.time() < deadline:  # 在条件满足时持续循环处理
            if process.poll() is not None:  # 根据当前条件决定是否进入对应业务分支
                output = process.stdout.read() if process.stdout else ""  # 创建内存输出缓冲区
                raise RuntimeError(f"API server exited early with code {process.returncode}\n{output}")  # 执行当前控制流分支
            try:  # 尝试执行可能依赖外部服务或数据库的逻辑
                response = requests.get(f"{base_url}/health", timeout=1)  # 保存当前分支生成的响应对象
                if response.status_code == 200:  # 根据状态参数决定是否追加筛选条件
                    break  # 满足退出条件后立即结束当前循环
                last_error = f"HTTP {response.status_code}: {response.text[:500]}"  # 更新当前逻辑中的 last error
            except requests.RequestException as exc:  # 捕获异常并执行降级或错误处理逻辑
                last_error = str(exc)  # 更新当前逻辑中的 last error
            time.sleep(0.5)  # 执行当前业务步骤并推进后续处理
        else:  # 处理其他未命中的业务情况
            process.terminate()  # 执行当前业务步骤并推进后续处理
            output = process.stdout.read() if process.stdout else ""  # 创建内存输出缓冲区
            raise RuntimeError(f"API server did not become ready: {last_error}\n{output}")  # 执行当前控制流分支

        yield base_url  # 把当前结果交给 FastAPI 依赖或生成器继续消费
    finally:  # 无论成功失败都执行资源释放或收尾逻辑
        process.terminate()  # 执行当前业务步骤并推进后续处理
        try:  # 尝试执行可能依赖外部服务或数据库的逻辑
            process.wait(timeout=10)  # 执行当前业务步骤并推进后续处理
        except subprocess.TimeoutExpired:  # 捕获异常并执行降级或错误处理逻辑
            process.kill()  # 执行当前业务步骤并推进后续处理
            process.wait(timeout=10)  # 执行当前业务步骤并推进后续处理
        _drop_test_database()  # 执行当前业务步骤并推进后续处理


@pytest.fixture()  # 为后续函数或类声明附加装饰器配置
def client(api_base_url):  # 定义业务处理函数 client
    session = requests.Session()  # 更新当前逻辑中的 session
    session.headers.update({"X-Tenant-Code": "demo-sx"})  # 执行当前业务步骤并推进后续处理
    try:  # 尝试执行可能依赖外部服务或数据库的逻辑
        yield session  # 把当前结果交给 FastAPI 依赖或生成器继续消费
    finally:  # 无论成功失败都执行资源释放或收尾逻辑
        session.close()  # 执行当前业务步骤并推进后续处理


def assert_ok(response: requests.Response) -> dict:  # 定义业务处理函数 assert_ok
    assert response.status_code == 200, response.text  # 执行当前业务步骤并推进后续处理
    payload = response.json()  # 组装发往外部问答服务的请求载荷
    assert payload.get("success") is True, payload  # 执行当前业务步骤并推进后续处理
    return payload  # 返回当前分支整理好的结果


@pytest.fixture(scope="session")  # 为后续函数或类声明附加装饰器配置
def super_headers(api_base_url):  # 定义业务处理函数 super_headers
    response = requests.post(  # 保存当前分支生成的响应对象
        f"{api_base_url}/api/admin/login",  # 设置 post 的 字段
        json={"username": "admin", "password": "Admin@123456"},  # 设置 post 的 username
        timeout=10,  # 设置 post 的 timeout
    )  # 结束 post 的定义或组装
    assert response.status_code == 200, response.text  # 执行当前业务步骤并推进后续处理
    token = response.json()["access_token"]  # 更新当前逻辑中的 token
    return {"Authorization": f"Bearer {token}", "X-Tenant-Code": "demo-sx"}  # 返回当前分支整理好的结果


@pytest.fixture(scope="session")  # 为后续函数或类声明附加装饰器配置
def tenant_headers(api_base_url):  # 定义业务处理函数 tenant_headers
    response = requests.post(  # 保存当前分支生成的响应对象
        f"{api_base_url}/api/admin/login",  # 设置 post 的 字段
        json={"username": "tenant_admin", "password": "Tenant@123456", "tenant_code": "demo-sx"},  # 设置 post 的 username
        timeout=10,  # 设置 post 的 timeout
    )  # 结束 post 的定义或组装
    assert response.status_code == 200, response.text  # 执行当前业务步骤并推进后续处理
    token = response.json()["access_token"]  # 更新当前逻辑中的 token
    return {"Authorization": f"Bearer {token}", "X-Tenant-Code": "demo-sx"}  # 返回当前分支整理好的结果


def unique(prefix: str) -> str:  # 定义业务处理函数 unique
    return f"{prefix}-{int(time.time() * 1000)}"  # 返回当前分支整理好的结果

