"""
测试API是否可以正常访问
"""
import requests  # 导入 HTTP 客户端，调用外部 Dify 或 RAGFlow 服务

def test_api():  # 定义业务处理函数 test_api
    try:  # 尝试执行可能依赖外部服务或数据库的逻辑
        # 测试根路径
        response = requests.get("http://localhost:8000/")  # 保存当前分支生成的响应对象
        print(f"根路径响应: {response.status_code}")  # 执行当前业务步骤并推进后续处理
        print(f"响应内容: {response.json()}")  # 执行当前业务步骤并推进后续处理
        
        # 测试健康检查
        response = requests.get("http://localhost:8000/health")  # 保存当前分支生成的响应对象
        print(f"健康检查响应: {response.status_code}")  # 执行当前业务步骤并推进后续处理
        print(f"响应内容: {response.json()}")  # 执行当前业务步骤并推进后续处理
        
        # 测试文档路径
        response = requests.get("http://localhost:8000/docs")  # 保存当前分支生成的响应对象
        print(f"文档路径响应: {response.status_code}")  # 执行当前业务步骤并推进后续处理
        
        print("\nAPI测试完成，服务运行正常！")  # 执行当前业务步骤并推进后续处理
    except Exception as e:  # 捕获异常并执行降级或错误处理逻辑
        print(f"测试失败: {e}")  # 执行当前业务步骤并推进后续处理

if __name__ == "__main__":  # 根据当前条件决定是否进入对应业务分支
    test_api()  # 执行当前业务步骤并推进后续处理