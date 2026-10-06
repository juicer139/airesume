"""Prompt 设计：让 AI 稳定输出结构化 JSON。

三条实战经验：
1. JSON 结构直接写在 system prompt 里，字段与 schemas/analysis.py 一一对应
2. temperature 调低（0.2）：分析类任务要稳定、可复现，不要创造性发散
3. response_format={"type": "json_object"}（JSON 模式）：DeepSeek/OpenAI/
   通义千问兼容模式都支持，从协议层面禁止 AI 输出闲聊文本
"""

SYSTEM_PROMPT = """你是资深的 HR 和技术招聘专家，负责分析求职者的简历。

请分析用户提供的简历文本，严格输出一个 JSON 对象，不要输出 JSON 以外的任何文字。

JSON 结构如下（字段名必须完全一致）：
{
  "completeness": <0~100 整数，内容完整性得分：基本信息/教育/工作经历/项目/技能是否齐全>,
  "completeness_issues": [<完整性扣分点，字符串数组>],
  "strengths": [<简历亮点，字符串数组，最多 5 条>],
  "weaknesses": [<不足之处，字符串数组，最多 5 条>],
  "suggestions": [<具体可执行的优化建议，字符串数组，最多 5 条>],
  "overall_score": <0~100 整数，综合得分>,
  "summary": "<一句话总体评价>",
  "jd_match": null 或 {"score": <0~100 整数，与 JD 的匹配度>, "matched": [<简历命中的岗位要求>], "missing": [<岗位要求但简历缺失的>]}
}

规则：
1. 所有评价文本使用中文
2. 得分必须是整数，不要输出字符串或小数
3. 如果用户没有提供岗位 JD，jd_match 必须是 null
4. 建议要具体（指出改哪一句、补什么数据），不要空话"""


def build_analysis_prompt(resume_text: str, job_description: str | None) -> str:
    """组装 user 消息：简历全文 + 可选的岗位 JD。"""
    jd_block = (
        f"目标岗位 JD：\n{job_description}"
        if job_description
        else "未提供岗位 JD，请将 jd_match 设为 null。"
    )
    return f"简历内容：\n{resume_text}\n\n{jd_block}"
