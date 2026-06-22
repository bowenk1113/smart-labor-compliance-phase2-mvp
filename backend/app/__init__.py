"""应用包。"""  # 模块文档字符串，概述当前文件职责


def __getattr__(name: str):  # 定义业务处理函数 __getattr__
    """按需暴露 FastAPI app，避免脚本导入 app.rag 时提前加载 Web 依赖。"""  # 函数文档字符串，说明 __getattr__ 的职责

    if name == "app":  # 根据当前条件决定是否进入对应业务分支
        from app.main import app  # 导入当前模块运行所依赖的工具或类型

        return app  # 返回当前分支整理好的结果
    raise AttributeError(name)  # 执行当前控制流分支


__all__ = ["app"]  # 更新当前逻辑中的   all  
