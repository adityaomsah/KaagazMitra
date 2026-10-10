"""Generate clearly fake specimen document images for KaagazMitra testing.

Every image is a plain, generic white card with an invented 12-digit number and a
large semi-transparent red "SPECIMEN - NOT A REAL DOCUMENT" watermark. No real
government logo, emblem, seal, or document design is imitated.

Usage (from the KaagazMitra project root):
    .\\frontend\\.venv\\Scripts\\python.exe scripts\\make_specimens.py
"""

from __future__ import annotations

import random
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, features

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "samples" / "synthetic"
FONTS_DIR = Path(r"C:\Windows\Fonts")

CANVAS_SIZE = (1200, 750)
CARD_MARGIN = 30
BACKGROUND = (240, 240, 236)
CARD_FILL = (255, 255, 255)
CARD_BORDER = (170, 170, 170)
TITLE_BAR = (60, 60, 60)
TEXT_DARK = (25, 25, 25)
TEXT_MUTED = (110, 110, 110)
WATERMARK_TEXT = "SPECIMEN - NOT A REAL DOCUMENT"
WATERMARK_RGBA = (220, 0, 0, 90)
WATERMARK_ANGLE = 30

LATIN_REGULAR = ["arial.ttf", "segoeui.ttf"]
LATIN_BOLD = ["arialbd.ttf", "segoeuib.ttf"]
DEVANAGARI = ["Nirmala.ttc", "Mangal.ttf", "mangal.ttf"]

HAS_RAQM = features.check("raqm")

SMS_TEXT = (
    "Your application could not be processed due to name mismatch with Aadhaar records."
)


@dataclass(frozen=True)
class Field:
    label: str
    value: str
    devanagari: bool = False


@dataclass(frozen=True)
class Specimen:
    filename: str
    title: str
    fields: tuple[Field, ...]


SPECIMENS: tuple[Specimen, ...] = (
    Specimen(
        "anita_id.png",
        "IDENTITY CARD (SAMPLE)",
        (
            Field("Name", "Anita Verma"),
            Field("Date of Birth", "15/08/1996"),
            Field("Address", "Flat 12, Lake View Road, Guwahati"),
        ),
    ),
    Specimen(
        "anita_marksheet.png",
        "CLASS 10 MARKSHEET (SAMPLE)",
        (
            Field("Name", "Anita Sharma"),
            Field("Date of Birth", "15/08/1996"),
            Field("Father's Name", "Rajesh Sharma"),
        ),
    ),
    Specimen(
        "anita_bank.png",
        "BANK PASSBOOK (SAMPLE)",
        (
            Field("Name", "Anita Verma"),
            Field("Address", "House 4, MG Road, Jaipur"),
        ),
    ),
    Specimen(
        "anita_marriage.png",
        "MARRIAGE CERTIFICATE (SAMPLE)",
        (
            Field("Bride", "Anita Sharma"),
            Field("Married to", "Vikram Verma"),
            Field("Date of Marriage", "10/02/2024"),
        ),
    ),
    Specimen(
        "rahim_id.png",
        "IDENTITY CARD (SAMPLE)",
        (
            Field("Name", "Mohd. Rahim"),
            Field("Date of Birth", "12/04/2005"),
            Field("Father's Name", "Abdul Karim"),
        ),
    ),
    Specimen(
        "rahim_marksheet.png",
        "CLASS 10 MARKSHEET (SAMPLE)",
        (
            Field("Name", "Mohammad Rahim Ali"),
            Field("Date of Birth", "13/04/2005"),
            Field("Father's Name", "Abdul Karim"),
        ),
    ),
    Specimen(
        "rahim_bank.png",
        "BANK PASSBOOK (SAMPLE)",
        (
            Field("Name", "Mohd Rahim Ali"),
            Field("Date of Birth", "12/04/2005"),
        ),
    ),
    Specimen(
        "ramesh_land.png",
        "LAND RECORD (SAMPLE)",
        (Field("Name", "रमेश कुमार", devanagari=True),),
    ),
    Specimen(
        "ramesh_id.png",
        "IDENTITY CARD (SAMPLE)",
        (Field("Name", "Ramesh Kumar"),),
    ),
)


def load_font(
    size: int, bold: bool = False, devanagari: bool = False
) -> ImageFont.FreeTypeFont:
    """Load a TrueType font from the Windows font directory, with fallbacks."""
    if devanagari:
        candidates = DEVANAGARI
    else:
        candidates = LATIN_BOLD if bold else LATIN_REGULAR
    for name in candidates:
        path = FONTS_DIR / name
        if path.exists():
            kwargs: dict = {}
            if devanagari and HAS_RAQM:
                kwargs["layout_engine"] = ImageFont.Layout.RAQM
            return ImageFont.truetype(str(path), size, index=0, **kwargs)
    sys.exit(f"ERROR: none of these fonts were found in {FONTS_DIR}: {candidates}")


def invented_number(seed: str) -> str:
    """Return a deterministic, invented 12-digit number grouped as 'XXXX XXXX XXXX'."""
    rng = random.Random(seed)
    digits = str(rng.randint(2, 9)) + "".join(str(rng.randint(0, 9)) for _ in range(11))
    return f"{digits[0:4]} {digits[4:8]} {digits[8:12]}"


def draw_watermark(base: Image.Image) -> Image.Image:
    """Composite a large, rotated, semi-transparent red watermark over the image."""
    width, _ = base.size
    font_size = 80
    font = load_font(font_size, bold=True)
    # Shrink until the text fits comfortably along the diagonal.
    while font.getlength(WATERMARK_TEXT) > width * 0.95 and font_size > 20:
        font_size -= 4
        font = load_font(font_size, bold=True)

    left, top, right, bottom = font.getbbox(WATERMARK_TEXT)
    text_layer = Image.new("RGBA", (right - left + 20, bottom - top + 20), (0, 0, 0, 0))
    ImageDraw.Draw(text_layer).text(
        (10 - left, 10 - top), WATERMARK_TEXT, font=font, fill=WATERMARK_RGBA
    )
    rotated = text_layer.rotate(
        WATERMARK_ANGLE, expand=True, resample=Image.Resampling.BICUBIC
    )

    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    position = ((base.width - rotated.width) // 2, (base.height - rotated.height) // 2)
    overlay.alpha_composite(rotated, dest=position)
    return Image.alpha_composite(base, overlay)


def make_card(specimen: Specimen) -> Image.Image:
    """Render one generic specimen card."""
    width, height = CANVAS_SIZE
    image = Image.new("RGBA", CANVAS_SIZE, BACKGROUND + (255,))
    draw = ImageDraw.Draw(image)

    card = (CARD_MARGIN, CARD_MARGIN, width - CARD_MARGIN, height - CARD_MARGIN)
    draw.rounded_rectangle(card, radius=24, fill=CARD_FILL, outline=CARD_BORDER, width=3)

    # Plain title bar (no emblems, seals, flags, or colour schemes of real documents).
    bar = (card[0] + 3, card[1] + 3, card[2] - 3, card[1] + 100)
    draw.rounded_rectangle(bar, radius=20, fill=TITLE_BAR)
    draw.rectangle((bar[0], bar[3] - 20, bar[2], bar[3]), fill=TITLE_BAR)
    draw.text(
        (width // 2, (bar[1] + bar[3]) // 2),
        specimen.title,
        font=load_font(44, bold=True),
        fill="white",
        anchor="mm",
    )

    # Placeholder photo box.
    photo = (card[0] + 40, card[1] + 140, card[0] + 240, card[1] + 390)
    draw.rectangle(photo, outline=CARD_BORDER, width=3, fill=(248, 248, 248))
    small_font = load_font(20)
    draw.multiline_text(
        ((photo[0] + photo[2]) // 2, (photo[1] + photo[3]) // 2),
        "PHOTO\n(SAMPLE)",
        font=small_font,
        fill=TEXT_MUTED,
        anchor="mm",
        align="center",
    )

    # Label / value rows.
    label_font = load_font(28, bold=True)
    value_font = load_font(30)
    devanagari_font = load_font(34, devanagari=True)
    label_x = photo[2] + 40
    value_x = label_x + 260
    row_y = photo[1] + 10
    for field in specimen.fields:
        draw.text((label_x, row_y), f"{field.label}:", font=label_font, fill=TEXT_DARK)
        if field.devanagari:
            extra = {"language": "hi"} if HAS_RAQM else {}
            draw.text(
                (value_x, row_y - 6), field.value, font=devanagari_font, fill=TEXT_DARK, **extra
            )
        else:
            draw.text((value_x, row_y), field.value, font=value_font, fill=TEXT_DARK)
        row_y += 62

    # Invented 12-digit document number.
    number_y = photo[3] + 60
    draw.text((label_x, number_y), "Document No.:", font=label_font, fill=TEXT_DARK)
    draw.text(
        (value_x, number_y),
        invented_number(specimen.filename),
        font=load_font(32, bold=True),
        fill=TEXT_DARK,
    )

    # Footer disclaimer.
    draw.line((card[0] + 40, card[3] - 70, card[2] - 40, card[3] - 70), fill=CARD_BORDER, width=2)
    draw.text(
        (width // 2, card[3] - 40),
        "Synthetic test data generated for KaagazMitra - not issued by any authority",
        font=small_font,
        fill=TEXT_MUTED,
        anchor="mm",
    )

    return draw_watermark(image)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not HAS_RAQM:
        print(
            "WARNING: Pillow was built without libraqm; Devanagari is rendered with basic "
            "layout (matras may be slightly misplaced)."
        )

    for specimen in SPECIMENS:
        path = OUTPUT_DIR / specimen.filename
        make_card(specimen).convert("RGB").save(path, "PNG")
        print(f"Wrote {path}")

    sms_path = OUTPUT_DIR / "rahim_rejection_sms.txt"
    sms_path.write_text(SMS_TEXT + "\n", encoding="utf-8")
    print(f"Wrote {sms_path}")


if __name__ == "__main__":
    main()

