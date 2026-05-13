import io
import hashlib
import re
import zipfile
from pathlib import Path
from docx import Document
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def compress_docx_images(file_path, quality=80, max_width=1000, target_bytes=None, min_compress_width=800, min_byte_size=50_000, maintain_image_quality=True, extreme_only=False):
    p = Path(file_path)
    output_path = p.with_stem(f"{p.stem}_compressed")
    
    input_mb = p.stat().st_size / 1024 / 1024
    target_str = f"{target_bytes / 1024 / 1024:.1f} MB" if target_bytes else "no target"
    print(f"[shrinker] input: {p.name} ({input_mb:.2f} MB) | target: {target_str}")
    
    attempts = [(quality, max_width, False)]
    if target_bytes is not None:
        attempts = [
            (quality, max_width, False),
            (85, 1200, False),
            (75, 1000, True),
            (65, 900, True),
            (55, 800, True),
            (45, 700, True),
            (35, 600, True),
            (25, 500, True),
            (10, 100, True),
        ]
    if not maintain_image_quality:
        MIN_QUALITY = 45
        attempts = [a for a in attempts if a[0] > MIN_QUALITY]
        min_compress_width = 0
        min_byte_size = 0
    if extreme_only:
        attempts = attempts[-1]
        min_compress_width = 0
        min_byte_size = 0
    
    min_widths_per_part = _scan_image_min_widths(p)
    cropped_count = sum(1 for w in min_widths_per_part.values() if w >= max_width)
    print(f"[shrinker] scanned {len(min_widths_per_part)} image refs; {cropped_count} need extra source width to render crops sharply")
    
    for attempt_idx, (q, mw, force_jpeg) in enumerate(attempts, start=1):
        fmt_label = "JPEG-only" if force_jpeg else "smart-format"
        print(f"[shrinker] attempt {attempt_idx}/{len(attempts)}: quality={q}, max_width={mw}, {fmt_label}")
        doc = Document(p)
        
        compressed_count = 0
        skipped_count = 0
        for part in doc.part.package.parts:
            if "media" in part.partname and any(ext in part.partname for ext in [".jpg", ".png", ".jpeg", ".tif", ".tiff"]):
                ext = Path(str(part.partname)).suffix.lower()
                if extreme_only:
                    effective_mw = mw
                else:
                    effective_mw = max(mw, min_widths_per_part.get(str(part.partname), 0))
                new_blob = _shrink_image_blob(part.blob, ext, q, effective_mw, min_compress_width, min_byte_size, force_jpeg)
                if new_blob is not None:
                    part._blob = new_blob
                    compressed_count += 1
                else:
                    skipped_count += 1
        print(f"[shrinker]   compressed {compressed_count} images, skipped {skipped_count} (already small or no win)")
        
        doc.save(output_path)
        _normalize_media_extensions(output_path)
        _dedupe_media_in_docx(output_path)
        
        out_mb = output_path.stat().st_size / 1024 / 1024
        if target_bytes is None or output_path.stat().st_size <= target_bytes:
            print(f"[shrinker] done: {out_mb:.2f} MB -> {output_path.name}")
            return output_path
        print(f"[shrinker]   result: {out_mb:.2f} MB, still over target ({target_str}); retrying with more aggressive settings")
    
    out_mb = output_path.stat().st_size / 1024 / 1024
    print(f"[shrinker] exhausted ladder; best result: {out_mb:.2f} MB -> {output_path.name}")
    return output_path


def _scan_image_min_widths(docx_path):
    drawing_re = re.compile(r"<w:drawing>.*?</w:drawing>", re.DOTALL)
    extent_re = re.compile(r'<wp:extent\s+cx="(\d+)"\s+cy="(\d+)"')
    src_rect_re = re.compile(r"<a:srcRect\s+([^/]*)/>")
    rid_re = re.compile(r'r:embed="(rId\d+)"')
    attr_re = re.compile(r'(\w)="(\d+)"')
    
    min_widths = {}
    z = zipfile.ZipFile(docx_path, "r")
    
    xml_targets = [n for n in z.namelist() if n.startswith("word/") and n.endswith(".xml") and ("document" in n or "header" in n or "footer" in n)]
    
    for xml_name in xml_targets:
        body = z.read(xml_name).decode("utf-8", errors="ignore")
        rels_name = xml_name.rsplit("/", 1)[0] + "/_rels/" + xml_name.rsplit("/", 1)[1] + ".rels"
        if rels_name not in z.namelist():
            continue
        rels_xml = z.read(rels_name).decode("utf-8", errors="ignore")
        rid_to_target = {m.group(1): m.group(2) for m in re.finditer(r'Id="(rId\d+)"[^>]*Target="(media/[^"]+)"', rels_xml)}
        
        for m in drawing_re.finditer(body):
            block = m.group(0)
            rid_match = rid_re.search(block)
            ext_match = extent_re.search(block)
            if not rid_match or not ext_match:
                continue
            target = rid_to_target.get(rid_match.group(1))
            if not target:
                continue
            
            display_px = int(ext_match.group(1)) / 9525
            visible_fraction_w = 1.0
            src_match = src_rect_re.search(block)
            if src_match:
                attrs = dict(attr_re.findall(src_match.group(1)))
                left = int(attrs.get("l", 0)) / 100000
                right = int(attrs.get("r", 0)) / 100000
                visible_fraction_w = max(1 - left - right, 0.01)
            
            required_w = int(display_px / visible_fraction_w) + 1
            part_name = "/word/" + target
            if required_w > min_widths.get(part_name, 0):
                min_widths[part_name] = required_w
    
    z.close()
    return min_widths


def _shrink_image_blob(blob, ext, quality, max_width, min_compress_width, min_byte_size, force_jpeg=False):
    if len(blob) < min_byte_size:
        return None
    
    img = Image.open(io.BytesIO(blob))
    
    if img.width <= min_compress_width:
        return None
    
    if img.width > max_width:
        height = int((max_width / img.width) * img.height)
        img = img.resize((max_width, height), Image.Resampling.LANCZOS)
    
    keep_png = (not force_jpeg) and ext in (".png", ".tif", ".tiff") and _is_line_art(img)
    
    output = io.BytesIO()
    if keep_png:
        save_img = img if img.mode in ("RGBA", "LA", "P") else img.convert("P", palette=Image.Palette.ADAPTIVE, colors=256)
        save_img.save(output, format="PNG", optimize=True)
    else:
        if img.mode in ("RGBA", "LA"):
            background = Image.new("RGB", img.size, "white")
            background.paste(img, mask=img.split()[-1])
            img = background
        img.convert("RGB").save(output, format="JPEG", quality=quality, optimize=True)
    
    new_blob = output.getvalue()
    if len(new_blob) >= len(blob):
        return None
    return new_blob


def _is_line_art(img):
    sample = img.copy()
    sample.thumbnail((200, 200))
    if sample.mode not in ("RGB", "RGBA", "L", "P"):
        sample = sample.convert("RGB")
    return sample.getcolors(maxcolors=4096) is not None


def _dedupe_media_in_docx(docx_path):
    z_in = zipfile.ZipFile(docx_path, "r")
    items = {info.filename: z_in.read(info.filename) for info in z_in.infolist()}
    z_in.close()
    
    canonical = {}
    seen = {}
    for name, blob in items.items():
        if not name.startswith("word/media/"):
            continue
        digest = hashlib.sha1(blob).hexdigest()
        if digest in seen:
            canonical[name] = seen[digest]
        else:
            seen[digest] = name
    
    if not canonical:
        return
    
    print(f"[shrinker]   deduped {len(canonical)} duplicate image part(s)")
    
    for name in list(items.keys()):
        if not name.endswith(".rels"):
            continue
        content = items[name].decode("utf-8")
        for old, new in canonical.items():
            content = content.replace(f'Target="{old[len("word/"):]}"', f'Target="{new[len("word/"):]}"')
        items[name] = content.encode("utf-8")
    
    if "[Content_Types].xml" in items:
        ct = items["[Content_Types].xml"].decode("utf-8")
        for old in canonical:
            ct = re.sub(rf'<Override[^>]*PartName="/{re.escape(old)}"[^>]*/>', "", ct)
        items["[Content_Types].xml"] = ct.encode("utf-8")
    
    for old in canonical:
        items.pop(old, None)
    
    z_out = zipfile.ZipFile(docx_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9)
    for name, blob in items.items():
        z_out.writestr(name, blob)
    z_out.close()


def _sniff_image_format(blob):
    if blob[:3] == b"\xff\xd8\xff":
        return "jpg"
    if blob[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if blob[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if blob[:4] in (b"II*\x00", b"MM\x00*"):
        return "tif"
    if blob[:4] == b"RIFF" and blob[8:12] == b"WEBP":
        return "webp"
    if blob[:2] == b"BM":
        return "bmp"
    return None


def _normalize_media_extensions(docx_path):
    z_in = zipfile.ZipFile(docx_path, "r")
    items = {info.filename: z_in.read(info.filename) for info in z_in.infolist()}
    z_in.close()
    
    rename_map = {}
    in_use = set(items.keys())
    aliases = {"jpeg": "jpg", "jfif": "jpg", "tiff": "tif"}
    
    for name, blob in items.items():
        if not name.startswith("word/media/"):
            continue
        actual = _sniff_image_format(blob)
        if not actual:
            continue
        current = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if aliases.get(current, current) == actual:
            continue
        stem = name.rsplit(".", 1)[0]
        candidate = f"{stem}.{actual}"
        suffix = 1
        while candidate in in_use and candidate != name:
            candidate = f"{stem}_{suffix}.{actual}"
            suffix += 1
        rename_map[name] = candidate
        in_use.add(candidate)
    
    if not rename_map:
        return
    
    print(f"[shrinker]   renamed {len(rename_map)} part(s) so extension matches re-encoded content")
    
    for old, new in rename_map.items():
        items[new] = items.pop(old)
    
    for name in list(items.keys()):
        if not name.endswith(".rels"):
            continue
        content = items[name].decode("utf-8")
        for old, new in rename_map.items():
            old_target = old[len("word/"):]
            new_target = new[len("word/"):]
            content = content.replace(f'Target="{old_target}"', f'Target="{new_target}"')
        items[name] = content.encode("utf-8")
    
    if "[Content_Types].xml" in items:
        ct = items["[Content_Types].xml"].decode("utf-8")
        content_type_for = {
            "jpg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "tif": "image/tiff",
            "webp": "image/webp",
            "bmp": "image/bmp",
        }
        new_exts = {new.rsplit(".", 1)[-1].lower() for new in rename_map.values()}
        for ext in new_exts:
            if f'Extension="{ext}"' in ct or ext not in content_type_for:
                continue
            ct = ct.replace("</Types>", f'<Default Extension="{ext}" ContentType="{content_type_for[ext]}"/></Types>')
        for old, new in rename_map.items():
            ct = ct.replace(f'PartName="/{old}"', f'PartName="/{new}"')
        items["[Content_Types].xml"] = ct.encode("utf-8")
    
    z_out = zipfile.ZipFile(docx_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9)
    for name, blob in items.items():
        z_out.writestr(name, blob)
    z_out.close()
