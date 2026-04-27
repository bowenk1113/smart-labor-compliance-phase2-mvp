"""
安全模块 - JWT认证、密码加密
"""
import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.admin import Admin

# JWT配置
SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24小时

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """获取密码哈希"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """解码令牌"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def authenticate_admin(username: str, password: str) -> Optional[dict]:
    """验证管理员"""
    db = SessionLocal()
    try:
        admin = db.query(Admin).filter(Admin.username == username).first()
        if not admin:
            return None
        if not verify_password(password, admin.password_hash):
            return None
        return {
            "id": admin.id,
            "username": admin.username,
            "role": admin.role
        }
    finally:
        db.close()


def create_admin(username: str, password: str, role: str = "admin") -> bool:
    """创建管理员账号"""
    db = SessionLocal()
    try:
        # 检查是否已存在
        existing = db.query(Admin).filter(Admin.username == username).first()
        if existing:
            print(f"管理员 {username} 已存在")
            return False
        
        admin = Admin(
            username=username,
            password_hash=get_password_hash(password),
            role=role
        )
        db.add(admin)
        db.commit()
        print(f"管理员 {username} 创建成功")
        return True
    except Exception as e:
        db.rollback()
        print(f"创建管理员失败: {e}")
        return False
    finally:
        db.close()