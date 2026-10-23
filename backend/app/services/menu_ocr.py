"""Extract structured daily menus from the university's weekly menu image."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import os
import re
from typing import Sequence


@dataclass(frozen=True)
class ExtractedMenuSection:
    meal_type: str
    corner: str
    price: int | None
    items: list[str]


# Ratios measured from the stable weekly menu template. The first column contains
# section labels and the remaining five columns contain Monday through Friday.
_DAY_COLUMN_EDGES = (0.124, 0.303, 0.478, 0.653, 0.826, 1.0)
_SECTION_BANDS = (
    ("중식", "정식", 0.047, 0.343),
    ("중식", "일품", 0.343, 0.550),
    ("중식", "돈가스", 0.550, 0.625),
    ("석식", "정식", 0.625, 0.927),
)
_ORIGIN_WORDS = ("국산", "외국산", "미국산", "중국산", "브라질산")


def _configure_tesseract(pytesseract_module) -> None:
    command = os.getenv("TESSERACT_CMD")
    if command:
        pytesseract_module.pytesseract.tesseract_cmd = command


def _find_table_bounds(image, cv2):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    binary = cv2.threshold(gray, 210, 255, cv2.THRESH_BINARY_INV)[1]
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    height, width = gray.shape
    candidates = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w >= width * 0.65 and h >= height * 0.55:
            candidates.append((w * h, x, y, w, h))

    if candidates:
        _, x, y, w, h = max(candidates)
        return x, y, w, h

    # Safe fallback for the published template when the outer border is faint.
    return (
        int(width * 0.075),
        int(height * 0.085),
        int(width * 0.852),
        int(height * 0.845),
    )


def _prepare_cell(cell, cv2):
    gray = cv2.cvtColor(cell, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    return cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]


def _ocr_lines(cell, cv2, pytesseract_module) -> list[str]:
    from pytesseract import Output

    prepared = _prepare_cell(cell, cv2)
    data = pytesseract_module.image_to_data(
        prepared,
        lang=os.getenv("MENU_OCR_LANG", "kor+eng"),
        config="--oem 1 --psm 6",
        output_type=Output.DICT,
    )

    grouped: dict[tuple[int, int, int], list[str]] = {}
    for index, text in enumerate(data["text"]):
        text = text.strip()
        if not text:
            continue
        try:
            confidence = float(data["conf"][index])
        except (TypeError, ValueError):
            confidence = -1
        if confidence < 10:
            continue
        key = (
            data["block_num"][index],
            data["par_num"][index],
            data["line_num"][index],
        )
        grouped.setdefault(key, []).append(text)
    return [" ".join(words) for words in grouped.values()]


def _normalize_menu_lines(lines: Sequence[str]) -> list[str]:
    items: list[str] = []
    for raw_line in lines:
        if "미운영" in raw_line:
            return []

        line = re.sub(r"\([^)]*\)", " ", raw_line)
        line = re.sub(r"^[\s·•\-–—|]+|[\s·•\-–—|]+$", "", line)
        line = re.sub(r"\s+", " ", line).strip()
        if not line or not re.search(r"[가-힣A-Za-z]", line):
            continue
        if any(word in line for word in _ORIGIN_WORDS) and (
            ":" in line or "/" in line or "," in line
        ):
            continue
        if line in {"Mon", "Tue", "Wed", "Thu", "Fri", "중식", "석식"}:
            continue
        if line not in items:
            items.append(line[:200])
    return items


def _read_price(label_cell, cv2, pytesseract_module) -> int | None:
    prepared = _prepare_cell(label_cell, cv2)
    text = pytesseract_module.image_to_string(
        prepared,
        lang=os.getenv("MENU_OCR_LANG", "kor+eng"),
        config="--oem 1 --psm 6",
    )
    for value in re.findall(r"\d[\d,\.]{2,}", text):
        digits = re.sub(r"\D", "", value)
        if digits:
            price = int(digits)
            if 1_000 <= price <= 50_000:
                return price
    return None


def extract_weekly_menu(
    image_bytes: bytes,
    menu_dates: Sequence[date],
) -> dict[date, list[ExtractedMenuSection]]:
    """Return OCR results for up to five weekday columns in a menu image."""
    if not image_bytes:
        raise ValueError("식단 이미지가 비어 있습니다.")
    if not menu_dates:
        raise ValueError("식단 날짜가 없습니다.")

    try:
        import cv2
        import numpy as np
        import pytesseract
    except ImportError as exc:
        raise RuntimeError(
            "식단 OCR 의존성이 없습니다. opencv-python-headless와 pytesseract를 설치하세요."
        ) from exc

    _configure_tesseract(pytesseract)
    image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("식단 이미지를 해석할 수 없습니다.")

    table_x, table_y, table_width, table_height = _find_table_bounds(image, cv2)
    results: dict[date, list[ExtractedMenuSection]] = {}
    dates = list(menu_dates)[:5]

    for day_index, menu_date in enumerate(dates):
        sections: list[ExtractedMenuSection] = []
        x1 = table_x + int(table_width * _DAY_COLUMN_EDGES[day_index]) + 3
        x2 = table_x + int(table_width * _DAY_COLUMN_EDGES[day_index + 1]) - 3

        for meal_type, corner, y_start, y_end in _SECTION_BANDS:
            y1 = table_y + int(table_height * y_start) + 3
            y2 = table_y + int(table_height * y_end) - 3
            cell = image[y1:y2, x1:x2]
            items = _normalize_menu_lines(_ocr_lines(cell, cv2, pytesseract))
            if not items:
                continue

            label_x2 = table_x + int(table_width * _DAY_COLUMN_EDGES[0]) - 3
            label_cell = image[y1:y2, table_x + 3 : label_x2]
            price = _read_price(label_cell, cv2, pytesseract)
            sections.append(
                ExtractedMenuSection(
                    meal_type=meal_type,
                    corner=corner,
                    price=price,
                    items=items,
                )
            )
        results[menu_date] = sections

    if not any(results.values()):
        raise ValueError("식단 이미지에서 메뉴를 찾지 못했습니다.")
    return results
