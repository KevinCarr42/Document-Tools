import argparse
import sys
from pathlib import Path

from src.proofreader import proofread_bytes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("target")
    parser.add_argument("--source", default=None)
    parser.add_argument("--max-iterations", type=int, default=3)
    parser.add_argument("--docx-out", required=True)
    parser.add_argument("--changes-out", required=True)
    args = parser.parse_args()

    target_bytes = Path(args.target).read_bytes()
    source_bytes = Path(args.source).read_bytes() if args.source else None

    def on_progress(done, total):
        print(f"PROGRESS {done}/{total}", flush=True)

    docx_bytes, changes_text = proofread_bytes(
        target_bytes=target_bytes,
        source_bytes=source_bytes,
        target_filename=Path(args.target).name,
        max_iterations=args.max_iterations,
        progress_callback=on_progress,
    )

    Path(args.docx_out).write_bytes(docx_bytes)
    Path(args.changes_out).write_text(changes_text, encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
