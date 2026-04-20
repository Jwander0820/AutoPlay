from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from pathlib import Path

from .script import Region

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_BRUTE_FORCE_COMPARISONS = 1_000_000


class ImageError(ValueError):
    pass


@dataclass(frozen=True)
class Image:
    width: int
    height: int
    rows: tuple[bytes, ...]

    def pixel(self, x: int, y: int) -> tuple[int, int, int, int]:
        index = x * 4
        row = self.rows[y]
        return (row[index], row[index + 1], row[index + 2], row[index + 3])


@dataclass(frozen=True)
class MatchResult:
    matched: bool
    score: float
    x: int | None = None
    y: int | None = None


def match_template_file(
    source_path: str | Path,
    template_path: str | Path,
    threshold: float,
    tolerance: int = 0,
    region: Region | None = None,
) -> MatchResult:
    source = read_png(source_path)
    template = read_png(template_path)
    return match_template(source, template, threshold=threshold, tolerance=tolerance, region=region)


def match_template(source: Image, template: Image, threshold: float, tolerance: int = 0, region: Region | None = None) -> MatchResult:
    if template.width > source.width or template.height > source.height:
        return MatchResult(matched=False, score=0.0)

    x0, y0, x1, y1 = _search_bounds(source, template, region)
    if x1 < x0 or y1 < y0:
        return MatchResult(matched=False, score=0.0)

    if tolerance == 0:
        exact = _match_exact_rows(source, template, x0, y0, x1, y1)
        if exact.matched:
            return exact
        _raise_if_brute_force_too_large(source, template, x0, y0, x1, y1)

    best_score = -1.0
    best_x: int | None = None
    best_y: int | None = None

    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            score = _score_at(source, template, x, y, tolerance)
            if score > best_score:
                best_score = score
                best_x = x
                best_y = y
            if score >= threshold:
                return MatchResult(matched=True, score=score, x=x, y=y)

    return MatchResult(matched=False, score=max(best_score, 0.0), x=best_x, y=best_y)


def read_png(path: str | Path) -> Image:
    data = Path(path).read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise ImageError("Not a PNG file.")

    chunks = _read_chunks(data)
    ihdr = chunks.get(b"IHDR", [None])[0]
    if ihdr is None:
        raise ImageError("PNG is missing IHDR.")

    width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(">IIBBBBB", ihdr)
    if bit_depth != 8:
        raise ImageError("Only 8-bit PNG files are supported.")
    if compression != 0 or filter_method != 0 or interlace != 0:
        raise ImageError("Unsupported PNG compression, filter, or interlace settings.")
    if color_type not in (0, 2, 6):
        raise ImageError("Only grayscale, RGB, and RGBA PNG files are supported.")

    compressed = b"".join(chunks.get(b"IDAT", []))
    if not compressed:
        raise ImageError("PNG is missing IDAT data.")
    raw = zlib.decompress(compressed)
    channels = {0: 1, 2: 3, 6: 4}[color_type]
    stride = width * channels
    rows = _unfilter_rows(raw, width, height, channels, stride)
    return Image(width=width, height=height, rows=tuple(_rows_to_rgba(rows, width, height, channels)))


def _read_chunks(data: bytes) -> dict[bytes, list[bytes]]:
    chunks: dict[bytes, list[bytes]] = {}
    offset = len(PNG_SIGNATURE)
    while offset < len(data):
        if offset + 8 > len(data):
            raise ImageError("PNG chunk header is truncated.")
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        chunk_data_start = offset + 8
        chunk_data_end = chunk_data_start + length
        if chunk_data_end + 4 > len(data):
            raise ImageError("PNG chunk data is truncated.")
        chunk_data = data[chunk_data_start:chunk_data_end]
        chunks.setdefault(chunk_type, []).append(chunk_data)
        offset = chunk_data_end + 4
        if chunk_type == b"IEND":
            break
    return chunks


def _unfilter_rows(raw: bytes, width: int, height: int, channels: int, stride: int) -> list[bytes]:
    rows: list[bytes] = []
    offset = 0
    previous = bytes(stride)
    for _ in range(height):
        if offset + stride + 1 > len(raw):
            raise ImageError("PNG scanline data is truncated.")
        filter_type = raw[offset]
        row = bytearray(raw[offset + 1 : offset + 1 + stride])
        offset += stride + 1
        if filter_type == 1:
            _apply_sub_filter(row, channels)
        elif filter_type == 2:
            _apply_up_filter(row, previous)
        elif filter_type == 3:
            _apply_average_filter(row, previous, channels)
        elif filter_type == 4:
            _apply_paeth_filter(row, previous, channels)
        elif filter_type != 0:
            raise ImageError(f"Unsupported PNG filter type: {filter_type}")
        previous = bytes(row)
        rows.append(previous)
    return rows


def _rows_to_rgba(rows: list[bytes], width: int, height: int, channels: int):
    for y in range(height):
        row = rows[y]
        rgba = bytearray()
        for x in range(width):
            index = x * channels
            if channels == 1:
                gray = row[index]
                rgba.extend((gray, gray, gray, 255))
            elif channels == 3:
                rgba.extend((row[index], row[index + 1], row[index + 2], 255))
            else:
                rgba.extend((row[index], row[index + 1], row[index + 2], row[index + 3]))
        yield bytes(rgba)


def _apply_sub_filter(row: bytearray, channels: int) -> None:
    for i in range(len(row)):
        left = row[i - channels] if i >= channels else 0
        row[i] = (row[i] + left) & 0xFF


def _apply_up_filter(row: bytearray, previous: bytes) -> None:
    for i in range(len(row)):
        row[i] = (row[i] + previous[i]) & 0xFF


def _apply_average_filter(row: bytearray, previous: bytes, channels: int) -> None:
    for i in range(len(row)):
        left = row[i - channels] if i >= channels else 0
        up = previous[i]
        row[i] = (row[i] + ((left + up) // 2)) & 0xFF


def _apply_paeth_filter(row: bytearray, previous: bytes, channels: int) -> None:
    for i in range(len(row)):
        left = row[i - channels] if i >= channels else 0
        up = previous[i]
        upper_left = previous[i - channels] if i >= channels else 0
        row[i] = (row[i] + _paeth(left, up, upper_left)) & 0xFF


def _paeth(left: int, up: int, upper_left: int) -> int:
    estimate = left + up - upper_left
    distance_left = abs(estimate - left)
    distance_up = abs(estimate - up)
    distance_upper_left = abs(estimate - upper_left)
    if distance_left <= distance_up and distance_left <= distance_upper_left:
        return left
    if distance_up <= distance_upper_left:
        return up
    return upper_left


def _search_bounds(source: Image, template: Image, region: Region | None) -> tuple[int, int, int, int]:
    if region is None:
        return 0, 0, source.width - template.width, source.height - template.height
    if region.x + region.width > source.width or region.y + region.height > source.height:
        raise ImageError("Search region is outside the source image.")
    if template.width > region.width or template.height > region.height:
        return region.x, region.y, region.x - 1, region.y - 1
    return region.x, region.y, region.x + region.width - template.width, region.y + region.height - template.height


def _score_at(source: Image, template: Image, x: int, y: int, tolerance: int) -> float:
    total = template.width * template.height
    matches = 0
    for template_y in range(template.height):
        for template_x in range(template.width):
            source_pixel = source.pixel(x + template_x, y + template_y)
            template_pixel = template.pixel(template_x, template_y)
            if _pixels_match(source_pixel, template_pixel, tolerance):
                matches += 1
    return matches / total


def _pixels_match(left: tuple[int, int, int, int], right: tuple[int, int, int, int], tolerance: int) -> bool:
    return all(abs(left[index] - right[index]) <= tolerance for index in range(4))


def _match_exact_rows(source: Image, template: Image, x0: int, y0: int, x1: int, y1: int) -> MatchResult:
    first_template_row = template.rows[0]
    template_row_width = template.width * 4
    start_byte = x0 * 4
    end_byte = (x1 + template.width) * 4

    for y in range(y0, y1 + 1):
        source_row = source.rows[y]
        found_at = source_row.find(first_template_row, start_byte, end_byte)
        while found_at != -1:
            if found_at % 4 == 0:
                x = found_at // 4
                if x0 <= x <= x1 and _all_template_rows_match(source, template, x, y, template_row_width):
                    return MatchResult(matched=True, score=1.0, x=x, y=y)
            found_at = source_row.find(first_template_row, found_at + 4, end_byte)
    return MatchResult(matched=False, score=0.0)


def _all_template_rows_match(source: Image, template: Image, x: int, y: int, row_width: int) -> bool:
    start = x * 4
    end = start + row_width
    for template_y in range(template.height):
        if source.rows[y + template_y][start:end] != template.rows[template_y]:
            return False
    return True


def _raise_if_brute_force_too_large(source: Image, template: Image, x0: int, y0: int, x1: int, y1: int) -> None:
    positions = (x1 - x0 + 1) * (y1 - y0 + 1)
    comparisons = positions * template.width * template.height
    if comparisons <= MAX_BRUTE_FORCE_COMPARISONS:
        return
    raise ImageError(
        "No exact template match found, and fuzzy search is too large for the built-in matcher. "
        "Use --region to limit the search area, crop a smaller template, or use an exact screenshot-derived template."
    )
