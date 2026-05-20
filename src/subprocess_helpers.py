import gc
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# We run the heavy doc operations (image compression, LLM proofreading) in
# child Python processes so their RSS is reclaimed by the OS on exit. The
# parent Streamlit process otherwise holds onto allocator arenas indefinitely
# on Windows, which compounds across consecutive multi-GB documents.
#
# Sources can be passed as bytes OR as a file-like object (e.g. Streamlit's
# UploadedFile). File-likes are streamed to disk in chunks so the parent never
# materializes a full copy of the upload — critical for multi-GB inputs.
# Once a file-like upload has been copied to disk we also release Streamlit's
# MemoryUploadedFileManager entry: that dict is the second 2 GB ref-holder
# (the first is the UploadedFile in the widget's session_state, which the
# caller is responsible for clearing).

_CHUNK = 8 * 1024 * 1024


def _python():
    return sys.executable


def _write_source(source, path):
    if isinstance(source, (bytes, bytearray, memoryview)):
        path.write_bytes(bytes(source))
        return
    if hasattr(source, "seek"):
        source.seek(0)
    with open(path, "wb") as f:
        shutil.copyfileobj(source, f, length=_CHUNK)


def release_upload(source):
    if not hasattr(source, "file_id"):
        return
    try:
        from streamlit.runtime import get_instance
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        ctx = get_script_run_ctx()
        if ctx is None:
            return
        runtime = get_instance()
        mgr = getattr(runtime, "uploaded_file_mgr", None) or getattr(runtime, "_uploaded_file_mgr", None)
        if mgr is not None and hasattr(mgr, "remove_file"):
            mgr.remove_file(ctx.session_id, source.file_id)
    except Exception:
        pass


def run_shrink(source, filename, target_bytes=None, maintain_image_quality=True, extreme_only=False):
    with tempfile.TemporaryDirectory(prefix="shrink_") as tmp:
        tmp = Path(tmp)
        in_path = tmp / filename
        _write_source(source, in_path)
        release_upload(source)
        gc.collect()
        out_path = tmp / f"{Path(filename).stem}_out.docx"

        cmd = [
            _python(), "-m", "src.shrink_cli",
            str(in_path),
            "--output", str(out_path),
        ]
        if target_bytes is not None:
            cmd.extend(["--target-bytes", str(target_bytes)])
        if not maintain_image_quality:
            cmd.append("--no-maintain-quality")
        if extreme_only:
            cmd.append("--extreme-only")

        # Diagnostic marker printed by THIS process. If this line is missing
        # from the console, the Streamlit server is running stale code.
        print("[run_shrink] launching shrink subprocess", file=sys.stderr, flush=True)
        # No stdout/stderr redirection: the child inherits this process's
        # console, so its prints, shrinker logs, and tracebacks appear live.
        result = subprocess.run(cmd)
        if result.returncode != 0:
            raise RuntimeError("shrink subprocess failed (see console output)")

        out = out_path.read_bytes()
        gc.collect()
        return out


def run_proofread(target_source, source_source=None, target_filename="document.docx", max_iterations=3, progress_callback=None):
    with tempfile.TemporaryDirectory(prefix="proofread_") as tmp:
        tmp = Path(tmp)
        in_path = tmp / target_filename
        _write_source(target_source, in_path)
        release_upload(target_source)
        src_path = None
        if source_source is not None:
            src_path = tmp / f"source_{target_filename}"
            _write_source(source_source, src_path)
            release_upload(source_source)
        gc.collect()
        docx_out = tmp / "out.docx"
        changes_out = tmp / "changes.txt"

        cmd = [
            _python(), "-m", "src.proofread_cli",
            str(in_path),
            "--max-iterations", str(max_iterations),
            "--docx-out", str(docx_out),
            "--changes-out", str(changes_out),
        ]
        if src_path is not None:
            cmd.extend(["--source", str(src_path)])

        err_path = tmp / "stderr.txt"
        with open(err_path, "w", encoding="utf-8") as errf:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=errf, text=True, bufsize=1)
            for line in proc.stdout:
                line = line.strip()
                if line.startswith("PROGRESS ") and progress_callback is not None:
                    payload = line[len("PROGRESS "):]
                    if "/" in payload:
                        done_str, total_str = payload.split("/", 1)
                        if done_str.isdigit() and total_str.isdigit():
                            progress_callback(int(done_str), int(total_str))
            proc.wait()

        if proc.returncode != 0:
            err = err_path.read_text(encoding="utf-8", errors="replace").strip() or "proofread subprocess failed"
            if "too large" in err.lower():
                raise ValueError(err)
            raise RuntimeError(err)

        out_bytes = docx_out.read_bytes()
        out_text = changes_out.read_text(encoding="utf-8")
        gc.collect()
        return out_bytes, out_text
