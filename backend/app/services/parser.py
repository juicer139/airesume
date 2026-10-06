"""文件解析服务：把 PDF / Word 转成纯文本。

设计要点：
- 解析在"上传时"同步完成（文件小、本地解析快），AI 调用才需要异步
- 解析结果直接存库，后续 AI 任务只消费纯文本，Worker 不碰文件
- 扫描件（图片型 PDF）提不出文本，明确报错提示用户，而不是存一个空串
"""
import io

import pdfplumber
from docx import Document as DocxDocument


def extract_text(file_ext: str, data: bytes) -> str:
    """根据扩展名分发到对应解析器，返回非空纯文本。

    解析失败 / 提不出内容时抛 ValueError，由路由层转成 400。
    """
    if file_ext == ".pdf":
        text = _extract_pdf(data)
    elif file_ext == ".docx":
        text = _extract_docx(data)
    else:
        raise ValueError("不支持的文件类型")

    text = text.strip()
    if not text:
        raise ValueError(
            "无法从文件中提取文本：可能是扫描件/图片型 PDF，请换用可复制文字的文件"
        )
    return text


def _extract_pdf(data: bytes) -> str:
    """pdfplumber 逐页提取，页与页之间用换行拼接。"""
    parts: list[str] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            parts.append(page_text)
    return "\n".join(parts)


def _extract_docx(data: bytes) -> str:
    """python-docx 提取段落 + 表格（很多简历模板用表格排版）。"""
    doc = DocxDocument(io.BytesIO(data))

    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                cell_text = cell.text.strip()
                if cell_text:
                    parts.append(cell_text)
    return "\n".join(parts)
