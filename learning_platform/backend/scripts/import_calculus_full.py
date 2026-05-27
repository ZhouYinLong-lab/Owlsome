from __future__ import annotations

import argparse
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.pipelines.calculus_full_importer import DEFAULT_REPORT, import_calculus_full


def print_summary(result: dict) -> None:
    counts = result["unit_counts"]
    print("\n微积分 II 全书结构化处理完成")
    print("=" * 52)
    print(f"输入文件: {result['input_path']}")
    print(f"导入数据库: {'是' if result['imported'] else '否，dry-run 或课程已存在'}")
    print(f"章节数: {result['chapters']}")
    print(f"知识点数: {result['knowledge_points']}")
    print(f"内容单元数: {result['content_units']}")
    print(
        "单元类型: "
        f"讲解 {counts.get('explanation', 0)} / "
        f"定义 {counts.get('definition', 0)} / "
        f"定理 {counts.get('theorem', 0)} / "
        f"例题 {counts.get('example', 0)} / "
        f"习题 {counts.get('exercise', 0)}"
    )
    print(f"报告路径: {result['report_path'] or '未写入'}")
    print(result["message"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Import the full cleaned Calculus II Markdown with rule-based segmentation.")
    parser.add_argument("--input", help="清洗版或 MinerU Markdown 路径；默认优先 merged_full_formatted.md")
    parser.add_argument("--dry-run", action="store_true", help="只切分并生成报告，不写入数据库")
    parser.add_argument("--import", dest="do_import", action="store_true", help="写入 SQLite 公共知识库")
    parser.add_argument("--reset-course", action="store_true", help="导入前删除同名课程及其下属章节/知识点")
    parser.add_argument("--report", help=f"报告输出路径，默认 {DEFAULT_REPORT}")
    args = parser.parse_args()

    dry_run = bool(args.dry_run or not args.do_import)
    result = import_calculus_full(
        dry_run=dry_run,
        reset_course_before_import=args.reset_course,
        write_report_file=True,
        input_path=args.input,
        report_path=args.report,
        via_api=False,
    )
    print_summary(result)

    if dry_run:
        print("\n下一步可执行真实导入:")
        print("python scripts\\import_calculus_full.py --import --reset-course")


if __name__ == "__main__":
    main()
