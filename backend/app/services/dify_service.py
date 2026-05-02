"""Dify 与本地 FAQ 的统一问答服务。"""
from __future__ import annotations

import time
from difflib import SequenceMatcher
from typing import Optional

import requests
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import settings
from app.models import FAQ, Source, Tenant
from app.schemas.chat import ChatResponse, SourceInfo, TaskInfo
from app.security import sanitize_text


DISCLAIMER = (
    "本回答用于企业合规辅助和演示，不替代正式法律意见。涉及具体待遇、金额、期限或争议处理时，"
    "请以当地人社、医保、税务等官方经办口径及企业制度最终复核为准。"
)


class ComplianceAnswerService:
    """先尝试 Dify，失败或未配置时回退到本地 FAQ。"""

    def __init__(self, db: Session, tenant: Tenant):
        self.db = db
        self.tenant = tenant

    def answer(
        self,
        question: str,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        language: str = "zh-CN",
    ) -> ChatResponse:
        question = sanitize_text(question) or ""
        start_time = int(time.time() * 1000)

        dify_key = self.tenant.dify_api_key or settings.dify_api_key
        if dify_key:
            dify_response = self._call_dify(question, dify_key, user_id, conversation_id)
            if dify_response:
                dify_response.response_time = int(time.time() * 1000) - start_time
                return dify_response

        local_response = self._answer_from_faq(question, language)
        local_response.response_time = int(time.time() * 1000) - start_time
        return local_response

    def _call_dify(
        self,
        question: str,
        api_key: str,
        user_id: Optional[str],
        conversation_id: Optional[str],
    ) -> Optional[ChatResponse]:
        try:
            payload = {
                "query": question,
                "user": user_id or "anonymous",
                "response_mode": "blocking",
                "inputs": {
                    "tenant_code": self.tenant.code,
                    "tenant_name": self.tenant.name,
                    "region": self.tenant.region,
                    "answer_style": "结构清晰、结论先行、引用来源、明确风险等级和待核验项",
                },
            }
            if conversation_id:
                payload["conversation_id"] = conversation_id

            response = requests.post(
                f"{settings.dify_base_url.rstrip('/')}/chat-messages",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=settings.dify_timeout_seconds,
            )
            if response.status_code != 200:
                return None

            data = response.json()
            metadata = data.get("metadata") or {}
            sources = []
            for resource in metadata.get("retriever_resources", []):
                sources.append(
                    SourceInfo(
                        title=resource.get("document_name") or resource.get("title") or "Dify 知识库来源",
                        url=resource.get("url"),
                        snippet=(resource.get("content") or "")[:220],
                    )
                )
            return ChatResponse(
                answer=self._normalize_answer(data.get("answer") or ""),
                sources=sources or None,
                related_tasks=self._extract_tasks(question),
                response_time=0,
                conversation_id=data.get("conversation_id"),
                provider="dify",
                risk_level=self._estimate_risk(question),
                suggestions=self._suggestions(question),
                disclaimer=DISCLAIMER,
            )
        except requests.RequestException:
            return None

    def _answer_from_faq(self, question: str, language: str) -> ChatResponse:
        faq = self._best_faq_match(question, language)
        if faq:
            answer = self._normalize_answer(faq.answer)
            source_infos = self._source_infos(faq.source_ids or [])
            return ChatResponse(
                answer=answer,
                sources=source_infos or None,
                related_tasks=self._extract_tasks(question),
                response_time=0,
                provider="local_faq",
                risk_level=faq.risk_level,
                suggestions=self._suggestions(question),
                disclaimer=DISCLAIMER,
            )

        return ChatResponse(
            answer=self._fallback_answer(question),
            sources=self._source_infos([]) or None,
            related_tasks=self._extract_tasks(question),
            response_time=0,
            provider="local_faq",
            risk_level=self._estimate_risk(question),
            suggestions=self._suggestions(question),
            disclaimer=DISCLAIMER,
        )

    def _best_faq_match(self, question: str, language: str) -> Optional[FAQ]:
        keyword = f"%{question[:80]}%"
        candidates = (
            self.db.query(FAQ)
            .filter(FAQ.tenant_id == self.tenant.id)
            .filter(or_(FAQ.language == language, FAQ.language == "zh-CN"))
            .filter(or_(FAQ.question.like(keyword), FAQ.answer.like(keyword), FAQ.category.like(keyword)))
            .limit(20)
            .all()
        )

        if not candidates:
            candidates = self.db.query(FAQ).filter(FAQ.tenant_id == self.tenant.id).all()

        best_score = 0.0
        best = None
        normalized_question = question.lower()
        for faq in candidates:
            terms = [faq.question, *(faq.aliases or []), *(faq.keywords or [])]
            score = max(SequenceMatcher(None, normalized_question, term.lower()).ratio() for term in terms if term)
            if any(term and term in question for term in terms):
                score += 0.35
            if score > best_score:
                best_score = score
                best = faq
        return best if best_score >= 0.18 else None

    def _source_infos(self, source_ids: list[int]) -> list[SourceInfo]:
        query = self.db.query(Source).filter(Source.tenant_id == self.tenant.id)
        if source_ids:
            query = query.filter(Source.id.in_(source_ids))
        else:
            query = query.order_by(Source.created_at.desc()).limit(3)
        sources = query.all()
        return [
            SourceInfo(title=item.title, url=item.url, snippet=item.description)
            for item in sources
        ]

    def _extract_tasks(self, question: str) -> list[TaskInfo]:
        if not any(word in question for word in ["仲裁", "办理", "申请", "共济", "医保"]):
            return []
        return [
            TaskInfo(
                title="合规办理建议路径",
                steps=[
                    "确认适用地区、员工身份、时间节点和企业制度版本。",
                    "准备劳动合同、考勤、工资、社保缴费或医保参保等证据材料。",
                    "通过当地人社、医保、税务等官方渠道核验最新办理入口。",
                    "对高风险事项保留书面处理记录，必要时交由 HR/法务复核。",
                ],
                url=settings.ragflow_web_url,
            )
        ]

    def _normalize_answer(self, answer: str) -> str:
        answer = sanitize_text(answer) or ""
        if DISCLAIMER not in answer:
            answer = f"{answer.strip()}\n\n风险提示：{DISCLAIMER}"
        return answer

    def _fallback_answer(self, question: str) -> str:
        risk = self._estimate_risk(question)
        return (
            "当前问题未命中已复核 FAQ，系统已按通用合规口径给出处理建议：\n"
            "1. 先确认适用地区、时间口径、员工身份、合同和企业制度版本。\n"
            "2. 涉及工资、社保、医保、假期、仲裁等事项时，应引用官方政策或经办规则，避免只凭经验答复。\n"
            "3. 对包含身份证号、手机号、银行卡号等个人信息的材料，应先脱敏再进入知识库或日志。\n"
            f"4. 本问题初步风险等级为：{risk}。建议由 HR 或法务复核后再对外确认。"
        )

    def _estimate_risk(self, question: str) -> str:
        high_words = ["仲裁", "工伤", "解除", "赔偿", "最低工资", "未签", "违法", "身份证", "手机号"]
        medium_words = ["社保", "医保", "产假", "护理假", "加班", "离职", "补缴"]
        if any(word in question for word in high_words):
            return "high"
        if any(word in question for word in medium_words):
            return "medium"
        return "low"

    def _suggestions(self, question: str) -> list[str]:
        if "产假" in question or "护理假" in question:
            return ["陕西护理假多少天？", "生育津贴和产假工资如何衔接？", "企业制度低于地方假期规定怎么办？"]
        if "仲裁" in question:
            return ["劳动仲裁时效是多久？", "仲裁申请需要哪些材料？", "员工所在地和公司所在地哪个有管辖权？"]
        if "社保" in question or "医保" in question:
            return ["新员工入职后多久要办理社保？", "居民医保断缴后还能报销吗？", "社保补缴有什么风险？"]
        return ["试用期工资可以低于最低工资吗？", "劳动合同最晚什么时候签？", "周末加班工资怎么算？"]


def check_external_services() -> dict:
    """探测本机 Dify 与 RAGFlow 服务状态。"""
    services = {
        "dify": {"name": "Dify", "url": settings.dify_base_url, "configured": bool(settings.dify_api_key)},
        "ragflow": {"name": "RAGFlow", "url": settings.ragflow_web_url, "configured": bool(settings.ragflow_api_key)},
    }
    for key, item in services.items():
        probe_url = item["url"]
        try:
            response = requests.get(probe_url, timeout=3)
            item["online"] = response.status_code < 500
            item["status_code"] = response.status_code
        except requests.RequestException:
            item["online"] = False
            item["status_code"] = None
    return services
