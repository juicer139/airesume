"""AI Provider：统一的模型调用客户端。

为什么抽象这一层？
DeepSeek / 通义千问 / OpenAI 全部兼容 OpenAI 协议，只是 base_url 和 model 不同。
业务代码只依赖 AIProvider，换模型 = 改 .env 两个变量，一行代码不用动。

核心流程：
    resume_text + JD → Prompt 组装 → LLM → JSON 字符串
    → json.loads → Pydantic 校验 → AnalysisResult 对象
"""
import json
from functools import lru_cache

from openai import OpenAI
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.analysis import AnalysisResult
from app.services.ai.prompts import SYSTEM_PROMPT, build_analysis_prompt


class AIProviderError(Exception):
    """AI 调用/解析失败。路由层捕获后转成 502，不把内部细节直接暴露给前端。"""


class AIProvider:
    """OpenAI 兼容协议客户端。"""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.AI_API_KEY:
            raise AIProviderError("未配置 AI_API_KEY，请在 backend/.env 中填写后重启")
        self._client = OpenAI(
            api_key=settings.AI_API_KEY,
            base_url=settings.AI_BASE_URL,
        )
        self._model = settings.AI_MODEL

    def analyze_resume(
        self, resume_text: str, job_description: str | None
    ) -> AnalysisResult:
        """分析简历，返回校验后的结构化结果。"""
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_analysis_prompt(resume_text, job_description)},
                ],
                temperature=0.2,   # 分析任务求稳，不需要发散
                response_format={"type": "json_object"},  # JSON 模式
                timeout=120,       # 长简历 + 慢模型的最坏情况
            )
        except Exception as e:  # SDK 的网络/鉴权/限流异常统一归口
            raise AIProviderError(f"AI 接口调用失败：{e}") from e

        raw = resp.choices[0].message.content
        return _parse_analysis_result(raw)


def _parse_analysis_result(raw: str | None) -> AnalysisResult:
    """AI 原始输出 → AnalysisResult。三道关：非空 → 合法 JSON → 结构校验。"""
    if not raw:
        raise AIProviderError("AI 返回内容为空")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise AIProviderError(f"AI 返回的不是合法 JSON：{e}") from e

    try:
        return AnalysisResult.model_validate(data)
    except ValidationError as e:
        # 只取前 3 条错误，避免超长报错刷屏
        raise AIProviderError(f"AI 返回的 JSON 不符合约定结构：{e.errors()[:3]}") from e


@lru_cache
def get_ai_provider() -> AIProvider:
    """单例入口：OpenAI 客户端内部有连接池，全进程共享一个。"""
    return AIProvider()
