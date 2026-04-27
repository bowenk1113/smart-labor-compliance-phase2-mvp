"""
测试所有依赖模块是否可以正常导入
"""
dependencies = [
    "fastapi",
    "uvicorn",
    "sqlalchemy",
    "pydantic",
    "pydantic_settings",
    "python_jose",
    "passlib",
    "python_multipart",
    "requests"
]

for dep in dependencies:
    try:
        __import__(dep)
        print(f"{dep} 导入成功")
    except ImportError as e:
        print(f"{dep} 导入失败: {e}")
    except Exception as e:
        print(f"{dep} 其他错误: {e}")

print("\n依赖检查完成!")