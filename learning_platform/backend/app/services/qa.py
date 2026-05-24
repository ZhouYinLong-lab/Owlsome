from __future__ import annotations

import os

from dotenv import load_dotenv
from openai import OpenAI

from app.db import get_connection, row_to_dict, rows_to_dicts


load_dotenv()


def build_context(knowledge_point_id: int) -> dict:
    with get_connection() as conn:
        point = row_to_dict(conn.execute("SELECT * FROM knowledge_points WHERE id = ?", (knowledge_point_id,)).fetchone())
        units = rows_to_dicts(
            conn.execute(
                "SELECT * FROM content_units WHERE knowledge_point_id = ? ORDER BY order_index",
                (knowledge_point_id,),
            ).fetchall()
        )
        notes = rows_to_dicts(
            conn.execute(
                "SELECT * FROM notes WHERE knowledge_point_id = ? AND status = 'approved' ORDER BY reviewed_at DESC",
                (knowledge_point_id,),
            ).fetchall()
        )
    if not point:
        raise ValueError("知识点不存在。")
    return {"point": point, "units": units, "notes": notes}


def build_personal_context(space_id: int, point_id: int) -> dict:
    with get_connection() as conn:
        point = row_to_dict(
            conn.execute(
                """
                SELECT pkp.*, ps.title AS space_title
                FROM personal_knowledge_points pkp
                JOIN personal_spaces ps ON ps.id = pkp.space_id
                WHERE pkp.space_id = ? AND pkp.id = ?
                """,
                (space_id, point_id),
            ).fetchone()
        )
        units = rows_to_dicts(
            conn.execute(
                """
                SELECT *
                FROM personal_content_units
                WHERE personal_knowledge_point_id = ?
                ORDER BY order_index
                """,
                (point_id,),
            ).fetchall()
        )
    if not point:
        raise ValueError("个人知识点不存在。")
    # 复用公共知识点的离线问答模板，因此这里提供空 notes，
    # 并保持 point/units 的字段形状一致。
    return {"point": point, "units": units, "notes": []}


def offline_answer(context: dict, question: str) -> str:
    """Deterministic fallback for offline demos without an LLM API key."""
    point = context["point"]
    units = context["units"]
    notes = context["notes"]
    definition = next((unit for unit in units if unit["unit_type"] == "definition"), None)
    theorem = next((unit for unit in units if unit["unit_type"] == "theorem"), None)
    example = next((unit for unit in units if unit["unit_type"] == "example"), None)

    parts = [
        f"基于当前知识点内容生成：你问的是“{question}”。",
        f"当前知识点是 {point['code']} {point['title']}。{point['summary']}",
    ]
    if definition:
        parts.append(f"先看定义线索：{definition['content'][:220]}...")
    if theorem:
        parts.append(f"相关定理：{theorem['content'][:220]}...")
    if example:
        parts.append(f"可以参考例题：{example['title']}。解题时先识别变量关系，再按教材步骤计算。")
    if notes:
        parts.append(f"已审核笔记补充：{notes[0]['content'][:160]}...")
    parts.append("离线模式建议：回到本知识点的定义、定理和例题三块内容交叉查看，先理解条件，再做习题。")
    return "\n\n".join(parts)


def llm_answer(context: dict, question: str) -> str | None:
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        return None
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    model = os.getenv("MODEL_NAME", "deepseek/deepseek-v4-flash:free")
    point = context["point"]
    snippets = "\n\n".join(unit["content"][:900] for unit in context["units"][:5])
    notes = "\n\n".join(note["content"][:500] for note in context["notes"][:3])
    prompt = f"""请基于给定教材知识点回答学生问题。不要编造教材外结论；如果资料不足，请说明。

知识点：{point['code']} {point['title']}
摘要：{point['summary']}

教材片段：
{snippets}

已审核笔记：
{notes or '暂无'}

学生问题：{question}
"""
    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "你是一个严谨、友好的大学数学助教。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content


def answer_question(knowledge_point_id: int, question: str) -> dict:
    context = build_context(knowledge_point_id)
    mode = "llm"
    try:
        answer = llm_answer(context, question)
    except Exception as exc:
        answer = None
        mode = f"offline_after_llm_error: {type(exc).__name__}"
    if not answer:
        mode = "offline" if mode == "llm" else mode
        answer = offline_answer(context, question)

    with get_connection() as conn:
        conn.execute(
            "INSERT INTO qa_logs (knowledge_point_id, question, answer, mode) VALUES (?, ?, ?, ?)",
            (knowledge_point_id, question, answer, mode),
        )
    return {"answer": answer, "mode": mode}


def answer_personal_question(space_id: int, point_id: int, question: str) -> dict:
    context = build_personal_context(space_id, point_id)
    mode = "llm"
    try:
        answer = llm_answer(context, question)
    except Exception as exc:
        answer = None
        mode = f"offline_after_llm_error: {type(exc).__name__}"
    if not answer:
        mode = "offline" if mode == "llm" else mode
        answer = offline_answer(context, question)
    return {"answer": answer, "mode": mode}
