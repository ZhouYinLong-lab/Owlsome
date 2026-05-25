#!/usr/bin/env python3
"""Markdown 文本校对工具 - 基于 OpenRouter 大模型 API 的文档格式化，支持断点续传与 diff 对比."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import difflib
import hashlib
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

from owlsome_core.obsidian import normalize_obsidian_markdown, title_from_path

# Load the repository-level env first, then the tool-local env.
# This lets `python D:\Projects\EL\text_archiver\main.py ...` work even
# when the command is launched from `D:\Projects\EL`.
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(Path(__file__).with_name(".env"), override=True)

# ================= 默认配置 =================
API_KEY = os.getenv("OPENROUTER_API_KEY", "")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
MODEL_NAME = os.getenv("OPENROUTER_MODEL") or os.getenv("MODEL_NAME", "deepseek/deepseek-v4-flash:free")
CHUNK_SIZE = 4000
OVERLAP_SIZE = 1  # 以段落为单位，不再需要字符级重叠
MAX_RETRIES = 3
RETRY_DELAY = 2
# ===========================================

SYSTEM_PROMPT = """你是一个严谨的文档排版专家。你的任务是将输入的 Markdown 文本进行标准格式化修复。
必须严格遵守以下规则：
1. 修正错误的 Markdown 语法、不规范的列表、加粗以及标题层级。
2. 统一中英文混排格式（在中文与英文、数字之间自动添加空格）。
3. 修复因PDF转化导致的断行、错位段落，恢复正常的阅读流。
4. **绝对不能漏掉、删减、篡改或概括原文中的任何一句话和任何一个字**。
5. 优先兼容 Obsidian Markdown：保留 YAML frontmatter、[[双链]]、> [!note] callout、==高亮==、任务列表、LaTeX 公式和图片链接。
6. 仅输出格式化后的 Markdown 文本，不要包含任何解释、前言、后记或 ```markdown 标记。"""


# ======================== 分块与合并 ========================


def chunk_markdown(text: str, chunk_size: int, overlap: int) -> list[str]:
    """按段落切分，确保每个分块在空行处断开，避免截断内容。

    段落之间以连续空行（1 个或多个 \\n\\n）分隔。当累计段落超过 chunk_size 字符时，
    将最后一段留作下一个块的"重叠锚点"，保证跨块边界的内容连贯性。
    """
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    buf: list[str] = []
    buf_len = 0

    for para in paragraphs:
        # 带分隔符的真实长度
        para_len = len(para) + (2 if buf else 0)

        if buf and buf_len + para_len > chunk_size:
            chunks.append("\n\n".join(buf))
            buf = [buf[-1]] if overlap else []  # 最后一段作为重叠锚点
            buf_len = len(buf[0]) + 2 if buf else 0

        buf.append(para)
        buf_len += para_len + (0 if len(buf) == 1 else 2)

    if buf:
        chunks.append("\n\n".join(buf))

    return chunks


def merge_chunks(formatted_chunks: list[str], overlap: int = 500) -> str:
    if not formatted_chunks:
        return ""
    final_text = formatted_chunks[0]
    for i in range(1, len(formatted_chunks)):
        current = formatted_chunks[i]
        anchor = current[:150]
        pos = final_text.rfind(anchor)
        if pos != -1:
            final_text = final_text[:pos] + current
        else:
            final_text += "\n\n" + current
    return final_text


# ======================== API 调用 ========================


def build_chunk_prompt(chunk_text: str, chunk_index: int, total_chunks: int, book_profile: str = "") -> str:
    profile_text = ""
    if book_profile.strip():
        profile_text = f"\n\n本书整理规范如下，请优先遵守：\n{book_profile.strip()}\n"
    return (
        f"这是整个文档的第 {chunk_index + 1}/{total_chunks} 部分，"
        f"请对其进行全面格式化，保持内容绝对完整。{profile_text}\n\n"
        f"当前分块内容：\n\n{chunk_text}"
    )


def format_chunk_via_api(
    client: OpenAI,
    model: str,
    chunk_text: str,
    chunk_index: int,
    total_chunks: int,
    max_retries: int = MAX_RETRIES,
    retry_delay: float = RETRY_DELAY,
    book_profile: str = "",
) -> tuple[str, dict]:
    user_prompt = build_chunk_prompt(chunk_text, chunk_index, total_chunks, book_profile)
    started = time.perf_counter()

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                stream=False,
            )
            return response.choices[0].message.content or "", {
                "status": "done",
                "duration_seconds": round(time.perf_counter() - started, 3),
                "attempts": attempt + 1,
                "fallback_to_original": False,
            }
        except Exception as e:
            if attempt < max_retries - 1:
                tqdm.write(
                    f"  [重试] 分块 {chunk_index + 1} 失败 (尝试 {attempt + 1}/{max_retries}): {e}"
                )
                time.sleep(retry_delay * (attempt + 1))
            else:
                tqdm.write(f"  [错误] 分块 {chunk_index + 1} 最终失败: {e}")
                return chunk_text, {
                    "status": "failed",
                    "duration_seconds": round(time.perf_counter() - started, 3),
                    "attempts": attempt + 1,
                    "fallback_to_original": True,
                    "error": str(e),
                }
    return chunk_text, {
        "status": "failed",
        "duration_seconds": round(time.perf_counter() - started, 3),
        "attempts": max_retries,
        "fallback_to_original": True,
    }


def format_chunk_worker(
    api_key: str,
    base_url: str,
    model: str,
    chunk_text: str,
    chunk_index: int,
    total_chunks: int,
    retry_delay: float,
    book_profile: str,
) -> tuple[int, str, dict]:
    client = OpenAI(api_key=api_key, base_url=base_url)
    result, meta = format_chunk_via_api(
        client,
        model,
        chunk_text,
        chunk_index,
        total_chunks,
        retry_delay=retry_delay,
        book_profile=book_profile,
    )
    return chunk_index, result, meta


# ======================== 本书规范抽样 ========================


def select_profile_sample_indices(chunks: list[str], sample_count: int) -> list[int]:
    if not chunks:
        return []
    sample_count = max(1, min(sample_count, len(chunks)))
    anchors = {0, len(chunks) // 2, len(chunks) - 1}
    scored = []
    for index, chunk in enumerate(chunks):
        score = chunk.count("$") + chunk.count("\\[") * 2 + chunk.count("例") + chunk.count("习题") + chunk.count("#")
        scored.append((score, index))
    scored.sort(reverse=True)
    for _score, index in scored:
        anchors.add(index)
        if len(anchors) >= sample_count:
            break
    return sorted(anchors)[:sample_count]


def build_profile_prompt(samples: list[tuple[int, str]], total_chunks: int) -> str:
    joined = "\n\n".join(
        f"## 样本分块 {index + 1}/{total_chunks}\n\n{text[:2500]}"
        for index, text in samples
    )
    return f"""请根据以下 Markdown 样本，生成“本书整理规范”。规范将用于后续批量清洗整本教材。

请只输出 Markdown 规范正文，包含以下小节：
- 标题层级规则
- 定义/定理/例题/习题格式
- LaTeX 公式保留规则
- 图片与表格处理规则
- Obsidian callout、wikilink、highlight 兼容规则
- 需要人工复核的风险点

样本如下：

{joined}
"""


def generate_book_profile(client: OpenAI, model: str, chunks: list[str], sample_count: int) -> tuple[str, list[int]]:
    sample_indices = select_profile_sample_indices(chunks, sample_count)
    samples = [(index, chunks[index]) for index in sample_indices]
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "你是严谨的教材 Markdown 整理规范制定专家。"},
            {"role": "user", "content": build_profile_prompt(samples, len(chunks))},
        ],
        temperature=0.1,
        stream=False,
    )
    return response.choices[0].message.content or "", sample_indices


# ======================== 断点续传 ========================


def get_checkpoint_path(input_file: str) -> str:
    return f"{input_file}.checkpoint.json"


def load_checkpoint(input_file: str) -> dict | None:
    cp_path = get_checkpoint_path(input_file)
    if not os.path.exists(cp_path):
        return None
    try:
        with open(cp_path, "r", encoding="utf-8") as f:
            cp = json.load(f)
        return cp
    except (json.JSONDecodeError, KeyError):
        return None


def save_checkpoint(
    input_file: str,
    file_hash: str,
    processed: dict[int, str],
    total: int,
    meta: dict[int, dict] | None = None,
):
    cp_path = get_checkpoint_path(input_file)
    with open(cp_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "file_hash": file_hash,
                "total_chunks": total,
                "processed": {str(k): v for k, v in processed.items()},
                "meta": {str(k): v for k, v in (meta or {}).items()},
            },
            f,
            ensure_ascii=False,
            indent=2,
        )


def clear_checkpoint(input_file: str):
    cp_path = get_checkpoint_path(input_file)
    if os.path.exists(cp_path):
        os.remove(cp_path)


def write_report(report_path: str, report: dict):
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"处理报告已保存至: {report_path}")


# ======================== Diff 对比 ========================


def build_diff(
    original: str, formatted: str, fromfile: str = "原始文档", tofile: str = "格式化后", context_lines: int = 3
) -> str:
    """生成 unified diff 文本。"""
    orig_lines = original.splitlines(keepends=True)
    fmt_lines = formatted.splitlines(keepends=True)
    diff_lines = list(difflib.unified_diff(
        orig_lines, fmt_lines,
        fromfile=fromfile, tofile=tofile,
        n=context_lines,
    ))
    return "".join(diff_lines)


def save_diff_file(diff_text: str, diff_path: str):
    """将 diff 写入文件。"""
    with open(diff_path, "w", encoding="utf-8") as f:
        if diff_text:
            f.write(diff_text)
        else:
            f.write("# (无差异 — 文档未发生变化)\n")
    print(f"Diff 已保存至: {diff_path}")


def show_diff(diff_text: str):
    """将 diff 文本彩色打印到终端。"""
    if not diff_text.strip():
        print("\n(无差异 — 文档未发生变化)")
        return

    try:
        from colorama import Fore, Style, init
        init()
        _color = True
    except ImportError:
        _color = False

    for line in diff_text.splitlines():
        if _color:
            if line.startswith("---") or line.startswith("+++"):
                print(f"{Style.BRIGHT}{line}{Style.RESET_ALL}")
            elif line.startswith("@@"):
                print(f"{Fore.CYAN}{line}{Style.RESET_ALL}")
            elif line.startswith("+"):
                print(f"{Fore.GREEN}{line}{Style.RESET_ALL}")
            elif line.startswith("-"):
                print(f"{Fore.RED}{line}{Style.RESET_ALL}")
            else:
                print(line)
        else:
            print(line)




# ======================== 主流程 ========================


def main():
    parser = argparse.ArgumentParser(
        description="Markdown 文本校对工具 — 基于大模型 API + 断点续传 + Diff 对比"
    )
    parser.add_argument("input", nargs="?", default="input.md", help="输入 Markdown 文件")
    parser.add_argument("-o", "--output", default="", help="输出文件（默认: <输入>_formatted.md）")
    parser.add_argument("-k", "--api-key", default="", help="OpenRouter API Key")
    parser.add_argument("--model", default="", help=f"模型（默认: {MODEL_NAME}）")
    parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE, help="分块字数")
    parser.add_argument("--overlap", type=int, default=OVERLAP_SIZE, help="重叠字数")
    parser.add_argument("--base-url", default="", help="API Base URL")
    parser.add_argument("--no-resume", action="store_true", help="禁用断点续传，从头处理")
    parser.add_argument("--diff", action="store_true", help="导出 diff 文件到 <输出>.diff 备查")
    parser.add_argument("--diff-context", type=int, default=3, help="diff 上下文行数（默认: 3）")
    parser.add_argument("--show-diff", action="store_true", help="完成后在终端打印 diff 对比")
    parser.add_argument("--diff-only", action="store_true", help="仅对比已有文件导出 diff（不调用 API）")
    parser.add_argument("--obsidian", action="store_true", default=True, help="输出 Obsidian 兼容 Markdown（默认开启）")
    parser.add_argument("--no-obsidian", dest="obsidian", action="store_false", help="关闭 Obsidian 兼容后处理")
    parser.add_argument("--obsidian-title", default="", help="Frontmatter 标题（默认取输入文件名）")
    parser.add_argument("--parallel", type=int, default=1, help="并发清洗 worker 数（默认: 1，保持串行）")
    parser.add_argument("--auto-profile", action="store_true", help="抽样生成本书整理规范后再清洗")
    parser.add_argument("--profile-samples", type=int, default=5, help="自动抽样生成规范的分块数量")
    parser.add_argument("--book-profile", default="", help="使用已有本书整理规范文件")
    parser.add_argument("--profile-output", default="", help="自动生成规范的保存路径（默认: <输入>_profile.md）")
    parser.add_argument("--report", action="store_true", help="输出处理报告 JSON 到 <输出>.report.json")
    parser.add_argument("--rate-limit-delay", type=float, default=RETRY_DELAY, help="API 失败后的基础退避秒数")
    parser.add_argument("--dry-run", action="store_true", help="只显示分块、抽样和输出计划，不调用 API，不写 formatted 输出")
    args = parser.parse_args()

    # ------- 仅 diff 模式 -------
    if args.diff_only:
        input_file = args.input
        output_file = args.output or f"{os.path.splitext(input_file)[0]}_formatted.md"
        if not os.path.exists(input_file):
            print(f"[错误] 找不到: {input_file}")
            sys.exit(1)
        if not os.path.exists(output_file):
            print(f"[错误] 找不到: {output_file}")
            sys.exit(1)
        with open(input_file, "r", encoding="utf-8") as f:
            orig = f.read()
        with open(output_file, "r", encoding="utf-8") as f:
            fmt = f.read()
        diff_text = build_diff(orig, fmt, fromfile=input_file, tofile=output_file)
        diff_path = f"{output_file}.diff"
        save_diff_file(diff_text, diff_path)
        if args.show_diff:
            show_diff(diff_text)
        return

    # ------- 参数解析 -------
    model = args.model or MODEL_NAME
    base_url = args.base_url or BASE_URL
    input_file = args.input
    output_file = args.output or f"{os.path.splitext(input_file)[0]}_formatted.md"
    profile_output = args.profile_output or f"{os.path.splitext(input_file)[0]}_profile.md"
    report_path = f"{output_file}.report.json"
    chunk_size = args.chunk_size
    overlap = args.overlap
    parallel = max(1, args.parallel)

    if not os.path.exists(input_file):
        print(f"[错误] 找不到输入文件: {input_file}")
        sys.exit(1)

    # ------- 读取原文 -------
    with open(input_file, "r", encoding="utf-8") as f:
        original_text = f.read()
    file_hash = hashlib.sha256(original_text.encode()).hexdigest()

    print(f"输入文件: {input_file} ({len(original_text):,} 字符)")
    print(f"模型: {model}")
    print(f"API: {base_url}")

    # ------- 分块 -------
    chunks = chunk_markdown(original_text, chunk_size, overlap)
    total = len(chunks)
    unit = "段" if overlap else "无重叠"
    print(f"分块: {total} 块 (每块 ~{chunk_size:,} 字, 重叠: {unit})")

    sample_indices = select_profile_sample_indices(chunks, args.profile_samples)
    if args.dry_run:
        print("\n[Dry Run] 不调用 API，不写 formatted 输出。")
        print(f"输入: {input_file}")
        print(f"输出: {output_file}")
        print(f"报告: {report_path if args.report else '未启用'}")
        print(f"并发: {parallel}")
        print(f"自动规范: {'是' if args.auto_profile else '否'}")
        print(f"规范输出: {profile_output if args.auto_profile else args.book_profile or '未启用'}")
        print(f"抽样分块: {', '.join(str(index + 1) for index in sample_indices)}")
        return

    api_key = args.api_key or API_KEY
    if not api_key:
        print("[错误] 请设置 OPENROUTER_API_KEY 环境变量或使用 -k 参数")
        sys.exit(1)

    started_at = datetime.now()

    # ------- 断点续传 -------
    processed: dict[int, str] = {}
    processed_meta: dict[int, dict] = {}
    start_from = 0
    if not args.no_resume:
        cp = load_checkpoint(input_file)
        if cp and cp.get("file_hash") == file_hash and cp.get("total_chunks") == total:
            processed = {int(k): v for k, v in cp.get("processed", {}).items()}
            processed_meta = {int(k): v for k, v in cp.get("meta", {}).items()}
            start_from = len(processed)
            if start_from > 0:
                print(f"[断点续传] 已恢复 {start_from}/{total} 块，从第 {start_from + 1} 块继续")

    # ------- 本书规范 -------
    client = OpenAI(api_key=api_key, base_url=base_url)
    book_profile = ""
    profile_mode = "none"
    if args.book_profile:
        with open(args.book_profile, "r", encoding="utf-8") as f:
            book_profile = f.read()
        profile_mode = "file"
        print(f"使用本书规范: {args.book_profile}")
    elif args.auto_profile:
        print("正在抽样生成本书整理规范...")
        book_profile, sample_indices = generate_book_profile(client, model, chunks, args.profile_samples)
        with open(profile_output, "w", encoding="utf-8") as f:
            f.write(book_profile)
        profile_mode = "auto"
        print(f"本书整理规范已保存至: {profile_output}")

    try:
        remaining = [index for index in range(total) if index not in processed]
        pbar = tqdm(total=total, desc="云端格式化进度", unit="块", initial=len(processed))
        if parallel == 1:
            for i in remaining:
                result, meta = format_chunk_via_api(
                    client,
                    model,
                    chunks[i],
                    i,
                    total,
                    retry_delay=args.rate_limit_delay,
                    book_profile=book_profile,
                )
                processed[i] = result
                processed_meta[i] = meta
                save_checkpoint(input_file, file_hash, processed, total, processed_meta)
                pbar.update(1)
        else:
            with ThreadPoolExecutor(max_workers=parallel) as executor:
                futures = {
                    executor.submit(
                        format_chunk_worker,
                        api_key,
                        base_url,
                        model,
                        chunks[i],
                        i,
                        total,
                        args.rate_limit_delay,
                        book_profile,
                    ): i
                    for i in remaining
                }
                for future in as_completed(futures):
                    index, result, meta = future.result()
                    processed[index] = result
                    processed_meta[index] = meta
                    save_checkpoint(input_file, file_hash, processed, total, processed_meta)
                    pbar.update(1)
        pbar.close()
    except KeyboardInterrupt:
        pbar.close()
        done = len(processed)
        print(f"\n[已中断] 已处理 {done}/{total} 块，checkpoint 已保存。")
        print(f"下次运行将自动从第 {done + 1} 块继续。")
        sys.exit(0)

    # ------- 合并 -------
    print("\n正在合并去重...")
    ordered = [processed[i] for i in sorted(processed)]
    final_output = merge_chunks(ordered, overlap)
    if args.obsidian:
        final_output = normalize_obsidian_markdown(
            final_output,
            title=args.obsidian_title or title_from_path(input_file),
            source=input_file,
            tags=["owlsome", "archived-markdown"],
            doc_type="cleaned_markdown",
        )

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(final_output)

    clear_checkpoint(input_file)

    # ------- 统计 -------
    orig_len = len(original_text)
    fmt_len = len(final_output)
    print(f"\n原始: {orig_len:,} 字符 → 格式化后: {fmt_len:,} 字符 "
          f"({'+' if fmt_len >= orig_len else ''}{fmt_len - orig_len:,})")
    print(f"输出文件: {output_file}")

    finished_at = datetime.now()
    if args.report:
        metas = list(processed_meta.values())
        fallback_chunks = sorted(index for index, meta in processed_meta.items() if meta.get("fallback_to_original"))
        done_chunks = sum(1 for meta in metas if meta.get("status") == "done")
        failed_chunks = sum(1 for meta in metas if meta.get("status") == "failed")
        avg_seconds = round(sum(float(meta.get("duration_seconds", 0)) for meta in metas) / len(metas), 3) if metas else 0
        write_report(
            report_path,
            {
                "input": input_file,
                "output": output_file,
                "model": model,
                "parallel": parallel,
                "chunk_size": chunk_size,
                "total_chunks": total,
                "profile_mode": profile_mode,
                "profile_output": profile_output if profile_mode == "auto" else args.book_profile,
                "profile_sample_chunks": [index + 1 for index in sample_indices],
                "started_at": started_at.isoformat(timespec="seconds"),
                "finished_at": finished_at.isoformat(timespec="seconds"),
                "duration_seconds": round((finished_at - started_at).total_seconds(), 3),
                "done_chunks": done_chunks,
                "failed_chunks": failed_chunks,
                "fallback_chunks": fallback_chunks,
                "average_chunk_seconds": avg_seconds,
                "chunk_meta": {str(k): v for k, v in sorted(processed_meta.items())},
            },
        )

    # ------- Diff -------
    if args.diff or args.show_diff:
        diff_text = build_diff(
            original_text, final_output,
            fromfile=input_file, tofile=output_file,
            context_lines=args.diff_context,
        )
        if args.diff:
            diff_path = f"{output_file}.diff"
            save_diff_file(diff_text, diff_path)
        if args.show_diff:
            print(f"\n{'─' * 60}")
            print(f"格式化前后差异对比 ({len(diff_text)} 字节):")
            print(f"{'─' * 60}")
            show_diff(diff_text)


if __name__ == "__main__":
    main()
