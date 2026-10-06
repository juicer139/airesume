"""简历模块 schemas：分析记录的对外形态。

列表接口只暴露元信息（不含 content_text/result_json 大字段），
详情接口才返回完整内容，避免列表接口传输量爆炸。
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.analysis import AnalysisResult


class ResumeOut(BaseModel):
    """分析记录（列表/创建返回）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    status: str
    error_message: str | None = None  # failed 时前端展示失败原因
    job_description: str | None = None
    created_at: datetime


class ResumeDetail(BaseModel):
    """分析记录详情：元信息 + AI 结果 + 解析文本（报告页数据源）。"""

    id: int
    filename: str
    status: str
    error_message: str | None = None
    job_description: str | None = None
    content_text: str = ""
    created_at: datetime
    # result_json 是 dict，这里显式校验成 AnalysisResult，保证结构可信
    result: AnalysisResult | None = None
