"""业务场景配置。

二期 MVP 只保留四个内部场景，避免场景过多导致前端选择复杂，也便于做边界检测。
每个场景都绑定 FAQ 文件、文档目录、关键词和前端展示信息。
"""

from __future__ import annotations  # 导入当前模块运行所依赖的工具或类型

from dataclasses import dataclass  # 导入当前模块运行所依赖的工具或类型
from pathlib import Path  # 导入路径处理工具，定位本地文件与目录


BACKEND_ROOT = Path(__file__).resolve().parents[2]  # 更新当前逻辑中的 BACKEND ROOT
RAG_DATA_ROOT = BACKEND_ROOT / "rag_data"  # 更新当前逻辑中的 RAG DATA ROOT


@dataclass(frozen=True)  # 为后续函数或类声明附加装饰器配置
class Scenario:  # 定义业务类 Scenario
    """一个业务场景的静态定义。"""  # 类文档字符串，概述 Scenario 的用途

    scenario_id: str  # 执行当前业务步骤并推进后续处理
    label: str  # 执行当前业务步骤并推进后续处理
    description: str  # 执行当前业务步骤并推进后续处理
    faq_csv: Path  # 执行当前业务步骤并推进后续处理
    data_dir: Path  # 执行当前业务步骤并推进后续处理
    keywords: tuple[str, ...]  # 执行当前业务步骤并推进后续处理
    source_label: str  # 执行当前业务步骤并推进后续处理


SCENARIOS: dict[str, Scenario] = {  # 更新当前逻辑中的 SCENARIOS
    "social_security": Scenario(  # 执行当前业务步骤并推进后续处理
        scenario_id="social_security",  # 更新当前逻辑中的 scenario id
        label="社保医保合规",  # 更新当前逻辑中的 label
        description="社保参保、缴费基数、医保缴费、家庭共济、异地就医等问题。",  # 更新当前逻辑中的 说明描述
        faq_csv=RAG_DATA_ROOT / "social_security" / "faq.csv",  # 更新当前逻辑中的 faq csv
        data_dir=RAG_DATA_ROOT / "social_security" / "data",  # 更新当前逻辑中的 data dir
        keywords=("社保", "社会保险", "医保", "养老", "工伤", "失业", "缴费", "参保", "断缴", "家庭共济", "异地就医", "基数"),  # 更新当前逻辑中的 关键字
        source_label="社保医保知识库",  # 更新当前逻辑中的 source label
    ),  # 执行当前业务步骤并推进后续处理
    "labor_compliance": Scenario(  # 执行当前业务步骤并推进后续处理
        scenario_id="labor_compliance",  # 更新当前逻辑中的 scenario id
        label="用工合规",  # 更新当前逻辑中的 label
        description="劳动合同、试用期、最低工资、加班、离职、制度扣款等问题。",  # 更新当前逻辑中的 说明描述
        faq_csv=RAG_DATA_ROOT / "labor_compliance" / "faq.csv",  # 更新当前逻辑中的 faq csv
        data_dir=RAG_DATA_ROOT / "labor_compliance" / "data",  # 更新当前逻辑中的 data dir
        keywords=("劳动合同", "试用期", "工资", "最低工资", "加班", "离职", "辞职", "扣款", "制度", "入职", "用工"),  # 更新当前逻辑中的 关键字
        source_label="用工合规知识库",  # 更新当前逻辑中的 source label
    ),  # 执行当前业务步骤并推进后续处理
    "leave_benefits": Scenario(  # 执行当前业务步骤并推进后续处理
        scenario_id="leave_benefits",  # 更新当前逻辑中的 scenario id
        label="假期福利",  # 更新当前逻辑中的 label
        description="产假、护理假、育儿假、年休假、病假等假期福利问题。",  # 更新当前逻辑中的 说明描述
        faq_csv=RAG_DATA_ROOT / "leave_benefits" / "faq.csv",  # 更新当前逻辑中的 faq csv
        data_dir=RAG_DATA_ROOT / "leave_benefits" / "data",  # 更新当前逻辑中的 data dir
        keywords=("产假", "护理假", "陪产假", "育儿假", "年休假", "年假", "病假", "假期", "福利", "生育"),  # 更新当前逻辑中的 关键字
        source_label="假期福利知识库",  # 更新当前逻辑中的 source label
    ),  # 执行当前业务步骤并推进后续处理
    "dispute_service": Scenario(  # 执行当前业务步骤并推进后续处理
        scenario_id="dispute_service",  # 更新当前逻辑中的 scenario id
        label="劳动争议办事",  # 更新当前逻辑中的 label
        description="劳动仲裁、争议时效、申请材料、西安仲裁机构电话地址等问题。",  # 更新当前逻辑中的 说明描述
        faq_csv=RAG_DATA_ROOT / "dispute_service" / "faq.csv",  # 更新当前逻辑中的 faq csv
        data_dir=RAG_DATA_ROOT / "dispute_service" / "data",  # 更新当前逻辑中的 data dir
        keywords=("仲裁", "劳动争议", "争议", "申请书", "证据", "材料", "仲裁院", "电话", "地址", "收费", "时效"),  # 更新当前逻辑中的 关键字
        source_label="劳动争议办事指南库",  # 更新当前逻辑中的 source label
    ),  # 执行当前业务步骤并推进后续处理
}  # 执行当前业务步骤并推进后续处理


DEFAULT_SCENARIO_ID = "social_security"  # 更新当前逻辑中的 DEFAULT SCENARIO ID


def get_scenario(scenario_id: str | None) -> Scenario:  # 定义获取 scenario 的接口或辅助函数
    """根据前端传入的场景 ID 返回场景配置。"""  # 函数文档字符串，说明 get_scenario 的职责

    return SCENARIOS.get(scenario_id or "", SCENARIOS[DEFAULT_SCENARIO_ID])  # 返回当前分支整理好的结果


def scenario_payloads() -> list[dict[str, str]]:  # 定义业务处理函数 scenario_payloads
    """返回前端场景选择器需要的轻量数据。"""  # 函数文档字符串，说明 scenario_payloads 的职责

    return [  # 返回当前分支整理好的结果
        {  # 补充列表中的 { 项
            "id": item.scenario_id,  # 补充列表中的 主键 ID 项
            "label": item.label,  # 补充列表中的 label 项
            "description": item.description,  # 补充列表中的 说明描述 项
        }  # 补充列表中的 } 项
        for item in SCENARIOS.values()  # 补充列表中的 values() 项
    ]  # 结束 返回结果 的定义或组装


def infer_scenario_id(question: str) -> tuple[str | None, int]:  # 定义业务处理函数 infer_scenario_id
    # This is the MVP's lightweight scene-intent detector.
    # It uses keyword overlap to infer which business scenario the question most likely belongs to.
    """用关键词给问题推断最可能的业务场景。"""  # 函数文档字符串，说明 infer_scenario_id 的职责

    text = question or ""  # 把文件字节内容解码成可解析的文本
    best_id: str | None = None  # 更新当前逻辑中的 best id
    best_score = 0  # 更新当前逻辑中的 best score
    for scenario in SCENARIOS.values():  # 遍历当前集合中的每一项并逐个处理
        score = sum(3 if keyword in text else 0 for keyword in scenario.keywords)  # 更新当前逻辑中的 score
        if score > best_score:  # 根据当前条件决定是否进入对应业务分支
            best_id = scenario.scenario_id  # 更新当前逻辑中的 best id
            best_score = score  # 更新当前逻辑中的 best score
    return best_id, best_score  # 返回当前分支整理好的结果
