"""AI 分析结果的 Pydantic 模型。

这是"人与 AI 的契约"：Prompt 要求 AI 输出什么结构，这里就定义什么结构。
AI 返回的 JSON 必须通过 model_validate 校验才算有效——AI 是不可靠的输入源，
绝不信任、必须校验，校验失败就重试或报错。
"""
from pydantic import BaseModel, Field


class JdMatch(BaseModel):
    """岗位 JD 匹配结果（未提供 JD 时整体为 null）。"""

    score: int = Field(ge=0, le=100, description="匹配度得分 0~100")
    matched: list[str] = Field(description="简历命中的岗位要求")
    missing: list[str] = Field(description="岗位要求但简历缺失的")


class AnalysisResult(BaseModel):
    """一次完整的简历分析结果，最终会存进 resume_analyses.result_json。"""

    completeness: int = Field(ge=0, le=100, description="内容完整性得分 0~100")
    completeness_issues: list[str] = Field(description="完整性扣分点，如缺少量化数据")
    strengths: list[str] = Field(description="简历亮点")
    weaknesses: list[str] = Field(description="不足之处")
    suggestions: list[str] = Field(description="具体可执行的优化建议")
    overall_score: int = Field(ge=0, le=100, description="综合得分 0~100")
    summary: str = Field(description="一句话总体评价")
    jd_match: JdMatch | None = Field(default=None, description="JD 匹配，未提供 JD 时为 null")
