"""AI 接口连通性测试：真实调用一次 AI，把返回内容原样打印出来。

用途：验证 backend/.env 里的 AI_API_KEY / AI_BASE_URL / AI_MODEL 是否可用，
以及 Prompt → LLM → JSON 解析 → Pydantic 校验这条链路是否走通。

运行（必须在 backend 目录下执行，否则读不到 .env）：
    pytest tests/test_ai_call.py

注意：
1. 会真实请求 AI 接口、消耗额度，只跑一次，不要接进 CI
2. 失败时 AIProviderError 的中文报错会直接显示，常见原因见文件末尾
"""
import time

from app.core.config import get_settings
from app.services.ai.provider import get_ai_provider

# 一段虚构简历：字段覆盖教育/工作/项目/技能，保证能触发各维度打分
SAMPLE_RESUME = """张三 / 后端开发工程师 / 3 年经验
电话：13800000000  邮箱：zhangsan@example.com

教育背景
2018.09 - 2022.06 某某大学 计算机科学与技术 本科

工作经历
2022.07 - 至今 某某科技有限公司 后端开发工程师
- 负责订单系统接口开发，日均调用量 200 万次
- 使用 FastAPI 重构老服务，接口平均响应时间从 800ms 降到 120ms

项目经历
分布式爬虫平台
- 负责调度模块设计，基于 Celery + Redis 实现任务分片
- 使抓取吞吐量提升 3 倍

技能
Python / FastAPI / MySQL / Redis / Celery / Docker
"""

# 目标岗位 JD：用于验证 jd_match 分支（不给 JD 时它应该是 null）
SAMPLE_JD = """高级后端开发工程师
1. 3 年以上 Python 后端开发经验
2. 熟悉 FastAPI、MySQL、Redis
3. 有 Celery 异步任务经验者优先
4. 有高并发系统性能优化经验
"""


def test_ai_config_ready():
    """前置检查：配置缺失时给出明确提示，而不是抛出一堆网络异常。"""
    settings = get_settings()
    assert settings.AI_API_KEY, (
        "未配置 AI_API_KEY，请在 backend/.env 中填写后重试（参考 .env.example）"
    )

    # 只打印 key 的后 4 位，避免完整密钥泄漏到日志/终端回滚记录里
    masked_key = f"****{settings.AI_API_KEY[-4:]}"
    print(f"\nAI 配置：base_url={settings.AI_BASE_URL} model={settings.AI_MODEL} key={masked_key}")


def test_ai_call():
    """真实调用一次 AI 分析接口，打印完整返回内容并校验结构。"""
    settings = get_settings()
    provider = get_ai_provider()

    print("\n" + "=" * 60)
    print(f"开始调用：{settings.AI_MODEL} @ {settings.AI_BASE_URL}")
    print("=" * 60)

    start = time.perf_counter()
    result = provider.analyze_resume(SAMPLE_RESUME, SAMPLE_JD)
    elapsed = time.perf_counter() - start

    # 打印 AI 的原始输出（已通过 JSON 解析与 Pydantic 校验）
    print(f"\n调用成功，耗时 {elapsed:.1f}s，返回内容：")
    print(result.model_dump_json(indent=2, ensure_ascii=False))

    # 关键信息单独摘出来，方便肉眼扫一眼是否合理
    print("\n---------- 摘要 ----------")
    print(f"综合得分：{result.overall_score}    完整性：{result.completeness}")
    print(f"总体评价：{result.summary}")
    if result.jd_match is not None:
        print(f"JD 匹配度：{result.jd_match.score}    命中 {len(result.jd_match.matched)} 条 / 缺失 {len(result.jd_match.missing)} 条")
    print(f"亮点 {len(result.strengths)} 条 / 不足 {len(result.weaknesses)} 条 / 建议 {len(result.suggestions)} 条")

    # 断言：返回值符合 schemas/analysis.py 约定的结构与取值范围
    assert 0 <= result.overall_score <= 100, "综合得分应为 0~100"
    assert 0 <= result.completeness <= 100, "完整性得分应为 0~100"
    assert result.summary.strip(), "总体评价不能为空"
    assert result.suggestions, "AI 应至少给出一条优化建议"
    # 传了 JD，jd_match 就必须有值，否则说明 Prompt 或 JSON 模式没生效
    assert result.jd_match is not None, "提供了 JD 却返回 jd_match=null，Prompt 未生效"
    assert 0 <= result.jd_match.score <= 100, "JD 匹配度应为 0~100"
