import argparse
import shutil
import sys
from pathlib import Path

from src.doc_shrinker import compress_docx_images


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--output", required=True)
    parser.add_argument("--target-bytes", type=int, default=None)
    parser.add_argument("--no-maintain-quality", action="store_true")
    parser.add_argument("--extreme-only", action="store_true")
    args = parser.parse_args()

    result = compress_docx_images(
        args.input,
        target_bytes=args.target_bytes,
        maintain_image_quality=not args.no_maintain_quality,
        extreme_only=args.extreme_only,
    )

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    if Path(result).resolve() != out.resolve():
        shutil.move(str(result), str(out))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
