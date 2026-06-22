"""验收测试问题模型。"""  # 模块文档字符串，概述当前文件职责
from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text  # 导入 SQLAlchemy 查询构造与数据库能力
from sqlalchemy.orm import relationship  # 导入 SQLAlchemy 会话与 ORM 相关能力
from sqlalchemy.sql import func  # 导入 SQLAlchemy 查询构造与数据库能力

from app.database import Base  # 导入数据库依赖与全局运行配置


class TestQuestion(Base):  # 定义业务类 TestQuestion
    """用于演示和回归验证的测试问题。"""  # 类文档字符串，概述 TestQuestion 的用途

    __tablename__ = "slc_test_questions"  # 更新当前逻辑中的   tablename  

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)  # 更新当前逻辑中的 主键 ID
    tenant_id = Column(Integer, ForeignKey("slc_tenants.id", ondelete="CASCADE"), nullable=False, index=True)  # 更新当前逻辑中的 租户 ID
    question = Column(String(500), nullable=False)  # 清洗并保存用户提交的问题文本
    expected_points = Column(JSON, nullable=True)  # 更新当前逻辑中的 expected points
    category = Column(String(60), nullable=True)  # 更新当前逻辑中的 分类
    region = Column(String(80), default="陕西", nullable=False)  # 组合省市信息，作为外部问答服务的地域上下文
    difficulty = Column(String(20), default="normal", nullable=False)  # 更新当前逻辑中的 difficulty
    created_at = Column(DateTime, default=func.now(), nullable=False)  # 更新当前逻辑中的 创建时间

    tenant = relationship("Tenant", back_populates="test_questions")  # 保存当前请求实际使用的租户对象

    def __repr__(self):  # 定义业务处理函数 __repr__
        return f"<TestQuestion {self.id}: {self.question[:30]}>"  # 返回当前分支整理好的结果
