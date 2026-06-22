"""统一 API 响应工具。"""  # 模块文档字符串，概述当前文件职责
from typing import Any, Optional  # 导入当前模块运行所依赖的工具或类型


def ok(data: Any = None, message: str = "ok") -> dict:  # 定义业务处理函数 ok
    return {"success": True, "message": message, "data": data}  # 返回当前分支整理好的结果


def page(items: list, total: int, page_num: int, page_size: int, extra: Optional[dict] = None) -> dict:  # 定义业务处理函数 page
    data = {  # 整理当前接口最终要返回的数据结构
        "list": items,  # 填充返回或配置中的 list 字段
        "total": total,  # 填充返回或配置中的 total 字段
        "page": page_num,  # 填充返回或配置中的 page 字段
        "page_size": page_size,  # 填充返回或配置中的 page size 字段
    }  # 结束 data 的定义或组装
    if extra:  # 根据当前条件决定是否进入对应业务分支
        data.update(extra)  # 执行当前业务步骤并推进后续处理
    return ok(data)  # 按统一成功响应格式返回结果
