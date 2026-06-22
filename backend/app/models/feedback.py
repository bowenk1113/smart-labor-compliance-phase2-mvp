"""反馈记录模型。"""  # 模块文档字符串，概述当前文件职责
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text  # 导入 SQLAlchemy 查询构造与数据库能力
from sqlalchemy.orm import relationship  # 导入 SQLAlchemy 会话与 ORM 相关能力
from sqlalchemy.sql import func  # 导入 SQLAlchemy 查询构造与数据库能力

from app.database import Base  # 导入数据库依赖与全局运行配置


class Feedback(Base):  # 定义业务类 Feedback
    """反馈记录表"""  # 类文档字符串，概述 Feedback 的用途
    __tablename__ = "slc_feedbacks"  # 更新当前逻辑中的   tablename  

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)  # 更新当前逻辑中的 主键 ID
    tenant_id = Column(Integer, ForeignKey("slc_tenants.id", ondelete="CASCADE"), nullable=False, index=True)  # 更新当前逻辑中的 租户 ID
    question_id = Column(Integer, ForeignKey("slc_chat_logs.id", ondelete="SET NULL"), nullable=True)  # 更新当前逻辑中的 关联问答 ID
    user_id = Column(String(64), nullable=True, index=True)  # 规范化本次问答对应的用户标识
    is_helpful = Column(Boolean, nullable=True)  # 更新当前逻辑中的 是否有帮助
    remark = Column(Text, nullable=True)  # 更新当前逻辑中的 备注
    status = Column(String(20), default="pending", nullable=False)  # 更新当前逻辑中的 状态
    created_at = Column(DateTime, default=func.now(), nullable=False)  # 更新当前逻辑中的 创建时间

    tenant = relationship("Tenant", back_populates="feedbacks")  # 保存当前请求实际使用的租户对象
    chat_log = relationship("ChatLog")  # 更新当前逻辑中的 chat log

    def __repr__(self):  # 定义业务处理函数 __repr__
        return f"<Feedback {self.id}: status={self.status}>"  # 返回当前分支整理好的结果
