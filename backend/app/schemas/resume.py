"""简历模块 schemas：分析记录的对外形态。

列表接口只暴露元信息（不含 content_text/result_json 大字段），
详情接口（阶段 7/8）再单独给完整内容，避免列表接口传输量爆炸。
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ResumeOut(BaseModel):
    """分析记录（列表/创建返回）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    status: str
    job_description: str | None = None
    created_at: datetime
