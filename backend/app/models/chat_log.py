"""问答记录模型。"""  # 模块文档字符串，概述当前文件职责
from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text  # 导入 SQLAlchemy 查询构造与数据库能力
from sqlalchemy.orm import relationship  # 导入 SQLAlchemy 会话与 ORM 相关能力
from sqlalchemy.sql import func  # 导入 SQLAlchemy 查询构造与数据库能力

from app.database import Base  # 导入数据库依赖与全局运行配置


class ChatLog(Base):  # 定义业务类 ChatLog
    """问答记录表"""  # 类文档字符串，概述 ChatLog 的用途
    __tablename__ = "slc_chat_logs"  # 更新当前逻辑中的   tablename  

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)  # 更新当前逻辑中的 主键 ID
    tenant_id = Column(Integer, ForeignKey("slc_tenants.id", ondelete="CASCADE"), nullable=False, index=True)  # 更新当前逻辑中的 租户 ID
    user_id = Column(String(64), nullable=True, index=True)  # 规范化本次问答对应的用户标识
    session_id = Column(String(64), nullable=True, index=True)  # 生成或复用本次问答的会话标识
    conversation_id = Column(String(128), nullable=True, index=True)  # 更新当前逻辑中的 会话 ID
    language = Column(String(12), default="zh-CN", nullable=False)  # 更新当前逻辑中的 语言代码
    question = Column(Text, nullable=False)  # 清洗并保存用户提交的问题文本
    answer = Column(Text, nullable=True)  # 更新当前逻辑中的 回答内容
    sources = Column(JSON, nullable=True)  # 更新当前逻辑中的 来源列表
    related_tasks = Column(JSON, nullable=True)  # 更新当前逻辑中的 关联任务列表
    provider = Column(String(30), default="local_faq", nullable=False)  # 更新当前逻辑中的 服务提供方
    risk_level = Column(String(20), default="medium", nullable=False)  # 更新当前逻辑中的 风险等级
    response_time = Column(Integer, nullable=True)  # 更新当前逻辑中的 响应耗时
    status = Column(String(20), default="success")  # 更新当前逻辑中的 状态
    client_ip_hash = Column(String(128), nullable=True)  # 更新当前逻辑中的 client ip hash
    created_at = Column(DateTime, default=func.now(), nullable=False)  # 更新当前逻辑中的 创建时间

    tenant = relationship("Tenant", back_populates="chat_logs")  # 保存当前请求实际使用的租户对象

    def __repr__(self):  # 定义业务处理函数 __repr__
        return f"<ChatLog {self.id}: {self.question[:30]}>"  # 返回当前分支整理好的结果
