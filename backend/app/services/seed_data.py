"""演示租户、政策来源、FAQ 与测试问题初始化。"""
from datetime import date

from sqlalchemy.orm import Session

from app.database import settings
from app.models import Admin, FAQ, KnowledgePackage, Source, Tenant, TestQuestion
from app.security import get_password_hash


SOURCE_SEED = []


FAQ_SEED = [
    {
        'faq_code': 'FAQ001',
        'question': '西安最低工资标准是多少？',
        'answer': '陕西自2026年1月1日起执行新最低工资标准。西安市新城区、碑林区、莲湖区、灞桥区、未央区、雁塔区、阎良区、临潼区、长安区、高陵区等一类区月最低工资为2376元；西安市鄠邑区、蓝田县、周至县等二类区为2250元。具体以员工实际工作地区县分类为准。',
        'category': '最低工资',
        'region': '陕西/西安',
        'keywords': ['西安最低工资是多少', '陕西最低工资'],
        'aliases': ['西安最低工资是多少', '陕西最低工资'],
        'risk_level': 'medium',
        'source_codes': ['SX001'],
    },
    {
        'faq_code': 'FAQ002',
        'question': '试用期工资可以低于最低工资吗？',
        'answer': '不可以。试用期工资可以按劳动合同法约定确定，但不得低于用人单位所在地最低工资标准。陕西地区还需结合实际工作地对应的一类区、二类区、三类区标准判断。',
        'category': '最低工资',
        'region': '全国/陕西',
        'keywords': ['试用期最低工资', '试用期工资底线'],
        'aliases': ['试用期最低工资', '试用期工资底线'],
        'risk_level': 'high',
        'source_codes': ['LAW002', 'LAW010', 'SX001'],
    },
    {
        'faq_code': 'FAQ003',
        'question': '陕西社保缴费基数上下限是多少？',
        'answer': '陕西2025年度职工基本养老保险、失业保险、工伤保险核定个人缴费基数相关参数为93003元，上限23250元/月，下限4650元/月。回答时需标注这是2025年度口径。',
        'category': '社保',
        'region': '陕西',
        'keywords': ['社保基数', '缴费基数上下限'],
        'aliases': ['社保基数', '缴费基数上下限'],
        'risk_level': 'medium',
        'source_codes': ['SX002'],
    },
    {
        'faq_code': 'FAQ004',
        'question': '新员工入职后多久要办理社保？',
        'answer': '国家规则要求用人单位依法为职工参加社会保险。具体办理时间和经办口径以当地社保、税务系统要求为准。企业实践中应在建立劳动关系后及时办理参保，避免断缴和补缴情形。',
        'category': '社保',
        'region': '全国/陕西',
        'keywords': ['入职社保', '新员工参保'],
        'aliases': ['入职社保', '新员工参保'],
        'risk_level': 'medium',
        'source_codes': ['LAW003'],
    },
    {
        'faq_code': 'FAQ005',
        'question': '离职后社保什么时候停？',
        'answer': '离职停保需按企业与员工解除或终止劳动关系的实际时间和当地社保系统申报规则办理。平台可提示 HR 按月度申报期及时处理，具体截止时间以当地社保、税务经办系统为准。',
        'category': '社保',
        'region': '陕西',
        'keywords': ['离职停保', '员工离职社保'],
        'aliases': ['离职停保', '员工离职社保'],
        'risk_level': 'medium',
        'source_codes': ['LAW003'],
    },
    {
        'faq_code': 'FAQ006',
        'question': '陕西居民医保一年交多少钱？',
        'answer': '陕西2026年度城乡居民医保个人筹资标准为每人每年400元，财政补助标准为700元。该信息为2026年度口径，后续年度需重新核验。',
        'category': '医保',
        'region': '陕西',
        'keywords': ['居民医保缴费', '陕西医保多少钱'],
        'aliases': ['居民医保缴费', '陕西医保多少钱'],
        'risk_level': 'low',
        'source_codes': ['SX004'],
    },
    {
        'faq_code': 'FAQ007',
        'question': '居民医保断缴后还能报销吗？',
        'answer': '陕西居民医保未连续参保会影响待遇享受。集中缴费期外参保按等待期规定执行，等待期内发生的就医费用不予报销；未连续参保人员还可能增加变动等待期。',
        'category': '医保',
        'region': '陕西',
        'keywords': ['医保断缴', '医保等待期'],
        'aliases': ['医保断缴', '医保等待期'],
        'risk_level': 'high',
        'source_codes': ['SX004'],
    },
    {
        'faq_code': 'FAQ008',
        'question': '陕西医保家庭共济怎么绑定？',
        'answer': '可通过陕西医保APP/小程序首页“家庭共济绑定”办理，阅读告知书后填写授权者和使用者信息，完成电子承诺签名并提交。使用时由使用人展示本人医保码结算。',
        'category': '医保',
        'region': '陕西',
        'keywords': ['家庭共济', '医保共济'],
        'aliases': ['家庭共济', '医保共济'],
        'risk_level': 'low',
        'source_codes': ['SX005'],
    },
    {
        'faq_code': 'FAQ009',
        'question': '陕西产假多少天？',
        'answer': '陕西职工符合政策生育子女的，在国家规定产假基础上增加产假60天；女职工参加孕前检查的，再增加产假10天；生育三孩的，在前述基础上再增加产假15天。',
        'category': '假期',
        'region': '陕西',
        'keywords': ['产假', '陕西生育假'],
        'aliases': ['产假', '陕西生育假'],
        'risk_level': 'medium',
        'source_codes': ['SX003'],
    },
    {
        'faq_code': 'FAQ010',
        'question': '陕西护理假多少天？',
        'answer': '陕西规定男方护理假15天；夫妻异地居住的，护理假20天；女职工生育三孩的，男方在前款基础上增加护理假10天。',
        'category': '假期',
        'region': '陕西',
        'keywords': ['陪产假', '男方护理假'],
        'aliases': ['陪产假', '男方护理假'],
        'risk_level': 'medium',
        'source_codes': ['SX003'],
    },
    {
        'faq_code': 'FAQ011',
        'question': '陕西育儿假怎么休？',
        'answer': '符合政策生育或依法收养子女的，在子女三周岁以内，每年给予父母双方各累计10天育儿假。育儿假期间按出勤对待，享受相应工资、福利待遇。',
        'category': '假期',
        'region': '陕西',
        'keywords': ['育儿假', '父母育儿假'],
        'aliases': ['育儿假', '父母育儿假'],
        'risk_level': 'medium',
        'source_codes': ['SX003'],
    },
    {
        'faq_code': 'FAQ012',
        'question': '劳动合同一定要签书面的吗？',
        'answer': '建立劳动关系应当订立书面劳动合同。已建立劳动关系未同时订立书面合同的，用人单位应在法律规定期限内补签，并注意未签书面合同可能产生的法律责任。',
        'category': '劳动合同',
        'region': '全国',
        'keywords': ['劳动合同书面', '没签合同'],
        'aliases': ['劳动合同书面', '没签合同'],
        'risk_level': 'high',
        'source_codes': ['LAW002'],
    },
    {
        'faq_code': 'FAQ013',
        'question': '员工不签劳动合同怎么办？',
        'answer': '企业应保留书面通知、沟通记录和签署安排证据，并在法定期限内依法处理。具体是否解除、如何通知，需要结合事实和当地裁判口径谨慎判断。',
        'category': '劳动合同',
        'region': '全国',
        'keywords': ['员工拒签合同', '不签合同'],
        'aliases': ['员工拒签合同', '不签合同'],
        'risk_level': 'high',
        'source_codes': ['LAW002'],
    },
    {
        'faq_code': 'FAQ014',
        'question': '企业可以用制度规定工资扣款吗？',
        'answer': '企业制度不得违反法律法规和最低工资等强制性规定。涉及扣款、赔偿、绩效扣减时，应有合法依据、民主程序、公示告知和证据支持，并避免导致正常劳动工资低于最低工资。',
        'category': '工资',
        'region': '全国/陕西',
        'keywords': ['工资扣款', '罚款制度'],
        'aliases': ['工资扣款', '罚款制度'],
        'risk_level': 'high',
        'source_codes': ['LAW001', 'LAW010', 'SX001'],
    },
    {
        'faq_code': 'FAQ015',
        'question': '员工自愿放弃社保可以吗？',
        'answer': '不建议认可员工放弃社保。参加社会保险是用人单位和职工的法定义务，企业仅凭自愿放弃声明不能免除依法参保缴费责任。',
        'category': '社保',
        'region': '全国',
        'keywords': ['放弃社保', '社保承诺书'],
        'aliases': ['放弃社保', '社保承诺书'],
        'risk_level': 'high',
        'source_codes': ['LAW003'],
    },
    {
        'faq_code': 'FAQ016',
        'question': '上班路上受伤一定算工伤吗？',
        'answer': '不能一概而论。上下班途中事故是否构成工伤，需要结合事故性质、责任认定、路线时间合理性等因素判断，并以工伤认定结论为准。',
        'category': '工伤',
        'region': '全国/陕西',
        'keywords': ['上下班途中工伤', '通勤工伤'],
        'aliases': ['上下班途中工伤', '通勤工伤'],
        'risk_level': 'high',
        'source_codes': ['LAW005'],
    },
    {
        'faq_code': 'FAQ017',
        'question': '工伤认定由谁申请？',
        'answer': '用人单位、工伤职工或其近亲属、工会组织均可能依法提出工伤认定申请。企业应及时准备劳动关系、事故经过、医疗诊断等材料，并关注法定申请期限。',
        'category': '工伤',
        'region': '全国',
        'keywords': ['谁申请工伤', '工伤申请主体'],
        'aliases': ['谁申请工伤', '工伤申请主体'],
        'risk_level': 'high',
        'source_codes': ['LAW005'],
    },
    {
        'faq_code': 'FAQ018',
        'question': '西安劳动仲裁去哪里申请？',
        'answer': '应根据争议管辖和用工所在地联系对应仲裁机构。市本级西安市劳动人事争议仲裁院电话029-87610526，地址西安市碑林区盐店街18号；区县机构见西安市人社局公开名单。',
        'category': '仲裁',
        'region': '西安',
        'keywords': ['西安仲裁', '劳动仲裁地址'],
        'aliases': ['西安仲裁', '劳动仲裁地址'],
        'risk_level': 'medium',
        'source_codes': ['XA001'],
    },
    {
        'faq_code': 'FAQ019',
        'question': '劳动仲裁收费吗？',
        'answer': '劳动争议仲裁一般不向当事人收取仲裁费。个案资料准备、律师代理等其他费用不属于仲裁机构收费，应另行判断。',
        'category': '仲裁',
        'region': '全国',
        'keywords': ['仲裁费', '劳动争议仲裁费用'],
        'aliases': ['仲裁费', '劳动争议仲裁费用'],
        'risk_level': 'low',
        'source_codes': ['LAW004'],
    },
    {
        'faq_code': 'FAQ020',
        'question': '劳动仲裁时效是多久？',
        'answer': '劳动争议申请仲裁通常适用一年的仲裁时效期间，从当事人知道或者应当知道其权利被侵害之日起计算。特殊情形需结合具体争议类型判断。',
        'category': '仲裁',
        'region': '全国',
        'keywords': ['仲裁时效', '劳动争议时效'],
        'aliases': ['仲裁时效', '劳动争议时效'],
        'risk_level': 'high',
        'source_codes': ['LAW004'],
    },
    {
        'faq_code': 'FAQ021',
        'question': '陕西居民养老保险缴费档次有哪些？',
        'answer': '陕西自2025年6月1日起，城乡居民基本养老保险个人缴费档次为每年300元、500元、800元、1000元、1500元、2000元、3000元、4000元、5000元、6000元。',
        'category': '养老',
        'region': '陕西',
        'keywords': ['居民养老缴费', '养老档次'],
        'aliases': ['居民养老缴费', '养老档次'],
        'risk_level': 'low',
        'source_codes': ['SX006'],
    },
    {
        'faq_code': 'FAQ022',
        'question': '养老保险关系什么时候需要转移？',
        'answer': '跨省或跨制度流动通常需要转移养老保险关系；企业职工省内流动就业一般不需要转移，只需办理变更登记；已领取养老金的人员通常不再转移。',
        'category': '养老',
        'region': '全国/陕西',
        'keywords': ['养老转移', '跨省转移'],
        'aliases': ['养老转移', '跨省转移'],
        'risk_level': 'medium',
        'source_codes': ['XA002'],
    },
    {
        'faq_code': 'FAQ023',
        'question': '异地就医备案在哪里办？',
        'answer': '可通过参保地医保经办窗口、国家医保服务平台APP、支付宝、微信小程序等渠道办理。国家医保服务平台APP路径为：在线办理 -> 异地备案 -> 异地就医备案申请。',
        'category': '医保',
        'region': '陕西/全国',
        'keywords': ['异地备案', '跨省就医'],
        'aliases': ['异地备案', '跨省就医'],
        'risk_level': 'medium',
        'source_codes': ['XA003'],
    },
    {
        'faq_code': 'FAQ024',
        'question': '工伤认定需要哪些基础材料？',
        'answer': '通常需要工伤认定申请表、劳动关系证明、医疗诊断证明或职业病诊断证明等基础材料。具体以当地人社部门工伤认定窗口要求为准。',
        'category': '工伤',
        'region': '全国/陕西',
        'keywords': ['工伤申请材料', '工伤认定'],
        'aliases': ['工伤申请材料', '工伤认定'],
        'risk_level': 'high',
        'source_codes': ['LAW005', 'SX008'],
    },
    {
        'faq_code': 'FAQ025',
        'question': '工伤职工转诊转院怎么办？',
        'answer': '陕西工伤职工因伤情确需转诊转院的，用人单位、工伤职工或近亲属需向经办机构提出申请，由工伤医疗协议机构提出意见，报参保地经办机构备案后转诊转院。',
        'category': '工伤',
        'region': '陕西',
        'keywords': ['工伤转院', '工伤转诊'],
        'aliases': ['工伤转院', '工伤转诊'],
        'risk_level': 'medium',
        'source_codes': ['SX008'],
    },
    {
        'faq_code': 'FAQ026',
        'question': '企业制度和地方政策冲突怎么办？',
        'answer': '企业制度不得低于国家法律法规和地方强制性规定。若企业制度与政策冲突，应优先按更有利于劳动者且符合法律规定的口径处理，并尽快修订内部制度。',
        'category': '制度',
        'region': '全国/陕西',
        'keywords': ['企业制度低于法规', '制度冲突'],
        'aliases': ['企业制度低于法规', '制度冲突'],
        'risk_level': 'high',
        'source_codes': ['LAW001', 'LAW002', 'SX003'],
    },
    {
        'faq_code': 'FAQ027',
        'question': '医保家庭共济可以跨市用吗？',
        'answer': '陕西省职工医保个人账户家庭共济已支持省内跨统筹区使用，只要共济人和被共济人都在省内参保，规则一致。',
        'category': '医保',
        'region': '陕西',
        'keywords': ['跨统筹区共济', '异地家庭共济'],
        'aliases': ['跨统筹区共济', '异地家庭共济'],
        'risk_level': 'low',
        'source_codes': ['SX005'],
    },
    {
        'faq_code': 'FAQ028',
        'question': '西安高新区劳动仲裁电话是多少？',
        'answer': '西安市人社局公开名单显示，高新区派出庭电话为029-88333687，地址为高新区锦业路一号都市之门A座1601室。',
        'category': '仲裁',
        'region': '西安高新区',
        'keywords': ['高新区仲裁', '高新区劳动仲裁'],
        'aliases': ['高新区仲裁', '高新区劳动仲裁'],
        'risk_level': 'low',
        'source_codes': ['XA001'],
    },
    {
        'faq_code': 'FAQ029',
        'question': '陕西居民医保连续参保有什么好处？',
        'answer': '陕西明确，自2025年起连续参保满4年后每连续参保1年，大病保险最高支付限额提高不低于3000元；当年未使用医保基金报销的，次年大病保险最高支付限额也提高不低于3000元。',
        'category': '医保',
        'region': '陕西',
        'keywords': ['连续参保', '大病保险限额'],
        'aliases': ['连续参保', '大病保险限额'],
        'risk_level': 'low',
        'source_codes': ['SX004'],
    },
    {
        'faq_code': 'FAQ030',
        'question': '最低工资包括加班费吗？',
        'answer': '最低工资判断需按当地最低工资规定和工资项目口径处理。实务中不应简单用包含加班费的总收入掩盖正常工作时间工资低于最低工资的风险，建议按当地人社口径核验。',
        'category': '工资',
        'region': '陕西',
        'keywords': ['最低工资组成', '加班费最低工资'],
        'aliases': ['最低工资组成', '加班费最低工资'],
        'risk_level': 'medium',
        'source_codes': ['SX001', 'LAW010'],
    },
]


TEST_QUESTIONS = [
    {
        "question": "如果员工问陕西产假和生育津贴，回答里必须提醒哪些风险？",
        "category": "假期",
        "difficulty": "normal",
        "expected_points": ["说明演示口径", "提示核验最新政策", "区分产假工资和生育津贴"],
    },
    {
        "question": "员工身份证号 610103199001011234 和手机号 13812345678 能否直接进入知识库？",
        "category": "数据安全",
        "difficulty": "edge",
        "expected_points": ["不能直接入库", "应脱敏", "避免个人敏感信息泄露"],
    },
    {
        "question": "A 租户能查看 B 租户的问答日志吗？",
        "category": "多租户",
        "difficulty": "edge",
        "expected_points": ["不能", "后端按 tenant_id 过滤", "超级管理员仅用于平台运维"],
    },
    {
        "question": "试用期工资低于最低工资有什么风险？",
        "category": "工资",
        "difficulty": "normal",
        "expected_points": ["最低工资", "劳动合同法", "补差或争议风险"],
    },
]


def _get_or_create_demo_tenant(db: Session) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.code == settings.default_tenant_code).first()
    if tenant:
        return tenant

    tenant = Tenant(
        code=settings.default_tenant_code,
        name="陕西演示企业",
        industry="企业服务 / 人力资源",
        region="陕西",
        contact_name="演示管理员",
        contact_email="demo@example.com",
        status="active",
        is_demo=True,
        notes="系统初始化演示租户，用于首期陕西用工与社保合规 MVP。",
    )
    db.add(tenant)
    db.flush()
    return tenant


def _seed_admins(db: Session, tenant: Tenant) -> None:
    existing = db.query(Admin).filter(Admin.username == settings.initial_admin_username).first()
    if not existing:
        db.add(
            Admin(
                username=settings.initial_admin_username,
                password_hash=get_password_hash(settings.initial_admin_password),
                role="super_admin",
                display_name="平台超级管理员",
                is_active=True,
            )
        )

    tenant_admin = db.query(Admin).filter(Admin.username == "tenant_admin", Admin.tenant_id == tenant.id).first()
    if not tenant_admin:
        db.add(
            Admin(
                tenant_id=tenant.id,
                username="tenant_admin",
                password_hash=get_password_hash("Tenant@123456"),
                role="tenant_admin",
                display_name="陕西演示企业管理员",
                is_active=True,
            )
        )


def _seed_sources(db: Session, tenant: Tenant) -> None:
    existing = db.query(Source).filter(Source.tenant_id == tenant.id).order_by(Source.id.asc()).all()
    by_code = {item.source_code: item for item in existing if item.source_code}
    by_title = {item.title: item for item in existing}

    for index, item in enumerate(SOURCE_SEED):
        source = by_code.get(item["source_code"]) or by_title.get(item["title"])
        if not source and index < len(existing):
            source = existing[index]
        if source:
            for field, value in item.items():
                setattr(source, field, value)
        else:
            db.add(Source(tenant_id=tenant.id, **item))
    db.flush()


def _source_ids_by_codes(db: Session, tenant: Tenant, source_codes: list[str]) -> list[int]:
    if not source_codes:
        return []
    rows = (
        db.query(Source)
        .filter(Source.tenant_id == tenant.id, Source.source_code.in_(source_codes))
        .all()
    )
    by_code = {item.source_code: item.id for item in rows}
    return [by_code[code] for code in source_codes if code in by_code]


def _seed_faqs(db: Session, tenant: Tenant) -> None:
    existing = db.query(FAQ).filter(FAQ.tenant_id == tenant.id).all()
    by_code = {item.faq_code: item for item in existing if item.faq_code}
    by_question = {item.question: item for item in existing}

    for item in FAQ_SEED:
        payload = {key: value for key, value in item.items() if key != "source_codes"}
        payload["source_ids"] = _source_ids_by_codes(db, tenant, item.get("source_codes", []))
        payload["language"] = "zh-CN"
        faq = by_code.get(payload["faq_code"]) or by_question.get(payload["question"])
        if faq:
            for field, value in payload.items():
                setattr(faq, field, value)
        else:
            db.add(FAQ(tenant_id=tenant.id, **payload))


def _seed_packages(db: Session, tenant: Tenant) -> None:
    if db.query(KnowledgePackage).filter(KnowledgePackage.tenant_id == tenant.id).count():
        return
    db.add(
        KnowledgePackage(
            tenant_id=tenant.id,
            name="陕西用工与社保合规知识包",
            region="陕西",
            version="mvp-2026.05",
            description="首期 MVP 演示知识包，包含劳动合同、工资、社保、医保、假期、仲裁等高频场景。",
            categories=["劳动合同", "工资", "社保", "医保", "假期", "仲裁", "数据安全"],
            status="active",
        )
    )


def _seed_test_questions(db: Session, tenant: Tenant) -> None:
    if db.query(TestQuestion).filter(TestQuestion.tenant_id == tenant.id).count():
        return
    for item in TEST_QUESTIONS:
        db.add(TestQuestion(tenant_id=tenant.id, region="陕西", **item))


def seed_initial_data(db: Session) -> None:
    """初始化演示数据，幂等执行。"""
    tenant = _get_or_create_demo_tenant(db)
    _seed_admins(db, tenant)
    _seed_sources(db, tenant)
    _seed_faqs(db, tenant)
    _seed_packages(db, tenant)
    _seed_test_questions(db, tenant)
    db.commit()
