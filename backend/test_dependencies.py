"""
测试所有依赖模块是否可以正常导入
"""
dependencies = [  # 更新当前逻辑中的 dependencies
    "fastapi",  # 补充列表中的 fastapi 项
    "uvicorn",  # 补充列表中的 uvicorn 项
    "sqlalchemy",  # 补充列表中的 sqlalchemy 项
    "pydantic",  # 补充列表中的 pydantic 项
    "pydantic_settings",  # 补充列表中的 pydantic settings 项
    "python_jose",  # 补充列表中的 python jose 项
    "passlib",  # 补充列表中的 passlib 项
    "python_multipart",  # 补充列表中的 python multipart 项
    "requests"  # 补充列表中的 requests 项
]  # 结束 dependencies 的定义或组装

for dep in dependencies:  # 遍历当前集合中的每一项并逐个处理
    try:  # 尝试执行可能依赖外部服务或数据库的逻辑
        __import__(dep)  # 执行当前业务步骤并推进后续处理
        print(f"{dep} 导入成功")  # 执行当前业务步骤并推进后续处理
    except ImportError as e:  # 捕获异常并执行降级或错误处理逻辑
        print(f"{dep} 导入失败: {e}")  # 执行当前业务步骤并推进后续处理
    except Exception as e:  # 捕获异常并执行降级或错误处理逻辑
        print(f"{dep} 其他错误: {e}")  # 执行当前业务步骤并推进后续处理

print("\n依赖检查完成!")  # 执行当前业务步骤并推进后续处理