import io
import random

from docx import Document
from PIL import Image

from src.doc_shrinker import (
    _is_line_art,
    _scan_image_min_widths,
    _shrink_image_blob,
    _sniff_image_format,
    compress_docx_images,
)


class TestSniffImageFormat:
    def test_jpeg(self):
        assert _sniff_image_format(b"\xff\xd8\xff\xe0\x00\x10JFIF") == "jpg"
    
    def test_png(self):
        assert _sniff_image_format(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8) == "png"
    
    def test_gif(self):
        assert _sniff_image_format(b"GIF89a" + b"\x00" * 4) == "gif"
    
    def test_tiff_little_endian(self):
        assert _sniff_image_format(b"II*\x00" + b"\x00" * 4) == "tif"
    
    def test_tiff_big_endian(self):
        assert _sniff_image_format(b"MM\x00*" + b"\x00" * 4) == "tif"
    
    def test_webp(self):
        assert _sniff_image_format(b"RIFF\x00\x00\x00\x00WEBPVP8 ") == "webp"
    
    def test_bmp(self):
        assert _sniff_image_format(b"BM" + b"\x00" * 10) == "bmp"
    
    def test_unknown_returns_none(self):
        assert _sniff_image_format(b"not an image at all") is None


class TestIsLineArt:
    def test_solid_colour_is_line_art(self):
        img = Image.new("RGB", (300, 300), (10, 20, 30))
        assert _is_line_art(img) is True
    
    def test_noisy_photo_is_not_line_art(self):
        raw = random.Random(0).randbytes(200 * 200 * 3)
        img = Image.frombytes("RGB", (200, 200), raw)
        assert _is_line_art(img) is False


class TestShrinkImageBlob:
    def test_large_image_is_resized_and_shrunk(self, noise_image):
        blob = noise_image(2000, 2000, fmt="JPEG", quality=95)
        result = _shrink_image_blob(
            blob, ".jpg", quality=70, max_width=800,
            min_compress_width=400, min_byte_size=10_000, force_jpeg=True,
        )
        assert result is not None
        assert len(result) < len(blob)
        assert Image.open(io.BytesIO(result)).width == 800
    
    def test_tiny_blob_is_skipped(self):
        result = _shrink_image_blob(
            b"\x00" * 100, ".jpg", quality=70, max_width=800,
            min_compress_width=400, min_byte_size=50_000,
        )
        assert result is None
    
    def test_narrow_image_is_skipped(self, noise_image):
        blob = noise_image(500, 500, fmt="JPEG", quality=95)
        result = _shrink_image_blob(
            blob, ".jpg", quality=70, max_width=800,
            min_compress_width=800, min_byte_size=10_000,
        )
        assert result is None


class TestScanImageMinWidths:
    def test_finds_embedded_image_widths(self, make_docx_with_image, tmp_path):
        path = make_docx_with_image(tmp_path / "scan.docx", width=1200, height=1200)
        widths = _scan_image_min_widths(path)
        assert len(widths) >= 1
        assert all(isinstance(w, int) and w > 0 for w in widths.values())


class TestCompressDocxImages:
    def test_shrinks_to_a_smaller_file(self, make_docx_with_image, tmp_path):
        path = make_docx_with_image(tmp_path / "big.docx", width=1200, height=1200)
        result = compress_docx_images(
            str(path), target_bytes=300_000, maintain_image_quality=False
        )
        assert result.name == "big_compressed.docx"
        assert result.exists()
        assert result.stat().st_size < path.stat().st_size
    
    def test_output_is_a_valid_docx(self, make_docx_with_image, tmp_path):
        path = make_docx_with_image(tmp_path / "doc.docx", width=1200, height=1200)
        result = compress_docx_images(
            str(path), target_bytes=300_000, maintain_image_quality=False
        )
        reopened = Document(str(result))
        assert reopened.paragraphs[0].text == "Document with an embedded image."
    
    def test_extreme_only_runs_a_single_aggressive_pass(self, make_docx_with_image, tmp_path):
        path = make_docx_with_image(tmp_path / "extreme.docx", width=1200, height=1200)
        result = compress_docx_images(str(path), extreme_only=True)
        assert result.exists()
        assert result.stat().st_size < path.stat().st_size
