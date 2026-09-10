"""Product requirement and business-content generators."""

from __future__ import annotations


class DocumentProductContentMixin:
    def _generate_vision(self) -> str:
        """生成产品愿景"""
        return f"""
打造一个{self.description}的{self.platform.upper()}应用，
为用户提供简单、高效、愉悦的使用体验。

我们相信：
- **用户至上**: 一切以用户价值为导向
- **简单至上**: 复杂的事情简单化
- **体验至上**: 每个细节都精益求精
"""

    def _domain_category(self) -> str:
        """根据 self.domain 和 self.description 推断领域分类"""
        combined = f"{self.domain} {self.description}".lower()
        if any(
            w in combined
            for w in [
                "教育",
                "培训",
                "education",
                "learning",
                "课程",
                "学习",
                "school",
                "university",
                "学校",
            ]
        ):
            return "education"
        if any(
            w in combined
            for w in [
                "医疗",
                "健康",
                "health",
                "medical",
                "hospital",
                "patient",
                "诊所",
                "clinic",
                "护理",
            ]
        ):
            return "healthcare"
        if any(
            w in combined
            for w in [
                "电商",
                "商城",
                "shop",
                "store",
                "mall",
                "购物",
                "ecommerce",
                "零售",
                "retail",
            ]
        ):
            return "ecommerce"
        if any(
            w in combined
            for w in [
                "金融",
                "支付",
                "fintech",
                "banking",
                "投资",
                "交易",
                "股票",
                "基金",
                "理财",
                "finance",
            ]
        ):
            return "fintech"
        if any(
            w in combined
            for w in ["内容", "社区", "content", "community", "blog", "cms", "媒体", "资讯", "新闻"]
        ):
            return "content"
        if any(
            w in combined for w in ["saas", "平台", "管理系统", "erp", "crm", "oa", "办公", "协作"]
        ):
            return "saas"
        if any(
            w in combined for w in ["求职", "招聘", "job", "resume", "career", "简历", "hr", "人才"]
        ):
            return "recruitment"
        if any(
            w in combined for w in ["物流", "配送", "logistics", "delivery", "仓储", "supply chain"]
        ):
            return "logistics"
        if any(w in combined for w in ["餐饮", "外卖", "food", "restaurant", "点餐", "菜单"]):
            return "food"
        if any(
            w in combined for w in ["旅游", "酒店", "travel", "hotel", "booking", "景点", "民宿"]
        ):
            return "travel"
        return "general"

    def _extract_description_nouns(self) -> list[str]:
        """从 self.description 中提取关键名词用于 general 场景下的内容生成"""
        desc = self.description
        # 中文关键词提取：按常见分隔符拆分后取有意义的词
        stop_words = {
            "的",
            "了",
            "和",
            "与",
            "或",
            "在",
            "是",
            "有",
            "一个",
            "这个",
            "那个",
            "可以",
            "需要",
            "支持",
            "实现",
            "使用",
            "通过",
            "进行",
            "提供",
            "包括",
            "a",
            "an",
            "the",
            "is",
            "are",
            "for",
            "to",
            "and",
            "or",
            "with",
            "that",
            "this",
        }
        tokens: list[str] = []
        # 按空格和标点拆分
        import re

        parts = re.split(r"[\s,，。、；;：:！!？?\-/\\|（）()\[\]{}]+", desc)
        for part in parts:
            part = part.strip()
            if len(part) >= 2 and part.lower() not in stop_words:
                tokens.append(part)
        return tokens[:10]

    def _generate_target_users(self) -> str:
        """生成目标用户 - 根据领域动态生成"""
        category = self._domain_category()
        segments = {
            "education": [
                (
                    "学生用户",
                    "65%",
                    "18-30 岁",
                    "在校学生、考证学员、终身学习者",
                    "追求高效学习、需要个性化学习路径、注重学习效果反馈",
                ),
                (
                    "教师/讲师",
                    "25%",
                    "25-55 岁",
                    "在职教师、培训讲师、课程创作者",
                    "需要教学管理工具、关注学生学习数据、重视内容创作效率",
                ),
                (
                    "教务管理员",
                    "10%",
                    "30-50 岁",
                    "学校教务、培训机构运营人员",
                    "关注整体运营数据、需要排课排班功能、重视报表和统计",
                ),
            ],
            "healthcare": [
                (
                    "患者/就诊者",
                    "60%",
                    "20-70 岁",
                    "慢性病患者、体检用户、门诊就诊者",
                    "需要便捷预约挂号、关注就诊记录查询、重视隐私数据安全",
                ),
                (
                    "医护人员",
                    "30%",
                    "25-55 岁",
                    "医生、护士、药剂师",
                    "需要高效查看病历、关注诊断辅助工具、重视处方管理规范",
                ),
                (
                    "医院管理者",
                    "10%",
                    "35-55 岁",
                    "科室主任、院长、运营人员",
                    "关注科室运营指标、需要排班管理、重视医疗质量监控",
                ),
            ],
            "ecommerce": [
                (
                    "消费者/买家",
                    "70%",
                    "18-45 岁",
                    "线上购物用户、比价用户、品牌忠实用户",
                    "关注商品质量与价格、需要便捷支付与物流追踪、重视售后服务",
                ),
                (
                    "商家/卖家",
                    "20%",
                    "25-50 岁",
                    "个体商户、品牌运营、供应商",
                    "需要商品管理工具、关注订单与库存、重视销售数据分析",
                ),
                (
                    "平台运营",
                    "10%",
                    "25-40 岁",
                    "平台客服、运营专员、审核人员",
                    "关注平台整体GMV、需要纠纷处理工具、重视用户投诉管理",
                ),
            ],
            "fintech": [
                (
                    "个人投资者",
                    "55%",
                    "25-55 岁",
                    "散户投资者、理财用户、储蓄用户",
                    "关注资产安全与收益、需要实时行情与交易、重视风险提示",
                ),
                (
                    "金融顾问/分析师",
                    "30%",
                    "28-50 岁",
                    "理财规划师、基金经理、风控专员",
                    "需要专业分析工具、关注客户资产配置、重视合规审查",
                ),
                (
                    "合规与风控人员",
                    "15%",
                    "30-50 岁",
                    "合规主管、审计人员、风控专员",
                    "关注交易合规性、需要反洗钱监控、重视监管报告生成",
                ),
            ],
            "recruitment": [
                (
                    "求职者",
                    "60%",
                    "20-40 岁",
                    "应届毕业生、在职跳槽者、自由职业者",
                    "需要简历优化工具、关注职位匹配度、重视面试准备与反馈",
                ),
                (
                    "HR/招聘方",
                    "30%",
                    "25-45 岁",
                    "企业HR、猎头、招聘专员",
                    "需要高效筛选简历、关注人才库管理、重视招聘流程自动化",
                ),
                (
                    "企业管理者",
                    "10%",
                    "30-55 岁",
                    "部门主管、CEO、CTO",
                    "关注团队人才结构、需要审批招聘需求、重视人力成本控制",
                ),
            ],
            "content": [
                (
                    "内容消费者",
                    "65%",
                    "18-45 岁",
                    "阅读用户、视频观众、社区浏览者",
                    "追求高质量内容、需要个性化推荐、重视互动与社交",
                ),
                (
                    "内容创作者",
                    "25%",
                    "20-40 岁",
                    "作者、博主、KOL、自媒体运营",
                    "需要创作与发布工具、关注粉丝互动与数据、重视内容变现",
                ),
                (
                    "平台运营",
                    "10%",
                    "25-40 岁",
                    "内容审核、社区运营、数据分析师",
                    "关注内容质量管控、需要审核与推荐策略、重视社区氛围维护",
                ),
            ],
            "saas": [
                (
                    "终端用户",
                    "60%",
                    "22-45 岁",
                    "企业员工、团队成员、项目参与者",
                    "需要高效完成日常工作、关注功能易用性、重视协作体验",
                ),
                (
                    "团队管理者",
                    "25%",
                    "28-50 岁",
                    "项目经理、部门主管、团队负责人",
                    "需要团队管理与权限控制、关注工作进度与报表、重视数据安全",
                ),
                (
                    "系统管理员",
                    "15%",
                    "25-45 岁",
                    "IT管理员、运维人员、安全管理员",
                    "关注系统稳定性与安全、需要配置与集成管理、重视日志与审计",
                ),
            ],
            "logistics": [
                (
                    "发货方/商家",
                    "45%",
                    "25-50 岁",
                    "电商商家、工厂、贸易公司",
                    "需要高效发货管理、关注物流成本与时效、重视包裹追踪",
                ),
                (
                    "配送人员",
                    "35%",
                    "20-45 岁",
                    "快递员、司机、仓库管理员",
                    "需要路线规划与任务分配、关注签收确认、重视工作效率",
                ),
                (
                    "收货方/消费者",
                    "20%",
                    "18-60 岁",
                    "线上购物用户、企业收件人",
                    "关注物流状态查询、需要预约送达、重视签收便捷性",
                ),
            ],
            "food": [
                (
                    "消费者/食客",
                    "65%",
                    "18-45 岁",
                    "上班族、学生、家庭用户",
                    "关注菜品质量与价格、需要便捷点餐与配送、重视用餐体验",
                ),
                (
                    "商家/餐厅",
                    "25%",
                    "25-55 岁",
                    "餐饮老板、厨师、门店管理",
                    "需要菜单与订单管理、关注营业数据、重视库存与供应链",
                ),
                (
                    "配送骑手",
                    "10%",
                    "20-40 岁",
                    "全职骑手、兼职配送员",
                    "需要订单接单与导航、关注配送时效、重视收入统计",
                ),
            ],
            "travel": [
                (
                    "旅行者/游客",
                    "65%",
                    "20-55 岁",
                    "自由行用户、商务出差、家庭游客",
                    "需要便捷预订与行程规划、关注价格与评价、重视出行体验",
                ),
                (
                    "供应商/商家",
                    "25%",
                    "30-55 岁",
                    "酒店经营者、景区管理、旅行社",
                    "需要房态与库存管理、关注订单与营收、重视用户评价",
                ),
                (
                    "平台运营",
                    "10%",
                    "25-40 岁",
                    "运营专员、客服、数据分析",
                    "关注平台交易数据、需要供应商管理、重视用户投诉处理",
                ),
            ],
        }

        if category in segments:
            user_list = segments[category]
        else:
            # general: 从描述中推断
            nouns = self._extract_description_nouns()
            desc_hint = f"（基于 {self.name} 的核心功能: {self.description[:80]}）"
            user_list = [
                (
                    "核心用户",
                    "65%",
                    "22-40 岁",
                    f"{self.name} 的主要使用者",
                    f"直接使用 {nouns[0] if nouns else '核心功能'}、追求效率与体验、{desc_hint}",
                ),
                (
                    "管理用户",
                    "25%",
                    "28-50 岁",
                    "后台管理者、运营人员、数据分析人员",
                    f"负责 {self.name} 的内容管理与运营、关注数据指标、需要管理工具",
                ),
                (
                    "外部协作者",
                    "10%",
                    "25-45 岁",
                    "合作方、第三方集成用户、API 调用方",
                    f"通过 API 或集成方式与 {self.name} 交互、关注接口稳定性与文档",
                ),
            ]

        lines = ["\n**主要用户群体**:\n"]
        for i, (name, pct, age, role, traits) in enumerate(user_list, 1):
            lines.append(f"""{i}. **{name}** ({pct})
   - 年龄: {age}
   - 角色: {role}
   - 特征: {traits}
""")
        return "\n".join(lines)

    def _generate_value_proposition(self) -> str:
        """生成价值主张 - 根据领域和产品描述动态生成"""
        category = self._domain_category()
        propositions = {
            "education": f"""
**核心价值**:

1. **学习效率提升**: 通过个性化学习路径和智能推荐，帮助学生将知识掌握效率提升 40% 以上，告别盲目刷题和低效重复
2. **教学管理数字化**: 为教师提供一体化教学管理工具，从备课、授课到批改作业、跟踪学情，减少 60% 行政事务时间
3. **数据驱动决策**: 通过学习行为数据分析，帮助管理者精准识别教学短板、优化课程设置，提升整体教学质量
4. **随时随地学习**: 基于 {self.platform.upper()} 平台，支持碎片化学习场景，学习进度跨设备同步
""",
            "healthcare": """
**核心价值**:

1. **就医流程优化**: 将挂号-就诊-取药全流程线上化，患者平均等待时间减少 70%，告别排队难题
2. **医疗数据互通**: 打通电子病历、检查报告、处方信息，医生可在 30 秒内获取患者完整就诊历史
3. **精准诊疗辅助**: 基于历史数据和临床知识库提供诊断建议，降低误诊风险，提升诊疗质量
4. **合规安全保障**: 严格遵循医疗数据安全标准（HIPAA / 《个人信息保护法》），确保患者隐私数据全链路加密
""",
            "ecommerce": """
**核心价值**:

1. **转化率提升**: 通过个性化推荐和智能搜索，将商品发现到下单的转化率提升 35%，减少用户决策成本
2. **运营效率翻倍**: 为商家提供一站式商品管理、订单处理、库存预警工具，日均处理效率提升 50%
3. **全链路体验**: 从浏览、下单、支付到物流追踪、售后服务，每个环节都经过精心设计，NPS 目标 60+
4. **数据赋能增长**: 实时销售数据分析、用户行为洞察、智能营销建议，帮助商家科学决策
""",
            "fintech": """
**核心价值**:

1. **交易安全可靠**: 多重安全认证与实时风控系统，资金操作全链路加密，年欺诈率控制在 0.01% 以下
2. **投资决策辅助**: 实时行情数据、智能投顾建议、风险评估报告，帮助用户做出更理性的投资决策
3. **合规自动化**: 内置 KYC/AML 流程自动化、监管报告自动生成，合规工作量减少 80%
4. **资产全景视图**: 跨账户、跨资产类别的统一资产面板，一目了然掌握财务状况
""",
            "recruitment": """
**核心价值**:

1. **匹配效率提升**: 智能简历解析与职位匹配算法，将人岗匹配准确率提升至 85%，招聘周期缩短 40%
2. **求职体验优化**: 一键简历生成、智能投递建议、面试准备辅导，让求职者少走弯路
3. **招聘流程自动化**: 从职位发布、简历筛选到面试安排、录用通知，全流程线上化，HR 工作效率提升 60%
4. **人才数据洞察**: 行业薪资趋势、人才流动分析、竞争对手招聘动态，帮助企业制定更有竞争力的人才策略
""",
            "content": """
**核心价值**:

1. **内容消费效率**: 智能推荐算法匹配用户兴趣，内容发现效率提升 50%，减少信息噪音
2. **创作者赋能**: 一站式创作工具 + 数据分析面板，帮助创作者专注内容本身，粉丝增长效率提升 30%
3. **社区活力**: 优质互动机制设计，用户日均停留时长提升 40%，核心用户 7 日留存率目标 55%+
4. **内容变现通路**: 打通付费订阅、打赏、广告分成等多元变现渠道，让优质内容获得合理回报
""",
            "saas": """
**核心价值**:

1. **团队协作效率**: 统一工作平台消除信息孤岛，跨部门协作效率提升 45%，减少重复沟通
2. **流程自动化**: 将重复性工作流自动化，团队成员可将 60% 以上时间投入高价值工作
3. **数据驱动管理**: 实时项目进度、团队效能、资源利用率看板，管理者决策效率提升 50%
4. **灵活扩展**: 模块化架构支持按需启用功能，从小团队到大企业平滑扩展，无需更换系统
""",
        }

        if category in propositions:
            return propositions[category]

        # general: 基于描述生成
        nouns = self._extract_description_nouns()
        core_noun = nouns[0] if nouns else "核心功能"
        return f"""
**核心价值**:

1. **核心体验升级**: 围绕「{self.description[:40]}」的核心场景，提供比传统方案更高效、更直观的解决路径，关键操作效率提升 50%+
2. **一站式整合**: 将 {core_noun} 相关的分散工具和流程整合到统一平台，消除工具切换和数据孤岛
3. **智能化辅助**: 基于用户行为数据提供个性化建议和自动化支持，降低使用门槛和学习成本
4. **持续迭代驱动**: 内置数据分析和用户反馈闭环，确保产品持续贴合用户需求演进
"""

    def _generate_core_features(self) -> str:
        """生成核心功能"""
        # 从描述中提取业务领域关键词
        description_lower = self.description.lower()
        keywords = self._extract_tech_keywords()

        # 基础功能（所有应用都有）
        base_features = """
1. **用户认证与授权**
   - 注册/登录（邮箱/手机号）
   - 密码重置
   - JWT Token 认证
   - 第三方登录（可选）

2. **用户中心**
   - 个人资料管理
   - 账户安全设置
   - 偏好配置
"""

        # 根据业务领域生成核心功能
        business_features = ""

        # 求职招聘领域
        if any(
            word in description_lower
            for word in ["求职", "招聘", "job", "resume", "career", "简历", "职位"]
        ):
            business_features = """
3. **简历管理**
   - 在线简历创建与编辑
   - 简历模板选择
   - 简历导入（上传 PDF/Word）
   - 简历预览与导出
   - 简历智能评分与优化建议

4. **职位搜索与推荐**
   - 职位搜索（关键词/地点/薪资）
   - 智能职位推荐
   - 职位收藏与对比
   - 职位订阅通知

5. **求职助手"""
            # 如果有 AI/Agent 相关技术，添加智能功能
            if (
                keywords["ai_frameworks"]
                or keywords["agent_tools"]
                or "Multi-Agent System" in keywords["other_keywords"]
            ):
                business_features += """
   - 多 Agent 智能求职助手：
     * **简历匹配 Agent**: JD 与简历匹配度分析，识别技能差距，提供优化建议
     * **简历优化 Agent**: 自动优化简历内容，提高匹配度
     * **职位推荐 Agent**: 基于用户画像智能推荐职位
     * **面试准备 Agent**: 模拟面试，提供问题预测和回答建议
     * **薪资谈判 Agent**: 分析市场薪资，提供谈判策略
     * **职业规划 Agent**: 基于行业趋势提供职业发展建议
   - 实时对话式求职咨询
   - 智能简历投递建议"""
            else:
                business_features += """
   - 求职进度跟踪
   - 面试提醒与日程管理
   - 求职数据分析"""

        # 电商领域
        elif any(
            word in description_lower for word in ["电商", "商城", "shop", "store", "mall", "购物"]
        ):
            business_features = """
3. **商品管理**
   - 商品浏览与搜索
   - 商品分类与筛选
   - 商品详情与评价

4. **购物车与订单**
   - 购物车管理
   - 订单创建与支付
   - 物流跟踪

5. **用户中心**
   - 收藏夹
   - 浏览历史
   - 优惠券管理"""

        # 内容/社区领域
        elif any(
            word in description_lower
            for word in ["内容", "社区", "content", "community", "blog", "forum", "社交"]
        ):
            business_features = """
3. **内容管理**
   - 内容发布与编辑
   - 富文本支持
   - 图片/视频上传

4. **社交互动**
   - 点赞/评论/分享
   - 关注作者
   - 消息通知"""

        # 教育领域
        elif any(
            word in description_lower
            for word in ["教育", "培训", "education", "learning", "课程", "学习"]
        ):
            business_features = """
3. **课程管理**
   - 课程浏览与购买
   - 课程进度跟踪
   - 学习笔记

4. **学习互动**
   - 问答讨论
   - 作业提交
   - 在线测试"""

        # 通用默认
        else:
            business_features = f"""
3. **核心业务功能**
   - {self.description}
   - 数据管理与展示
   - 搜索与过滤
   - 数据导入/导出"""

        return base_features + business_features

    def _generate_extended_features(self) -> str:
        """生成扩展功能 - 根据领域生成 Phase 2 特性"""
        category = self._domain_category()
        features = {
            "education": """
1. **智能学习引擎**
   - AI 驱动的个性化学习路径推荐
   - 知识图谱可视化与薄弱点定位
   - 自适应练习题难度调节
   - 学习行为分析与效率报告

2. **互动教学升级**
   - 实时在线直播课堂
   - 互动白板与屏幕共享
   - 分组讨论与小组作业
   - 同伴互评与学习社区

3. **考试与认证体系**
   - 在线考试系统（防作弊机制）
   - 自动阅卷与成绩统计
   - 电子证书生成与验证
   - 学分管理与成绩单导出

4. **教务运营工具**
   - 智能排课与教室资源管理
   - 教师绩效评估看板
   - 家校沟通与通知系统
   - 财务对账与退费管理

5. **移动学习扩展**
   - 离线课程下载与学习
   - 碎片化学习推送（每日一练）
   - 学习打卡与激励体系
""",
            "healthcare": """
1. **远程医疗**
   - 在线问诊与视频会诊
   - 远程病情监测（可穿戴设备接入）
   - 多学科会诊协作平台
   - AI 辅助预诊与分诊

2. **智能健康管理**
   - 个性化健康档案与风险评估
   - 慢性病管理方案与用药提醒
   - 健康数据趋势分析与预警
   - 运动与饮食建议

3. **医院运营优化**
   - 床位管理与周转率优化
   - 医疗耗材与药品库存预警
   - 医保结算与费用清单
   - 满意度调查与改进追踪

4. **数据与合规**
   - 医疗数据脱敏与授权访问
   - 电子病历互联互通
   - 药品不良反应上报
   - 医疗质量指标自动采集

5. **患者服务扩展**
   - 复诊预约与随访管理
   - 检查报告在线查看与解读
   - 院内导航与排队叫号
""",
            "ecommerce": """
1. **智能营销系统**
   - 用户画像与精准营销
   - 优惠券与满减活动引擎
   - 限时秒杀与拼团功能
   - 会员等级与积分体系

2. **供应链管理**
   - 多仓库库存同步
   - 智能补货预测
   - 供应商管理与采购协同
   - 物流渠道对比与自动分单

3. **商家运营工具**
   - 店铺装修与模板编辑器
   - 多渠道（直播/社交/搜索）流量分析
   - 竞品价格监控
   - 售后工单与退换货流程

4. **社交电商**
   - 商品分享返利机制
   - 用户评价与晒单社区
   - KOL/KOC 合作管理
   - 直播带货与实时互动

5. **全球化扩展**
   - 多语言与多币种支持
   - 跨境物流与关税计算
   - 本地化支付方式接入
""",
            "fintech": """
1. **智能投顾**
   - AI 资产配置建议
   - 投资组合回测与模拟
   - 市场情绪分析与预警
   - 定投策略与自动调仓

2. **高级风控系统**
   - 实时交易异常检测
   - 反洗钱（AML）自动化审查
   - 信用评分模型
   - 欺诈行为模式识别

3. **监管合规工具**
   - 监管报告自动生成
   - KYC 文档自动化处理
   - 合规规则引擎与变更追踪
   - 审计轨迹与证据链

4. **数据分析平台**
   - 多维度财务报表
   - 实时资金流向监控
   - 客户生命周期价值分析
   - 产品收益归因分析

5. **开放银行接口**
   - 第三方账户聚合
   - 支付网关集成
   - Open API 开发者平台
""",
            "recruitment": """
1. **AI 智能匹配**
   - 简历智能解析与结构化
   - JD-简历双向匹配度评分
   - 人才推荐与被动候选人发现
   - 技能差距分析与培训建议

2. **面试流程管理**
   - 视频面试与录制回放
   - 面试评分卡与评委协同
   - 面试日程智能排期
   - 面试题库与能力模型

3. **人才运营**
   - 人才库管理与标签体系
   - 候选人关系维护（CRM）
   - 招聘渠道效果分析
   - Offer 管理与电子签约

4. **数据洞察**
   - 招聘漏斗分析
   - 行业薪资对标报告
   - 人才市场趋势洞察
   - 团队人力结构分析
""",
        }

        if category in features:
            return features[category]

        # general / other categories
        nouns = self._extract_description_nouns()
        core = nouns[0] if nouns else "核心业务"
        return f"""
1. **高级 {core} 功能**
   - {core} 数据批量导入/导出
   - 高级搜索与多维筛选
   - 自定义工作流与审批流程
   - 模板管理与快速创建

2. **协作与权限**
   - 多角色权限精细控制
   - 团队协作空间与任务分配
   - 操作审计日志与变更历史
   - 通知中心与消息订阅

3. **数据分析与报表**
   - 自定义数据看板
   - 多维度统计图表
   - 定时报告生成与邮件推送
   - 数据导出（Excel/PDF/CSV）

4. **智能化扩展**
   - 基于用户行为的智能推荐
   - 异常数据自动检测与预警
   - 自然语言搜索与查询
   - 自动化规则引擎

5. **集成与开放**
   - 第三方应用集成（钉钉/企业微信/飞书）
   - Open API 与 Webhook
   - 数据同步与 ETL 管道
"""

    def _generate_user_stories(self) -> str:
        """生成用户故事 - 根据领域生成 8-12 条具体故事"""
        category = self._domain_category()
        stories_map = {
            "education": [
                ("学生", "通过手机号或邮箱快速注册", "立即开始学习", "P0"),
                ("学生", "浏览课程目录并按分类/难度筛选", "找到适合自己水平的课程", "P0"),
                ("学生", "观看课程视频并做笔记", "高效掌握知识点", "P0"),
                ("学生", "完成课后测验并查看解析", "检验学习效果", "P0"),
                ("学生", "查看我的学习进度和统计", "了解学习情况并调整计划", "P1"),
                ("教师", "创建和发布新课程", "分享教学内容给学生", "P0"),
                ("教师", "查看学生的学习数据和成绩", "针对性地调整教学策略", "P1"),
                ("教师", "布置作业和批改学生提交", "评估学生掌握程度", "P1"),
                ("管理员", "管理用户账号和角色权限", "确保平台安全运营", "P1"),
                ("管理员", "查看平台运营数据报表", "做出运营决策", "P2"),
                ("学生", "获得课程完成证书", "证明自己的学习成果", "P2"),
                ("学生", "参与课程讨论区互动", "与同学和老师交流问题", "P2"),
            ],
            "healthcare": [
                ("患者", "在线预约挂号并选择医生", "减少到院等待时间", "P0"),
                ("患者", "查看个人就诊记录和检查报告", "了解自己的健康状况", "P0"),
                ("患者", "在线缴费和查看费用明细", "便捷完成支付流程", "P0"),
                ("医生", "查看今日接诊列表和患者病历", "高效了解患者情况", "P0"),
                ("医生", "开具电子处方并发送给药房", "规范化处方流程", "P0"),
                ("医生", "记录诊断结果和医嘱", "完善患者医疗档案", "P1"),
                ("护士", "查看护理任务和用药提醒", "按时完成护理工作", "P1"),
                ("护士", "记录患者生命体征数据", "持续监测病情变化", "P1"),
                ("管理员", "管理科室排班和医生出诊表", "合理分配医疗资源", "P1"),
                ("患者", "收到复诊提醒和用药通知", "按时就医和服药", "P2"),
                ("管理员", "查看医院运营数据和科室绩效", "优化医院管理决策", "P2"),
                ("患者", "在线咨询医生获取初步建议", "解决轻症和日常健康疑问", "P2"),
            ],
            "ecommerce": [
                ("买家", "通过关键词/分类搜索商品", "快速找到想要的商品", "P0"),
                ("买家", "查看商品详情、评价和规格", "做出购买决策", "P0"),
                ("买家", "将商品加入购物车并结算", "完成购买流程", "P0"),
                ("买家", "选择支付方式完成在线支付", "安全便捷地付款", "P0"),
                ("买家", "查看订单状态和物流轨迹", "掌握包裹配送进度", "P0"),
                ("卖家", "上架新商品并设置价格库存", "开始售卖商品", "P0"),
                ("卖家", "处理新订单并安排发货", "及时完成履约", "P0"),
                ("买家", "申请退换货并跟踪处理进度", "解决商品问题", "P1"),
                ("卖家", "查看销售数据和库存预警", "优化经营策略", "P1"),
                ("买家", "管理收货地址和常用支付方式", "简化下单流程", "P1"),
                ("买家", "收藏商品并在降价时收到通知", "以理想价格购买", "P2"),
                ("卖家", "设置优惠活动和促销规则", "提升商品销量", "P2"),
            ],
            "fintech": [
                ("投资者", "注册并完成实名认证和风险评估", "合规开通投资账户", "P0"),
                ("投资者", "查看实时行情和市场数据", "做出投资决策", "P0"),
                ("投资者", "下单买入/卖出金融产品", "执行投资操作", "P0"),
                ("投资者", "查看资产总览和持仓明细", "了解投资组合状况", "P0"),
                ("投资者", "查看交易记录和资金流水", "核对账目和报税", "P1"),
                ("顾问", "查看客户资产配置和风险偏好", "提供个性化投顾建议", "P1"),
                ("顾问", "为客户生成投资报告", "展示投资表现和策略建议", "P1"),
                ("风控人员", "查看异常交易预警", "及时发现潜在风险", "P1"),
                ("风控人员", "审核大额交易和可疑操作", "确保交易合规", "P0"),
                ("投资者", "设置价格预警和自动交易规则", "不错过投资机会", "P2"),
                ("管理员", "生成监管合规报告", "满足监管要求", "P1"),
                ("投资者", "绑定银行卡完成充值和提现", "资金便捷流转", "P0"),
            ],
            "recruitment": [
                ("求职者", "上传或在线创建个人简历", "展示自己的专业能力", "P0"),
                ("求职者", "搜索和筛选职位（地点/薪资/类型）", "找到合适的工作机会", "P0"),
                ("求职者", "一键投递简历到目标职位", "高效求职", "P0"),
                ("求职者", "查看投递状态和面试邀请", "掌握求职进度", "P0"),
                ("HR", "发布职位并设置筛选条件", "吸引目标候选人", "P0"),
                ("HR", "浏览和筛选收到的简历", "快速定位合适候选人", "P0"),
                ("HR", "安排面试并发送邀请通知", "推进招聘流程", "P1"),
                ("HR", "记录面试评价和录用决定", "团队协同招聘决策", "P1"),
                ("求职者", "获取简历优化建议和匹配度评分", "提升求职竞争力", "P1"),
                ("管理者", "查看团队招聘进度和数据看板", "把控招聘节奏", "P2"),
                ("求职者", "订阅感兴趣的职位类型通知", "第一时间获取新机会", "P2"),
                ("HR", "管理人才库和历史候选人", "积累和盘活人才资源", "P2"),
            ],
        }

        if category in stories_map:
            stories = stories_map[category]
        else:
            # general: 基于描述生成
            nouns = self._extract_description_nouns()
            core = nouns[0] if nouns else "数据"
            second = nouns[1] if len(nouns) > 1 else "内容"
            stories = [
                ("用户", "通过邮箱或手机号快速注册", "立即开始使用产品", "P0"),
                ("用户", f"浏览和搜索{core}", f"快速找到目标{core}", "P0"),
                ("用户", f"查看{core}的详细信息", "做出操作决策", "P0"),
                ("用户", f"创建和编辑{second}", f"管理自己的{second}", "P0"),
                ("用户", "配置个人偏好和通知设置", "获得个性化体验", "P1"),
                ("管理员", "管理用户账号和权限分配", "确保平台安全运营", "P1"),
                ("管理员", f"审核和管理平台{core}", "维护内容质量", "P1"),
                ("用户", f"收藏和分享{core}", "方便后续查看和传播", "P1"),
                ("用户", f"导出{core}为 Excel/PDF", "离线查看和分析", "P2"),
                ("管理员", "查看平台运营数据和统计报表", "做出运营策略调整", "P2"),
                ("用户", "在移动端使用核心功能", "随时随地完成操作", "P2"),
                ("用户", "通过消息中心接收系统通知", "及时了解重要变更", "P2"),
            ]

        header = "\n| 作为 | 我想要 | 以便于 | 优先级 |\n|:---|:---|:---|:---:|\n"
        rows = "".join(
            f"| {role} | {want} | {benefit} | {pri} |\n" for role, want, benefit, pri in stories
        )
        return header + rows

    def _generate_data_entities(self) -> str:
        """生成数据实体 - 根据领域生成特定实体"""
        category = self._domain_category()
        # 通用的用户实体
        user_entity = """
### User（用户）

**属性**:
- id (UUID, PK) - 用户唯一标识
- username (string, unique) - 用户名
- email (string, unique) - 邮箱
- phone (string, unique, nullable) - 手机号
- password_hash (string) - 密码哈希
- avatar_url (string, nullable) - 头像地址
- role (enum) - 角色类型
- status (enum: active/inactive/banned) - 账户状态
- created_at (datetime) - 创建时间
- updated_at (datetime) - 更新时间
"""

        domain_entities = {
            "education": """
### Course（课程）

**属性**:
- id (UUID, PK) - 课程唯一标识
- title (string) - 课程名称
- description (text) - 课程描述
- instructor_id (UUID, FK -> User) - 讲师ID
- category_id (UUID, FK -> Category) - 分类ID
- cover_image (string) - 封面图URL
- difficulty (enum: beginner/intermediate/advanced) - 难度级别
- price (decimal) - 课程价格
- duration_hours (float) - 总时长（小时）
- student_count (int) - 学员数量
- rating (float) - 综合评分
- status (enum: draft/published/archived) - 发布状态
- created_at (datetime) - 创建时间

### Lesson（课时）

**属性**:
- id (UUID, PK) - 课时唯一标识
- course_id (UUID, FK -> Course) - 所属课程
- title (string) - 课时标题
- content_type (enum: video/text/quiz) - 内容类型
- content_url (string) - 内容资源URL
- duration_minutes (int) - 时长（分钟）
- sort_order (int) - 排序序号
- is_free_preview (boolean) - 是否免费试看

### Enrollment（选课记录）

**属性**:
- id (UUID, PK) - 记录唯一标识
- user_id (UUID, FK -> User) - 学员ID
- course_id (UUID, FK -> Course) - 课程ID
- enrolled_at (datetime) - 选课时间
- payment_amount (decimal) - 支付金额
- status (enum: active/completed/refunded) - 状态
- completed_at (datetime, nullable) - 完成时间

### Progress（学习进度）

**属性**:
- id (UUID, PK) - 记录唯一标识
- user_id (UUID, FK -> User) - 学员ID
- lesson_id (UUID, FK -> Lesson) - 课时ID
- progress_percent (float) - 完成百分比
- last_position (int) - 上次播放位置（秒）
- is_completed (boolean) - 是否完成
- updated_at (datetime) - 更新时间

### Quiz（测验）

**属性**:
- id (UUID, PK) - 测验唯一标识
- lesson_id (UUID, FK -> Lesson) - 所属课时
- title (string) - 测验标题
- questions (JSON) - 题目列表
- pass_score (int) - 及格分数
- time_limit_minutes (int, nullable) - 限时（分钟）

### Certificate（证书）

**属性**:
- id (UUID, PK) - 证书唯一标识
- user_id (UUID, FK -> User) - 学员ID
- course_id (UUID, FK -> Course) - 课程ID
- certificate_no (string, unique) - 证书编号
- issued_at (datetime) - 颁发时间
- verify_url (string) - 验证链接
""",
            "healthcare": """
### Patient（患者）

**属性**:
- id (UUID, PK) - 患者唯一标识
- user_id (UUID, FK -> User) - 关联用户账户
- medical_record_no (string, unique) - 病历号
- gender (enum: male/female/other) - 性别
- date_of_birth (date) - 出生日期
- blood_type (enum) - 血型
- allergy_info (text, nullable) - 过敏信息
- emergency_contact (string) - 紧急联系人
- emergency_phone (string) - 紧急联系电话
- insurance_info (JSON, nullable) - 医保信息

### Doctor（医生）

**属性**:
- id (UUID, PK) - 医生唯一标识
- user_id (UUID, FK -> User) - 关联用户账户
- department_id (UUID, FK -> Department) - 所属科室
- license_no (string, unique) - 执业证号
- title (enum: resident/attending/associate_chief/chief) - 职称
- specialization (string) - 专长领域
- consultation_fee (decimal) - 挂号费
- is_available (boolean) - 是否出诊

### Department（科室）

**属性**:
- id (UUID, PK) - 科室唯一标识
- name (string) - 科室名称
- description (text) - 科室描述
- location (string) - 位置楼层
- head_doctor_id (UUID, FK -> Doctor, nullable) - 科主任

### Appointment（预约挂号）

**属性**:
- id (UUID, PK) - 预约唯一标识
- patient_id (UUID, FK -> Patient) - 患者ID
- doctor_id (UUID, FK -> Doctor) - 医生ID
- appointment_date (date) - 预约日期
- time_slot (string) - 时段
- status (enum: pending/confirmed/cancelled/completed/no_show) - 状态
- symptoms (text, nullable) - 主诉症状
- fee (decimal) - 挂号费

### MedicalRecord（就诊记录）

**属性**:
- id (UUID, PK) - 记录唯一标识
- patient_id (UUID, FK -> Patient) - 患者ID
- doctor_id (UUID, FK -> Doctor) - 医生ID
- appointment_id (UUID, FK -> Appointment) - 关联预约
- diagnosis (text) - 诊断结果
- symptoms (text) - 症状描述
- treatment_plan (text) - 治疗方案
- notes (text, nullable) - 医嘱备注
- visit_date (datetime) - 就诊时间

### Prescription（处方）

**属性**:
- id (UUID, PK) - 处方唯一标识
- medical_record_id (UUID, FK -> MedicalRecord) - 关联就诊记录
- doctor_id (UUID, FK -> Doctor) - 开方医生
- items (JSON) - 药品列表（名称/剂量/用法/数量）
- status (enum: pending/dispensed/cancelled) - 状态
- total_cost (decimal) - 总费用
- issued_at (datetime) - 开方时间
""",
            "ecommerce": """
### Product（商品）

**属性**:
- id (UUID, PK) - 商品唯一标识
- seller_id (UUID, FK -> User) - 卖家ID
- category_id (UUID, FK -> Category) - 分类ID
- name (string) - 商品名称
- description (text) - 商品描述
- price (decimal) - 销售价
- original_price (decimal, nullable) - 原价
- stock (int) - 库存数量
- images (JSON) - 图片列表
- specs (JSON) - 规格参数
- rating (float) - 综合评分
- sales_count (int) - 销量
- status (enum: draft/on_sale/off_shelf/sold_out) - 状态

### Category（分类）

**属性**:
- id (UUID, PK) - 分类唯一标识
- name (string) - 分类名称
- parent_id (UUID, FK -> Category, nullable) - 父分类
- icon (string, nullable) - 图标
- sort_order (int) - 排序

### Order（订单）

**属性**:
- id (UUID, PK) - 订单唯一标识
- order_no (string, unique) - 订单编号
- buyer_id (UUID, FK -> User) - 买家ID
- total_amount (decimal) - 订单总额
- discount_amount (decimal) - 优惠金额
- shipping_fee (decimal) - 运费
- payment_amount (decimal) - 实付金额
- status (enum: pending/paid/shipped/delivered/completed/cancelled/refunding) - 状态
- address_snapshot (JSON) - 收货地址快照
- payment_method (string) - 支付方式
- paid_at (datetime, nullable) - 支付时间
- shipped_at (datetime, nullable) - 发货时间

### OrderItem（订单项）

**属性**:
- id (UUID, PK) - 订单项唯一标识
- order_id (UUID, FK -> Order) - 订单ID
- product_id (UUID, FK -> Product) - 商品ID
- product_snapshot (JSON) - 商品快照（下单时信息）
- quantity (int) - 数量
- unit_price (decimal) - 单价
- subtotal (decimal) - 小计

### Payment（支付记录）

**属性**:
- id (UUID, PK) - 支付唯一标识
- order_id (UUID, FK -> Order) - 订单ID
- payment_no (string, unique) - 支付流水号
- channel (enum: wechat/alipay/card/bank) - 支付渠道
- amount (decimal) - 支付金额
- status (enum: pending/success/failed/refunded) - 状态
- paid_at (datetime, nullable) - 完成时间

### Review（评价）

**属性**:
- id (UUID, PK) - 评价唯一标识
- product_id (UUID, FK -> Product) - 商品ID
- user_id (UUID, FK -> User) - 用户ID
- order_item_id (UUID, FK -> OrderItem) - 订单项ID
- rating (int, 1-5) - 评分
- content (text) - 评价内容
- images (JSON, nullable) - 评价图片
- created_at (datetime) - 评价时间

### Address（收货地址）

**属性**:
- id (UUID, PK) - 地址唯一标识
- user_id (UUID, FK -> User) - 用户ID
- receiver_name (string) - 收件人
- phone (string) - 联系电话
- province (string) - 省
- city (string) - 市
- district (string) - 区
- detail (string) - 详细地址
- is_default (boolean) - 是否默认
""",
            "fintech": """
### Account（账户）

**属性**:
- id (UUID, PK) - 账户唯一标识
- user_id (UUID, FK -> User) - 用户ID
- account_no (string, unique) - 账户编号
- account_type (enum: savings/investment/credit) - 账户类型
- balance (decimal) - 账户余额
- currency (string) - 币种
- risk_level (enum: conservative/moderate/aggressive) - 风险等级
- kyc_status (enum: pending/verified/rejected) - KYC 状态
- frozen (boolean) - 是否冻结
- opened_at (datetime) - 开户时间

### Transaction（交易记录）

**属性**:
- id (UUID, PK) - 交易唯一标识
- transaction_no (string, unique) - 交易流水号
- account_id (UUID, FK -> Account) - 账户ID
- type (enum: deposit/withdraw/buy/sell/transfer/dividend) - 交易类型
- amount (decimal) - 交易金额
- fee (decimal) - 手续费
- balance_after (decimal) - 交易后余额
- status (enum: pending/completed/failed/cancelled) - 状态
- description (text) - 交易描述
- created_at (datetime) - 交易时间

### Portfolio（投资组合）

**属性**:
- id (UUID, PK) - 组合唯一标识
- user_id (UUID, FK -> User) - 用户ID
- name (string) - 组合名称
- total_value (decimal) - 总市值
- total_cost (decimal) - 总成本
- return_rate (float) - 收益率
- risk_score (float) - 风险评分
- updated_at (datetime) - 更新时间

### Asset（资产持仓）

**属性**:
- id (UUID, PK) - 持仓唯一标识
- portfolio_id (UUID, FK -> Portfolio) - 组合ID
- asset_code (string) - 资产代码
- asset_name (string) - 资产名称
- asset_type (enum: stock/bond/fund/crypto/cash) - 资产类型
- quantity (decimal) - 持有数量
- avg_cost (decimal) - 平均成本
- current_price (decimal) - 当前价格
- market_value (decimal) - 当前市值
- unrealized_pnl (decimal) - 未实现盈亏

### Alert（预警规则）

**属性**:
- id (UUID, PK) - 预警唯一标识
- user_id (UUID, FK -> User) - 用户ID
- asset_code (string) - 资产代码
- condition_type (enum: price_above/price_below/change_percent) - 条件类型
- threshold (decimal) - 阈值
- is_active (boolean) - 是否启用
- triggered_at (datetime, nullable) - 最后触发时间

### ComplianceReport（合规报告）

**属性**:
- id (UUID, PK) - 报告唯一标识
- report_type (enum: daily/monthly/quarterly/suspicious) - 报告类型
- period_start (date) - 统计起始日
- period_end (date) - 统计截止日
- content (JSON) - 报告内容
- generated_by (UUID, FK -> User) - 生成人
- status (enum: draft/submitted/approved) - 状态
""",
            "recruitment": """
### Resume（简历）

**属性**:
- id (UUID, PK) - 简历唯一标识
- user_id (UUID, FK -> User) - 求职者ID
- title (string) - 简历标题
- summary (text) - 个人简介
- work_experience (JSON) - 工作经历列表
- education (JSON) - 教育经历列表
- skills (JSON) - 技能标签
- expected_salary_min (decimal) - 期望薪资下限
- expected_salary_max (decimal) - 期望薪资上限
- expected_city (string) - 期望城市
- file_url (string, nullable) - 简历附件URL
- is_public (boolean) - 是否公开
- updated_at (datetime) - 更新时间

### JobPosting（职位）

**属性**:
- id (UUID, PK) - 职位唯一标识
- company_id (UUID, FK -> User) - 企业ID
- title (string) - 职位名称
- department (string) - 所属部门
- description (text) - 职位描述
- requirements (text) - 任职要求
- salary_min (decimal) - 薪资下限
- salary_max (decimal) - 薪资上限
- city (string) - 工作城市
- employment_type (enum: full_time/part_time/contract/intern) - 工作类型
- experience_years (string) - 经验要求
- education_level (string) - 学历要求
- headcount (int) - 招聘人数
- status (enum: open/paused/closed/filled) - 状态
- expires_at (datetime) - 截止日期

### Application（投递记录）

**属性**:
- id (UUID, PK) - 投递唯一标识
- resume_id (UUID, FK -> Resume) - 简历ID
- job_id (UUID, FK -> JobPosting) - 职位ID
- applicant_id (UUID, FK -> User) - 求职者ID
- status (enum: submitted/viewed/shortlisted/interview/offer/rejected/withdrawn) - 状态
- match_score (float, nullable) - 匹配度评分
- cover_letter (text, nullable) - 求职信
- applied_at (datetime) - 投递时间

### Interview（面试）

**属性**:
- id (UUID, PK) - 面试唯一标识
- application_id (UUID, FK -> Application) - 投递ID
- round (int) - 面试轮次
- interview_type (enum: phone/video/onsite) - 面试类型
- scheduled_at (datetime) - 面试时间
- duration_minutes (int) - 预计时长
- interviewer_ids (JSON) - 面试官列表
- feedback (text, nullable) - 面试反馈
- rating (int, nullable) - 面试评分
- result (enum: pending/pass/fail, nullable) - 面试结果

### Company（企业）

**属性**:
- id (UUID, PK) - 企业唯一标识
- user_id (UUID, FK -> User) - 管理者ID
- name (string) - 企业名称
- industry (string) - 所属行业
- scale (enum: startup/small/medium/large/enterprise) - 企业规模
- description (text) - 企业介绍
- logo_url (string, nullable) - LOGO
- website (string, nullable) - 官网
- address (string) - 地址
""",
        }

        if category in domain_entities:
            return user_entity + domain_entities[category]

        # general: 从描述提取实体
        nouns = self._extract_description_nouns()
        core = nouns[0] if nouns else "Resource"
        second = nouns[1] if len(nouns) > 1 else "Category"
        third = nouns[2] if len(nouns) > 2 else "Record"

        return user_entity + f"""
### {core}（核心业务实体）

**属性**:
- id (UUID, PK) - 唯一标识
- title (string) - 名称/标题
- description (text) - 描述
- creator_id (UUID, FK -> User) - 创建者
- {second.lower()}_id (UUID, FK, nullable) - 关联分类
- status (enum: draft/active/archived) - 状态
- metadata (JSON) - 扩展属性
- tags (JSON) - 标签列表
- created_at (datetime) - 创建时间
- updated_at (datetime) - 更新时间

### {second}（分类）

**属性**:
- id (UUID, PK) - 唯一标识
- name (string) - 分类名称
- parent_id (UUID, FK -> {second}, nullable) - 父分类
- description (text, nullable) - 分类描述
- sort_order (int) - 排序
- created_at (datetime) - 创建时间

### {third}（操作记录）

**属性**:
- id (UUID, PK) - 唯一标识
- user_id (UUID, FK -> User) - 操作用户
- {core.lower()}_id (UUID, FK -> {core}) - 关联业务实体
- action (enum: create/update/delete/view/export) - 操作类型
- details (JSON) - 操作详情
- ip_address (string) - IP 地址
- created_at (datetime) - 操作时间

### Comment（评论/反馈）

**属性**:
- id (UUID, PK) - 唯一标识
- user_id (UUID, FK -> User) - 评论者
- target_id (UUID) - 目标实体ID
- target_type (string) - 目标实体类型
- content (text) - 评论内容
- rating (int, nullable) - 评分
- created_at (datetime) - 创建时间

### Notification（通知）

**属性**:
- id (UUID, PK) - 唯一标识
- user_id (UUID, FK -> User) - 接收用户
- type (enum: system/business/alert) - 通知类型
- title (string) - 通知标题
- content (text) - 通知内容
- is_read (boolean) - 是否已读
- created_at (datetime) - 创建时间
"""

    def _generate_user_journeys(self) -> str:
        """生成用户旅程 - 根据领域生成 3-4 个具体旅程"""
        category = self._domain_category()
        journeys_map = {
            "education": """
**旅程 1: 学生选课与学习**

```
浏览课程目录 → 筛选分类/难度 → 查看课程详情与评价 → 试看免费章节
     → 购买/选课 → 观看视频课程 → 完成课后测验 → 查看学习进度
     → 获得课程证书
```

痛点: 不知道哪门课适合自己的水平；学习中途容易放弃
优化: 提供学前水平测试和个性化推荐；设置学习计划和打卡提醒机制

**旅程 2: 教师创建课程**

```
登录教师端 → 创建新课程 → 编辑课程大纲 → 上传视频/文档资料
     → 设置测验题目 → 预览课程效果 → 发布上线
     → 查看学生学习数据 → 根据反馈迭代内容
```

痛点: 视频上传慢、格式兼容问题多；缺少学生反馈渠道
优化: 支持多格式断点续传；提供实时学情数据面板和问答区

**旅程 3: 管理员日常运营**

```
查看今日运营数据 → 审核新提交课程 → 处理用户反馈/投诉
     → 管理教师账号和权限 → 生成月度运营报表 → 调整推荐策略
```

痛点: 数据分散在多个系统，运营效率低
优化: 统一运营看板，关键指标实时更新，异常自动预警
""",
            "healthcare": """
**旅程 1: 患者在线就诊**

```
搜索科室/症状 → 选择医生 → 预约挂号（选择日期时段）→ 在线缴挂号费
     → 到院签到/在线候诊 → 医生问诊 → 查看诊断和医嘱
     → 取药/在线购药 → 查看电子病历
```

痛点: 挂号难、等候时间长；纸质病历查找不便
优化: 智能推荐科室和医生；电子病历随时查看，跨院互通

**旅程 2: 医生接诊工作流**

```
查看今日排班和接诊列表 → 查阅患者历史病历和检查报告
     → 问诊记录与诊断 → 开具电子处方 → 安排复查/转诊
     → 撰写病历记录 → 查看科室工作量统计
```

痛点: 病历书写耗时；历史数据调取慢
优化: 结构化病历模板快速填写；AI 辅助病历摘要和诊断提示

**旅程 3: 慢病管理**

```
建立健康档案 → 设置用药提醒 → 定期记录健康指标（血压/血糖等）
     → 查看健康趋势图 → 收到异常预警 → 在线复诊咨询
     → 调整治疗方案
```

痛点: 慢病患者缺乏持续管理，复诊不及时
优化: 自动化指标采集和趋势分析；智能复诊提醒

**旅程 4: 医院管理**

```
查看全院运营数据 → 管理科室排班 → 审核医疗质量指标
     → 处理患者投诉 → 管理医疗耗材库存 → 生成监管报告
```

痛点: 数据采集依赖人工，报表滞后
优化: 数据自动采集和实时看板；报告一键生成
""",
            "ecommerce": """
**旅程 1: 消费者购物**

```
首页/搜索发现商品 → 浏览商品列表 → 筛选（价格/品牌/评分）
     → 查看商品详情与评价 → 选择规格加入购物车
     → 确认订单与地址 → 选择支付方式付款
     → 查看物流追踪 → 确认收货 → 评价晒单
```

痛点: 搜索结果不精准，找不到想要的商品；支付流程繁琐
优化: 智能搜索与个性化推荐；一键支付和地址智能填充

**旅程 2: 商家运营**

```
登录商家后台 → 上架新商品（编辑信息/拍照/定价）→ 管理库存
     → 处理新订单 → 打包发货 → 跟踪物流
     → 处理退换货/售后 → 查看销售数据与分析
     → 参与平台促销活动
```

痛点: 多个平台库存不同步；退换货流程复杂
优化: 多平台库存统一管理；标准化售后工单流程

**旅程 3: 售后维权**

```
发起退换货申请 → 选择原因 → 提交证据（照片/描述）
     → 等待商家审核 → 寄回商品 → 确认退款
     → 评价售后服务
```

痛点: 退换货流程长、沟通成本高
优化: 标准化退换货流程；引入平台仲裁机制

**旅程 4: 首次用户转化**

```
广告/分享链接到达落地页 → 浏览爆款/活动 → 领取新人优惠券
     → 注册/手机号登录 → 首单下单 → 收到货品
     → 推送二次复购优惠
```

痛点: 新用户注册流程摩擦大，首单犹豫
优化: 一键手机号登录；新人专属优惠降低决策门槛
""",
            "fintech": """
**旅程 1: 新用户开户**

```
下载APP/访问网站 → 手机号注册 → 实名认证（身份证/人脸）
     → 风险评估问卷 → 绑定银行卡 → 首次入金
     → 浏览理财产品/行情 → 首笔投资
```

痛点: 实名认证流程复杂，等待时间长
优化: OCR 自动识别证件；人脸比对秒级验证；清晰的进度提示

**旅程 2: 日常投资交易**

```
查看资产总览 → 浏览市场行情 → 分析目标标的
     → 下单买入/卖出 → 确认交易 → 查看成交结果
     → 查看持仓变化 → 收到风险/收益提醒
```

痛点: 行情数据延迟；交易确认不及时
优化: 实时行情推送；交易状态即时反馈；关键节点push通知

**旅程 3: 资产管理与分析**

```
查看投资组合全景 → 分析收益走势 → 查看各资产表现
     → 评估风险敞口 → 调整资产配置 → 导出投资报告
```

痛点: 资产分散难以全局把控；分析工具不够直观
优化: 跨账户资产聚合面板；可视化分析图表；一键导出报告

**旅程 4: 合规风控**

```
系统自动扫描交易 → 触发异常预警 → 风控人员审核
     → 标记/冻结可疑交易 → 联系客户确认 → 解除/上报处理
     → 生成合规报告
```

痛点: 人工审核效率低，漏报风险高
优化: AI 驱动的实时异常检测；自动化分级预警
""",
            "recruitment": """
**旅程 1: 求职者找工作**

```
注册/完善简历 → 搜索职位（关键词/城市/薪资）→ 浏览职位列表
     → 查看职位详情与公司信息 → 投递简历 → 查看投递状态
     → 收到面试邀请 → 在线/现场面试 → 等待结果通知
     → 接受Offer
```

痛点: 海投低效，匹配度差；不知道面试应该准备什么
优化: AI 匹配度评分指导精准投递；提供面试题库和公司面经

**旅程 2: HR 招聘流程**

```
创建招聘需求 → 发布职位 → 收到简历 → 筛选简历（AI 辅助排序）
     → 约候选人面试 → 面试评价打分 → 团队决策
     → 发送Offer → 入职跟踪
```

痛点: 简历量大筛选耗时；面试安排协调困难
优化: AI 简历预筛选和排序；智能排期自动匹配面试官空闲时段

**旅程 3: 简历优化**

```
上传现有简历 → 获取智能评分 → 查看优化建议（内容/格式/关键词）
     → 在线编辑修改 → 选择简历模板 → 预览效果
     → 下载 PDF 版本
```

痛点: 不知道简历哪里有问题；缺少行业针对性
优化: 基于JD的关键词匹配分析；分行业的简历优化建议
""",
        }

        if category in journeys_map:
            return journeys_map[category]

        # general
        nouns = self._extract_description_nouns()
        core = nouns[0] if nouns else "核心功能"
        return f"""
**旅程 1: 新用户首次体验**

```
发现产品（搜索/推荐/分享）→ 访问首页 → 浏览核心功能介绍
     → 注册账户（手机号/邮箱/社交登录）→ 完成引导设置
     → 体验{core}核心操作 → 完成首次任务
```

痛点: 不了解产品能做什么；注册流程摩擦大
优化: 清晰的功能引导和新手教程；支持社交一键登录

**旅程 2: 核心功能使用**

```
登录 → 进入{core}模块 → 搜索/浏览目标内容
     → 查看详情 → 执行核心操作（创建/编辑/提交）
     → 确认结果 → 收到操作反馈/通知
```

痛点: 操作步骤多、路径不清晰；等待反馈时间长
优化: 减少操作步骤；实时状态反馈；常用操作一键直达

**旅程 3: 管理与分析**

```
进入管理后台 → 查看数据概览看板 → 筛选和分析关键指标
     → 处理待办事项（审核/回复/处理）→ 导出数据报表
     → 调整系统配置
```

痛点: 数据展示不直观；导出格式有限
优化: 可视化数据看板；支持多格式导出；异常数据自动预警

**旅程 4: 问题反馈与支持**

```
遇到问题 → 查看帮助文档/FAQ → 提交反馈/工单
     → 收到客服回复 → 问题解决 → 评价服务体验
```

痛点: 找不到帮助入口；回复不及时
优化: 全局帮助入口和智能搜索；工单状态实时更新
"""

    def _generate_page_structure(self) -> str:
        """生成页面结构"""
        return """
**主要页面**:

1. **登录/注册页**
   - 登录表单
   - 注册表单
   - 忘记密码

2. **首页**
   - 欢迎信息
   - 快速入口
   - 数据概览

3. **列表页**
   - 搜索栏
   - 筛选器
   - 数据列表
   - 分页器

4. **详情页**
   - 详细信息
   - 相关操作
   - 返回按钮

5. **设置页**
   - 个人资料
   - 账户安全
   - 偏好设置
"""

    def _generate_business_rules(self) -> str:
        """生成业务规则 - 根据领域生成特定规则"""
        return self._build_business_rules()

    def _build_business_rules(self) -> str:
        category = self._domain_category()
        auth_rules = (
            "\n### 认证与安全规则\n"
            "- 密码最小长度 8 位，必须包含大小写字母和数字\n"
            "- 不能包含用户名或常见弱密码\n"
            "- 连续登录失败 5 次，账户锁定 30 分钟\n"
            "- Session 超时时间 2 小时，支持续期\n"
            "- 同一账户最多 5 台设备同时在线\n"
            "- 敏感操作需二次验证\n"
        )
        if category == "education":
            return auth_rules + (
                "\n### 选课与学习规则\n"
                "- 免费课程注册即可学习，付费课程需完成支付后开通\n"
                "- 购买后 7 天内未开始学习可申请全额退款\n"
                "- 已学习超过 30% 的课程不支持退款\n"
                "- 课程学习进度自动保存，支持跨设备同步\n"
                "\n### 测验评分规则\n"
                "- 每次测验最多 3 次答题机会，取最高分\n"
                "- 综合得分达到 60 分以上方可获得课程完成证书\n"
                "- 证书编号全局唯一，支持在线验证\n"
                "\n### 讲师与内容规则\n"
                "- 讲师发布课程需经过平台审核（1-3 个工作日）\n"
                "- 课程上线后修改内容需重新提交审核\n"
                "- 讲师收入每月结算，次月 15 日前到账\n"
                "\n### 运营规则\n"
                "- 学生反馈需在 24 小时内响应\n"
                "- 课程评分低于 3.0 将自动下架\n"
            )
        if category == "healthcare":
            return auth_rules + (
                "\n### 预约挂号规则\n"
                "- 每位患者同一科室同一天限挂 1 个号\n"
                "- 预约挂号需提前 1-7 天，当日号源仅限现场\n"
                "- 累计 3 次未到院将限制预约功能 30 天\n"
                "- 取消预约需在就诊前 4 小时以上\n"
                "\n### 处方与用药规则\n"
                "- 处方有效期 3 天，超期需重新开具\n"
                "- 特殊管制药品需双人核对签字\n"
                "- 患者过敏信息必须在开方前自动校验\n"
                "\n### 数据隐私规则\n"
                "- 病历数据仅限就诊医生和授权医护访问\n"
                "- 病历查看记录全程留痕，支持审计追溯\n"
                "- 数据存储和传输必须加密（AES-256 / TLS 1.3）\n"
                "- 脱敏处理：隐藏身份证号、手机号中间 4 位\n"
                "\n### 医疗质量规则\n"
                "- 门诊病历需在就诊当日完成\n"
                "- 医疗差错事件必须在 24 小时内上报\n"
            )
        if category == "ecommerce":
            return auth_rules + (
                "\n### 订单规则\n"
                "- 订单提交后 30 分钟内未支付自动取消\n"
                "- 已支付未发货可随时取消并全额退款\n"
                "- 订单完成后 15 天内可申请售后\n"
                "\n### 退换货规则\n"
                "- 非质量问题：7 天无理由退换（未拆封）\n"
                "- 质量问题：30 天内可退换，运费由商家承担\n"
                "- 退款审核通过后 1-3 个工作日退回原支付方式\n"
                "\n### 库存规则\n"
                "- 库存低于安全线自动预警\n"
                "- 下单即锁定库存，取消/超时自动释放\n"
                "\n### 营销活动规则\n"
                "- 优惠券不可叠加使用\n"
                "- 秒杀商品限购 1 件/人\n"
                "- 拼团 24 小时内未成团自动退款\n"
                "\n### 商家规则\n"
                "- 新订单需在 48 小时内发货\n"
                "- 商家评分低于 4.0 将限制活动参与\n"
            )
        if category == "fintech":
            return auth_rules + (
                "\n### 交易规则\n"
                "- 单笔交易金额上限根据风险等级设定\n"
                "- 当日撤单次数上限 20 次\n"
                "\n### KYC 与合规规则\n"
                "- 开户必须完成实名认证（身份证 + 人脸识别）\n"
                "- 风险评估问卷必须每 2 年更新一次\n"
                "- 高风险产品仅向合格投资者开放\n"
                "- 单日转账超过 5 万元触发大额报告\n"
                "\n### 风控规则\n"
                "- 高频交易自动触发审核\n"
                "- 异地登录自动触发二次验证\n"
                "- 可疑交易 24 小时内冻结并通知客户\n"
                "\n### 资金安全规则\n"
                "- 提现必须至绑定的实名银行卡\n"
                "- 新绑定银行卡 24 小时内限额 5000 元\n"
                "- 修改交易密码后 24 小时内禁止提现\n"
                "- 资金流水保留 5 年以上\n"
            )
        if category == "recruitment":
            return auth_rules + (
                "\n### 简历与投递规则\n"
                "- 每位求职者最多创建 5 份简历\n"
                "- 同一职位限投 1 次，30 天后可重新投递\n"
                "- HR 应在 7 天内给出反馈\n"
                "\n### 职位发布规则\n"
                "- 职位信息必须包含岗位名称、职责、要求、薪资范围\n"
                "- 薪资范围必须真实\n"
                "- 职位有效期默认 30 天，可续期\n"
                "\n### 面试规则\n"
                "- 面试邀请需至少提前 24 小时发出\n"
                "- 面试评价需在面试结束 48 小时内完成\n"
                "\n### 隐私规则\n"
                "- 求职者可设置简历可见范围\n"
                "- 企业下载简历需获得求职者授权\n"
                "- 账号注销后简历数据 30 天内完全清除\n"
            )
        # general
        nouns = self._extract_description_nouns()
        core = nouns[0] if nouns else "业务数据"
        return auth_rules + (
            f"\n### {core}管理规则\n"
            f"- 创建{core}时必填字段需完成验证后才能提交\n"
            f"- {core}状态变更需记录操作日志\n"
            f"- 已发布的{core}修改需经审核后生效\n"
            f"- 删除{core}为软删除，保留 30 天后永久清除\n"
            "\n### 权限与协作规则\n"
            "- 数据访问遵循最小权限原则\n"
            "- 管理员操作日志保留 180 天\n"
            "- 批量操作需二次确认\n"
            "\n### 数据质量规则\n"
            "- 导入数据需通过格式校验和去重检查\n"
            "- 关键业务数据每日自动备份\n"
            "- 敏感字段展示时自动脱敏\n"
        )

    def _generate_acceptance_criteria(self) -> str:
        """生成验收标准 - 根据领域生成具体标准"""
        category = self._domain_category()
        common = (
            "\n以下是待筛选的候选验收，不代表新增需求或已执行结果。宿主须依据已确认范围"
            "保留适用项，并为每条原需求写清前提/触发、主体和可观察结果。"
            "模板中的技术选项、时间和性能数字仅为示例，采用前须有项目依据。\n"
            "\n### 认证与安全验收\n"
            "- [ ] 用户可以使用邮箱/手机号注册\n"
            "- [ ] 用户可以使用密码登录\n"
            "- [ ] 用户可以重置密码\n"
            "- [ ] 登录状态保持 2 小时\n"
            "- [ ] 所有受保护接口需要认证\n"
            "- [ ] 密码使用 bcrypt 加密存储\n"
            "- [ ] Token 使用 JWT 签名\n"
            "- [ ] 所有输入验证防注入\n"
            "- [ ] 敏感操作有审计日志\n"
        )
        domain = self._acceptance_criteria_for_domain(category)
        if domain:
            return common + domain
        nouns = self._extract_description_nouns()
        core = nouns[0] if nouns else "核心功能"
        return common + (
            f"\n### {core}功能验收\n"
            f"- [ ] 用户可以创建/编辑/删除{core}\n"
            f"- [ ] 用户可以搜索和筛选{core}\n"
            f"- [ ] 用户可以查看{core}详情\n"
            f"- [ ] 用户可以导出{core}数据\n"
            "\n### 管理功能验收\n"
            "- [ ] 管理员可以管理用户和权限\n"
            "- [ ] 管理员可以查看运营数据\n"
            "\n### 性能验收\n"
            "- [ ] 列表页加载 < 2s\n"
            "- [ ] 搜索响应 < 500ms\n"
            "- [ ] API P95 < 200ms\n"
            "- [ ] 支持 1000+ 并发用户\n"
        )

    def _acceptance_criteria_for_domain(self, category: str) -> str:
        """返回领域特定的验收标准"""
        criteria = {
            "education": (
                "\n### 课程功能验收\n"
                "- [ ] 学生可以浏览和搜索课程\n"
                "- [ ] 学生可以购买付费课程\n"
                "- [ ] 学生可以观看视频（倍速/断点续播）\n"
                "- [ ] 学习进度自动保存并跨设备同步\n"
                "- [ ] 学生可以完成测验并查看成绩\n"
                "- [ ] 教师可以创建和编辑课程\n"
                "- [ ] 教师可以查看学生学习数据\n"
                "- [ ] 管理员可以审核课程\n"
                "\n### 性能验收\n"
                "- [ ] 课程页面首屏加载 < 2s\n"
                "- [ ] 视频播放启动 < 3s\n"
                "- [ ] 搜索响应 < 500ms\n"
            ),
            "healthcare": (
                "\n### 患者服务验收\n"
                "- [ ] 患者可以预约挂号\n"
                "- [ ] 患者可以查看就诊记录和检查报告\n"
                "- [ ] 患者可以在线缴费\n"
                "- [ ] 医生可以查看接诊列表和病历\n"
                "- [ ] 医生可以开具电子处方\n"
                "- [ ] 处方开具时自动校验过敏信息\n"
                "\n### 合规验收\n"
                "- [ ] 病历仅授权人员可访问\n"
                "- [ ] 数据访问记录可审计\n"
                "- [ ] 敏感数据自动脱敏\n"
                "- [ ] 数据传输和存储全程加密\n"
                "\n### 性能验收\n"
                "- [ ] 挂号页面加载 < 2s\n"
                "- [ ] 病历查询响应 < 500ms\n"
            ),
            "ecommerce": (
                "\n### 购物流程验收\n"
                "- [ ] 买家可以搜索和筛选商品\n"
                "- [ ] 买家可以加入购物车并结算\n"
                "- [ ] 买家可以完成在线支付\n"
                "- [ ] 买家可以查看订单和物流\n"
                "- [ ] 买家可以申请退换货\n"
                "- [ ] 商家可以上架商品和处理订单\n"
                "\n### 交易安全验收\n"
                "- [ ] 支付流程全程加密\n"
                "- [ ] 库存扣减保证原子性\n"
                "- [ ] 超时未支付自动取消\n"
                "\n### 性能验收\n"
                "- [ ] 商品搜索响应 < 500ms\n"
                "- [ ] 下单接口响应 < 1s\n"
                "- [ ] 支持 2000+ 并发用户\n"
            ),
            "fintech": (
                "\n### 账户与交易验收\n"
                "- [ ] 用户可以完成实名认证\n"
                "- [ ] 用户可以绑定银行卡并充值/提现\n"
                "- [ ] 用户可以查看实时行情\n"
                "- [ ] 用户可以下单买入/卖出\n"
                "- [ ] 用户可以查看资产和持仓\n"
                "\n### 风控合规验收\n"
                "- [ ] 异常交易自动预警\n"
                "- [ ] 大额交易需风控审核\n"
                "- [ ] KYC 未通过无法交易\n"
                "\n### 性能验收\n"
                "- [ ] 行情数据延迟 < 1s\n"
                "- [ ] 交易下单响应 < 500ms\n"
            ),
            "recruitment": (
                "\n### 求职功能验收\n"
                "- [ ] 求职者可以创建/编辑简历\n"
                "- [ ] 求职者可以搜索和筛选职位\n"
                "- [ ] 求职者可以一键投递\n"
                "- [ ] 求职者可以查看投递状态\n"
                "\n### 招聘功能验收\n"
                "- [ ] HR 可以发布和管理职位\n"
                "- [ ] HR 可以筛选简历\n"
                "- [ ] HR 可以安排面试\n"
                "\n### 性能验收\n"
                "- [ ] 职位搜索响应 < 500ms\n"
                "- [ ] 简历解析 < 5s\n"
                "- [ ] 页面首屏加载 < 2s\n"
            ),
        }
        return criteria.get(category, "")

    def _generate_technical_risks(self) -> str:
        """生成技术风险 - 根据技术栈和领域动态生成"""
        category = self._domain_category()
        frontend = self.frontend.lower()
        backend = self.backend.lower()
        fe_risks = {
            "react": "React 组件树深层嵌套导致渲染性能下降；大量状态更新引发不必要的 re-render",
            "next": "Next.js SSR/SSG 首屏渲染策略选择不当导致 TTFB 偏高；ISR 缓存失效策略需精细调优",
            "vue": "Vue 大型列表虚拟滚动性能优化；响应式数据过深导致性能问题",
            "angular": "Angular 变更检测策略不当导致性能瓶颈；RxJS 订阅泄漏风险",
        }
        fe_risk = fe_risks.get(frontend, f"{self.frontend} 前端框架在大数据量渲染时的性能优化挑战")
        be_risks = {
            "node": "Node.js 单线程在 CPU 密集型任务下的性能瓶颈；内存泄漏排查困难",
            "python": "Python GIL 限制多核并发能力；异步与同步混用导致性能不稳定",
            "java": "Java 服务启动时间较长影响弹性伸缩效率；GC 停顿可能影响 P99 延迟",
            "go": "Go 协程泄漏导致内存持续增长；依赖管理和版本兼容性挑战",
        }
        be_risk = be_risks.get(backend, f"{self.backend} 后端在高并发场景下的稳定性挑战")
        domain_risks = {
            "education": (
                "\n### 领域特定风险\n"
                "- **视频流媒体**: 大量并发视频播放对 CDN 和带宽的压力\n"
                "- **考试防作弊**: 在线考试防切屏、防复制等机制的技术实现复杂度\n"
                "- **学习数据分析**: 海量学习行为数据的实时采集和分析挑战\n"
                "\n**缓解方案**:\n"
                "- 采用 HLS/DASH 自适应码率 + 多 CDN 调度\n"
                "- 前端全屏监控 + 后端行为分析双重防作弊\n"
                "- 引入流式计算处理实时学习数据\n"
            ),
            "healthcare": (
                "\n### 领域特定风险\n"
                "- **数据合规**: 医疗数据需严格遵循《个人信息保护法》/HIPAA，加密方案复杂度高\n"
                "- **系统可用性**: 医疗系统不允许停机，需要 99.99% 可用性保障\n"
                "- **数据互通**: 与 HIS/LIS/PACS 等医院信息系统的集成标准不统一\n"
                "\n**缓解方案**:\n"
                "- 引入合规审计框架，数据分级分类管理\n"
                "- 多活架构 + 自动故障转移 + 定期容灾演练\n"
                "- 采用 HL7 FHIR 标准接口，渐进式集成\n"
            ),
            "ecommerce": (
                "\n### 领域特定风险\n"
                "- **秒杀高并发**: 瞬时流量峰值可能是日常的 100 倍，库存扣减需保证原子性\n"
                "- **支付安全**: 需防范重复支付、支付回调伪造等攻击\n"
                "- **数据一致性**: 订单-库存-支付三方数据一致性挑战\n"
                "\n**缓解方案**:\n"
                "- Redis 预扣库存 + 消息队列异步下单 + 令牌桶限流\n"
                "- 支付签名校验 + 幂等性设计 + 对账机制\n"
                "- Saga 模式处理分布式事务\n"
            ),
            "fintech": (
                "\n### 领域特定风险\n"
                "- **交易延迟**: 行情数据和交易执行的毫秒级延迟要求\n"
                "- **资金安全**: 资金计算精度（浮点数问题）、并发交易下的余额一致性\n"
                "- **监管合规**: PCI-DSS 安全标准、反洗钱系统的持续合规成本\n"
                "\n**缓解方案**:\n"
                "- 内存数据库 + 低延迟消息队列 + 就近部署\n"
                "- 使用 Decimal 精确计算 + 乐观锁 + 事务日志\n"
                "- 引入合规引擎自动化审查\n"
            ),
            "recruitment": (
                "\n### 领域特定风险\n"
                "- **简历解析准确性**: 不同格式简历的结构化解析准确率挑战\n"
                "- **匹配算法公平性**: AI 匹配算法可能存在隐性偏见\n"
                "- **数据隐私**: 大量简历数据的存储和使用需严格合规\n"
                "\n**缓解方案**:\n"
                "- 多格式解析引擎 + NLP 实体抽取 + 人工校验兜底\n"
                "- 定期进行偏见审计和模型调优\n"
                "- 数据最小化原则 + 自动化数据生命周期管理\n"
            ),
        }
        domain_section = domain_risks.get(
            category,
            (
                "\n### 领域特定风险\n"
                f"- **业务复杂度**: {self.description[:60]} 涉及的业务规则复杂\n"
                "- **第三方依赖**: 外部服务的稳定性直接影响系统可用性\n"
                "\n**缓解方案**:\n"
                "- 领域驱动设计（DDD）明确限界上下文\n"
                "- 第三方服务封装隔离层 + 降级预案\n"
            ),
        )
        return (
            f"\n### 前端技术风险\n"
            f"- {fe_risk}\n"
            f"- {self.platform.upper()} 平台下多设备适配的测试覆盖挑战\n"
            "\n**缓解方案**:\n"
            "- 性能监控（Web Vitals / Lighthouse）+ 性能预算机制\n"
            "- 关键路径渲染优化 + 代码分割 + 懒加载\n"
            f"\n### 后端技术风险\n"
            f"- {be_risk}\n"
            "- 数据库在数据量增长后的查询性能衰减\n"
            "\n**缓解方案**:\n"
            "- 负载测试 + APM 监控 + 自动扩缩容\n"
            "- 数据库读写分离 + 合理索引 + 缓存层\n"
            f"{domain_section}"
            "\n### 基础设施风险\n"
            "- 容器编排复杂度随服务数量增加而上升\n"
            "- 多环境配置管理一致性\n"
            "\n**缓解方案**:\n"
            "- 基础设施即代码（Terraform/Pulumi）+ GitOps\n"
            "- 配置中心统一管理\n"
        )

    def _generate_business_risks(self) -> str:
        """生成业务风险 - 根据领域和市场动态生成"""
        category = self._domain_category()
        risks = {
            "education": (
                "\n### 市场竞争风险\n"
                "- 在线教育赛道竞争激烈，头部平台已占据主要市场份额\n"
                "- 免费优质教育内容对付费课程形成替代压力\n"
                "\n**缓解方案**:\n"
                "- 聚焦垂直领域差异化内容\n"
                "- 强化互动学习体验和个性化服务\n"
                "\n### 内容质量风险\n"
                "- 讲师水平参差不齐，低质课程影响平台口碑\n"
                "\n**缓解方案**:\n"
                "- 建立严格的讲师准入和课程审核机制\n"
                "\n### 用户留存风险\n"
                "- 在线学习完课率普遍偏低（行业平均 10-15%）\n"
                "\n**缓解方案**:\n"
                "- 游戏化学习设计 + 打卡激励机制\n"
            ),
            "healthcare": (
                "\n### 监管合规风险\n"
                "- 医疗信息系统需通过等级保护测评\n"
                "- 医疗数据跨境传输受法律严格限制\n"
                "- 远程医疗服务资质审批流程复杂\n"
                "\n**缓解方案**:\n"
                "- 提前规划等保合规建设\n"
                "- 数据本地化存储\n"
                "- 与有资质的医疗机构合作运营\n"
                "\n### 医患信任风险\n"
                "- 患者对线上诊疗的信任度低于面对面就诊\n"
                "\n**缓解方案**:\n"
                "- 展示医生真实资质和患者评价\n"
                "- 明确服务协议和责任边界\n"
                "\n### 推广获客风险\n"
                "- 医院/医生端的推广依赖线下关系，获客成本高\n"
                "\n**缓解方案**:\n"
                "- 从合作医院切入，以 B2B2C 模式降低获客成本\n"
            ),
            "ecommerce": (
                "\n### 市场竞争风险\n"
                "- 电商市场高度集中，新平台获客成本极高\n"
                "- 直播电商和社交电商不断分流传统电商流量\n"
                "\n**缓解方案**:\n"
                "- 聚焦垂直品类或特定人群\n"
                "- 整合社交裂变和内容电商能力\n"
                "\n### 供应链风险\n"
                "- 商品质量不可控导致退货率高\n"
                "- 物流时效不稳定\n"
                "\n**缓解方案**:\n"
                "- 建立商家准入和商品质检机制\n"
                "- 接入多家物流服务商，智能调度\n"
                "\n### 资金安全风险\n"
                "- 需取得支付牌照或与持牌机构合作\n"
                "- 恶意刷单和虚假交易影响数据真实性\n"
                "\n**缓解方案**:\n"
                "- 与持牌支付机构合作，资金托管隔离\n"
                "- 建立反作弊系统\n"
            ),
            "fintech": (
                "\n### 监管合规风险\n"
                "- 金融行业监管政策变化频繁，合规成本持续上升\n"
                "- 需要获取相关金融牌照，审批周期长\n"
                "\n**缓解方案**:\n"
                "- 设立专职合规团队\n"
                "- 优先与持牌金融机构合作\n"
                "\n### 资金安全风险\n"
                "- 系统漏洞可能导致资金损失\n"
                "- 欺诈和洗钱行为的持续威胁\n"
                "\n**缓解方案**:\n"
                "- 多层安全防护 + 定期渗透测试\n"
                "- 实时风控引擎 + AI 异常检测\n"
                "\n### 市场波动风险\n"
                "- 市场剧烈波动可能导致系统负载骤增\n"
                "\n**缓解方案**:\n"
                "- 弹性架构设计 + 自动扩缩容 + 限流降级\n"
            ),
            "recruitment": (
                "\n### 市场竞争风险\n"
                "- 招聘市场头部平台已建立强大的网络效应\n"
                "- 新平台面临双边市场冷启动问题\n"
                "\n**缓解方案**:\n"
                "- 聚焦特定行业或地域的垂直招聘\n"
                "- 通过内容营销吸引求职者和企业\n"
                "\n### 数据隐私风险\n"
                "- 简历数据属于敏感信息，泄露面临法律责任\n"
                "\n**缓解方案**:\n"
                "- 严格的数据访问权限控制和加密存储\n"
                "\n### AI 偏见风险\n"
                "- 简历筛选算法可能存在歧视性偏见\n"
                "\n**缓解方案**:\n"
                "- 定期进行算法公平性审计\n"
                "- 人工审核兜底\n"
                "\n### 用户留存风险\n"
                "- 求职者找到工作后即离开平台\n"
                "\n**缓解方案**:\n"
                "- 拓展职业发展服务，延长用户生命周期\n"
            ),
        }
        if category in risks:
            return risks[category]
        return (
            "\n### 市场竞争风险\n"
            f"- {self.name} 所在赛道可能已有成熟竞品，用户迁移成本高\n"
            "- 大厂入局风险\n"
            "\n**缓解方案**:\n"
            "- 聚焦核心差异化功能\n"
            "- 快速迭代，保持对用户需求的敏锐响应\n"
            "\n### 用户获取与留存风险\n"
            "- 获客成本和渠道不确定\n"
            "- 试用到付费转化路径需要验证\n"
            "\n**缓解方案**:\n"
            "- MVP 阶段验证核心价值假设\n"
            "- 建立用户反馈闭环\n"
            "\n### 合规风险\n"
            f"- {self.platform.upper()} 平台的数据保护法规要求\n"
            "\n**缓解方案**:\n"
            "- 数据收集最小化原则 + 用户明确授权\n"
            "\n### 团队与资源风险\n"
            f"- 技术栈（{self.frontend}/{self.backend}）的人才招聘和培养\n"
            "\n**缓解方案**:\n"
            "- 选择主流技术栈降低招聘难度\n"
            "- 建立 CI/CD 和自动化测试保障质量\n"
        )

    def _generate_dependencies(self) -> str:
        """生成依赖关系"""
        return """
### 外部依赖
- 邮件服务 (SendGrid/阿里云)
- 短信服务 (可选)
- 社交登录 (OAuth2)

### 内部依赖
- 用户服务 (提供用户信息)
- 通知服务 (发送验证消息)
- 审计服务 (记录操作日志)
"""

    def _generate_glossary(self) -> str:
        """生成术语表"""
        return """
优先引用项目已有的权威业务词表；没有独立词表时在此记录已确认的领域定义。
下面是待填充的结构，不表示已取得项目事实。只填写有依据的业务概念，不用通用技术缩写占位。

| 业务概念 | 定义与适用范围 | 别名或代码映射 | 易混淆概念与依据 |
|:---|:---|:---|:---|

如果文档和代码含义冲突，先用具体场景澄清，记录未决影响；不要猜测定义或批量改名。
已确认且映射明确的别名可以保留。需要跨文档共享时只维护一份词表，其他位置引用。
涉及设计取舍时，先按本轮未决问题的依赖澄清，再将词义、行为和技术决定分别写回原文档；
用原争议场景回读复核，尚未调整的代码差异留作待实现，不把文档更新当成代码修复。
"""

    def _generate_references(self) -> str:
        """生成参考资料"""
        return """
### 技术标准
- OWASP Top 10
- RFC 6749 (OAuth 2.0)
- RFC 7519 (JWT)

### 最佳实践
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
"""
