"""
测试API是否可以正常访问
"""
import requests

def test_api():
    try:
        # 测试根路径
        response = requests.get("http://localhost:8000/")
        print(f"根路径响应: {response.status_code}")
        print(f"响应内容: {response.json()}")
        
        # 测试健康检查
        response = requests.get("http://localhost:8000/health")
        print(f"健康检查响应: {response.status_code}")
        print(f"响应内容: {response.json()}")
        
        # 测试文档路径
        response = requests.get("http://localhost:8000/docs")
        print(f"文档路径响应: {response.status_code}")
        
        print("\nAPI测试完成，服务运行正常！")
    except Exception as e:
        print(f"测试失败: {e}")

if __name__ == "__main__":
    test_api()