"""统一 API 响应工具。"""
from typing import Any, Optional


def ok(data: Any = None, message: str = "ok") -> dict:
    return {"success": True, "message": message, "data": data}


def page(items: list, total: int, page_num: int, page_size: int, extra: Optional[dict] = None) -> dict:
    data = {
        "list": items,
        "total": total,
        "page": page_num,
        "page_size": page_size,
    }
    if extra:
        data.update(extra)
    return ok(data)
