"""
Dify API 服务
"""
import os
import requests
import json
import time
from typing import Optional, Dict, Any, List
from app.schemas.chat import ChatResponse, SourceInfo, TaskInfo


# Dify API 配置
DIFY_API_KEY = os.getenv('DIFY_API_KEY', 'your-dify-api-key')
DIFY_BASE_URL = "https://api.dify.ai/v1"


class DifyService:
    """Dify API 服务类"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or DIFY_API_KEY
        self.base_url = DIFY_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def chat(self, question: str, user_id: str = None, conversation_id: str = None) -> ChatResponse:
        """
        调用 Dify Chatflow API 进行问答
        
        Args:
            question: 用户问题
            user_id: 用户ID
            conversation_id: 会话ID
        
        Returns:
            ChatResponse: 包含回答、来源、办事路径等
        """
        start_time = int(time.time() * 1000)
        
        try:
            # 构建请求
            url = f"{self.base_url}/chat-messages"
            
            payload = {
                "query": question,
                "user": user_id or "anonymous",
                "response_mode": "blocking"
            }
            
            if conversation_id:
                payload["conversation_id"] = conversation_id
            
            # 发送请求
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            response_time = int(time.time() * 1000) - start_time
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_response(data, response_time)
            else:
                # API 调用失败，返回错误信息
                return ChatResponse(
                    answer=f"抱歉，系统暂时无法回答您的问题。请稍后再试。错误码：{response.status_code}",
                    response_time=response_time
                )
                
        except requests.exceptions.Timeout:
            response_time = int(time.time() * 1000) - start_time
            return ChatResponse(
                answer="抱歉，系统响应超时。请稍后再试。",
                response_time=response_time
            )
        except Exception as e:
            response_time = int(time.time() * 1000) - start_time
            return ChatResponse(
                answer=f"抱歉，系统发生错误：{str(e)}",
                response_time=response_time
            )
    
    def _parse_response(self, data: Dict[str, Any], response_time: int) -> ChatResponse:
        """
        解析 Dify API 响应
        
        Args:
            data: API 响应数据
            response_time: 响应时间（毫秒）
        
        Returns:
            ChatResponse: 解析后的响应对象
        """
        # 提取回答
        answer = data.get("answer", "")
        
        # 提取来源（从 metadata 中获取）
        sources = []
        metadata = data.get("metadata", {})
        
        # 尝试从不同位置获取来源
        if "retriever_resources" in metadata:
            for resource in metadata["retriever_resources"]:
                source = SourceInfo(
                    title=resource.get("title", "未知来源"),
                    url=resource.get("url"),
                    snippet=resource.get("content", "")[:200]
                )
                sources.append(source)
        
        # 提取对话ID
        conversation_id = data.get("conversation_id")
        
        # 提取办事路径（如果有）
        related_tasks = []
        if "tasks" in metadata:
            for task in metadata["tasks"]:
                task_info = TaskInfo(
                    title=task.get("title", ""),
                    steps=task.get("steps", []),
                    url=task.get("url")
                )
                related_tasks.append(task_info)
        
        return ChatResponse(
            answer=answer,
            sources=sources if sources else None,
            related_tasks=related_tasks if related_tasks else None,
            response_time=response_time,
            conversation_id=conversation_id
        )
    
    def get_conversation_history(self, conversation_id: str, user_id: str = None) -> List[Dict]:
        """
        获取对话历史
        
        Args:
            conversation_id: 会话ID
            user_id: 用户ID
        
        Returns:
            List[Dict]: 对话历史列表
        """
        try:
            url = f"{self.base_url}/conversations/{conversation_id}/messages"
            
            params = {
                "user": user_id or "anonymous",
                "first_id": None,
                "limit": 20
            }
            
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
            return []
            
        except Exception as e:
            print(f"获取对话历史失败: {e}")
            return []
    
    def delete_conversation(self, conversation_id: str, user_id: str = None) -> bool:
        """
        删除对话
        
        Args:
            conversation_id: 会话ID
            user_id: 用户ID
        
        Returns:
            bool: 是否删除成功
        """
        try:
            url = f"{self.base_url}/conversations/{conversation_id}"
            
            params = {
                "user": user_id or "anonymous"
            }
            
            response = requests.delete(
                url,
                headers=self.headers,
                params=params,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"删除对话失败: {e}")
            return False


# 创建全局服务实例
dify_service = DifyService()


def get_dify_response(question: str, user_id: str = None, conversation_id: str = None) -> ChatResponse:
    """
    获取 Dify 回答的便捷函数
    
    Args:
        question: 用户问题
        user_id: 用户ID
        conversation_id: 会话ID
    
    Returns:
        ChatResponse: 回答响应
    """
    return dify_service.chat(question, user_id, conversation_id)