"""CLI tools for debugging Mnemo's pipeline.

Usage:
    mnemo debug inspect-pdf <path> [--pages=N]
"""
import sys
import argparse
from pathlib import Path

from .parser import parse_pdf


def cmd_inspect_pdf(args):
    fpath = Path(args.path)
    if not fpath.exists():
        print(f"File not found: {fpath}")
        return 1

    pages, total = parse_pdf(str(fpath))
    print(f"File: {fpath.name}")
    print(f"Total pages: {total}")
    print()

    ocr_count = 0
    text_count = 0
    for p in pages:
        if p["ocr_needed"]:
            ocr_count += 1
        else:
            text_count += 1

        max_pages = getattr(args, "pages", total)
        show_all = max_pages >= total
        if not show_all and p["page_num"] >= max_pages:
            continue

        label = "OCR" if p["ocr_needed"] else "TEXT"
        preview = p["text"][:120].replace("\n", " | ").replace("\r", "")
        print(
            f"  p{p['page_num']:>4} [{label}] "
            f"q={p['quality']:.3f}  "
            f"len={len(p['text']):>6}  "
            f"{preview}"
        )

    print()
    print(f"Summary: {text_count} extracted, {ocr_count} OCR needed")


def main():
    parser = argparse.ArgumentParser(prog="mnemo debug")
    sub = parser.add_subparsers(dest="command")

    inspect = sub.add_parser("inspect-pdf", help="Show page-by-page OCR classification for a PDF")
    inspect.add_argument("path", help="Path to PDF file")
    inspect.add_argument("--pages", type=int, default=999999, help="Number of pages to show")

    args = parser.parse_args()
    if args.command == "inspect-pdf":
        return cmd_inspect_pdf(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
