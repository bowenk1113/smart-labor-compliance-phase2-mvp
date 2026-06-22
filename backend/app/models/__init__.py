"""数据模型包。"""  # 模块文档字符串，概述当前文件职责
from app.models.tenant import Tenant  # 导入当前业务会读写的 ORM 模型
from app.models.chat_log import ChatLog  # 导入当前业务会读写的 ORM 模型
from app.models.feedback import Feedback  # 导入当前业务会读写的 ORM 模型
from app.models.faq import FAQ  # 导入当前业务会读写的 ORM 模型
from app.models.source import Source  # 导入当前业务会读写的 ORM 模型
from app.models.knowledge_package import KnowledgePackage  # 导入当前业务会读写的 ORM 模型
from app.models.admin import Admin  # 导入当前业务会读写的 ORM 模型
from app.models.test_question import TestQuestion  # 导入当前业务会读写的 ORM 模型

__all__ = [  # 更新当前逻辑中的   all  
    "Tenant",  # 补充列表中的 Tenant 项
    "ChatLog",  # 补充列表中的 ChatLog 项
    "Feedback",  # 补充列表中的 Feedback 项
    "FAQ",  # 补充列表中的 FAQ 项
    "Source",  # 补充列表中的 Source 项
    "KnowledgePackage",  # 补充列表中的 KnowledgePackage 项
    "Admin",  # 补充列表中的 Admin 项
    "TestQuestion",  # 补充列表中的 TestQuestion 项
]  # 结束 __all__ 的定义或组装
