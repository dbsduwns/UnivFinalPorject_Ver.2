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


@dataclass(frozen=True)
class _OcrCandidate:
    preprocessing: str
    lines: list[str]
    mean_confidence: float
    korean_ratio: float
    score: float


# Ratios measured from the stable weekly menu template. The first column contains
# section labels and the remaining five columns contain Monday through Friday.
_DAY_COLUMN_EDGES = (0.124, 0.303, 0.478, 0.653, 0.826, 1.0)
# The detected bounds include the title above the table. These ratios align with
# the actual menu row borders in the published template and exclude the header
# and notice rows.
_SECTION_BANDS = (
    ("중식", "일품 1", 0.110, 0.372),
    ("중식", "일품 2", 0.372, 0.658),
    ("석식", "일품 2", 0.658, 0.919),
)
_ORIGIN_WORDS = ("국산", "외국산", "미국산", "중국산", "브라질산")
_PARENTHETICAL_CONTENT_PATTERN = re.compile(
    r"[\(\[（［][^\)\]）］]*[\)\]）］]"
)
_UNCLOSED_PARENTHETICAL_PATTERN = re.compile(r"[\(\[（［][^\)\]）］]*$")


def remove_parenthetical_content(value: str) -> str:
    """Remove origin notes and other OCR text enclosed by bracket variants."""
    value = _PARENTHETICAL_CONTENT_PATTERN.sub(" ", value)
    value = _UNCLOSED_PARENTHETICAL_PATTERN.sub(" ", value)
    return re.sub(r"\s+", " ", value).strip()


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


def _resize_grayscale_cell(cell, cv2):
    gray = cv2.cvtColor(cell, cv2.COLOR_BGR2GRAY)
    return cv2.resize(
        gray,
        None,
        fx=2.5,
        fy=2.5,
        interpolation=cv2.INTER_CUBIC,
    )


def _prepare_cell_variants(cell, cv2) -> list[tuple[str, object]]:
    resized = _resize_grayscale_cell(cell, cv2)
    blurred = cv2.GaussianBlur(resized, (3, 3), 0)
    otsu = cv2.threshold(
        resized,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )[1]
    blurred_otsu = cv2.threshold(
        blurred,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )[1]
    adaptive = cv2.adaptiveThreshold(
        resized,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        35,
        11,
    )
    return [
        ("grayscale", resized),
        ("otsu", otsu),
        ("adaptive", adaptive),
        ("blurred_otsu", blurred_otsu),
    ]


def _prepare_cell(cell, cv2):
    """Return the stable binary image used by numeric price OCR."""
    resized = _resize_grayscale_cell(cell, cv2)
    blurred = cv2.GaussianBlur(resized, (3, 3), 0)
    return cv2.threshold(
        blurred,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )[1]


def _read_ocr_candidate(
    prepared,
    preprocessing: str,
    pytesseract_module,
) -> _OcrCandidate | None:
    from pytesseract import Output

    data = pytesseract_module.image_to_data(
        prepared,
        lang=os.getenv("MENU_OCR_LANG", "kor"),
        config="--oem 1 --psm 6",
        output_type=Output.DICT,
    )

    grouped: dict[tuple[int, int, int], list[str]] = {}
    accepted_words: list[tuple[str, float]] = []
    for index, raw_text in enumerate(data["text"]):
        text = raw_text.strip()
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
        accepted_words.append((text, confidence))

    if not accepted_words:
        return None

    lines = [" ".join(words) for words in grouped.values()]
    character_weights = [max(len(text), 1) for text, _ in accepted_words]
    weight_sum = sum(character_weights)
    mean_confidence = sum(
        confidence * weight
        for (_, confidence), weight in zip(accepted_words, character_weights)
    ) / weight_sum

    combined_text = " ".join(text for text, _ in accepted_words)
    korean_count = len(re.findall(r"[가-힣]", combined_text))
    letter_count = len(re.findall(r"[가-힣A-Za-z]", combined_text))
    korean_ratio = korean_count / letter_count if letter_count else 0.0

    # Confidence is primary. Korean ratio rejects symbol-heavy results, while a
    # small coverage bonus prevents a single easy word from beating a complete cell.
    score = (
        mean_confidence
        + korean_ratio * 12.0
        + min(korean_count, 30) * 0.3
    )
    return _OcrCandidate(
        preprocessing=preprocessing,
        lines=lines,
        mean_confidence=mean_confidence,
        korean_ratio=korean_ratio,
        score=score,
    )


def _ocr_lines(cell, cv2, pytesseract_module) -> list[str]:
    candidates = [
        candidate
        for preprocessing, prepared in _prepare_cell_variants(cell, cv2)
        if (
            candidate := _read_ocr_candidate(
                prepared,
                preprocessing,
                pytesseract_module,
            )
        ) is not None
    ]
    if not candidates:
        return []

    selected = max(candidates, key=lambda candidate: candidate.score)
    if os.getenv("MENU_OCR_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}:
        candidate_scores = ", ".join(
                f"{candidate.preprocessing}:{candidate.score:.1f}"
                for candidate in candidates
        )
        print(
            "🔎 식단 OCR 전처리 선택: "
            f"{selected.preprocessing}({selected.score:.1f}) "
            f"후보=[{candidate_scores}]"
        )
    return selected.lines


def _normalize_menu_lines(lines: Sequence[str]) -> list[str]:
    items: list[str] = []
    for raw_line in lines:
        if "미운영" in raw_line:
            return []

        line = remove_parenthetical_content(raw_line)
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
        lang=os.getenv("MENU_OCR_LANG", "kor"),
        config="--oem 1 --psm 6 -c tessedit_char_whitelist=0123456789,.",
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
