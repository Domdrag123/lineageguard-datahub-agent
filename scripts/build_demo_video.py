from __future__ import annotations

import subprocess
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
import imageio_ffmpeg


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "video" / "build"
W, H = 1280, 720
BG = "#070b0a"
TEXT = "#f3f7f4"
MUTED = "#9aacA2"
MINT = "#62e6ae"
RED = "#ff695e"


def font(size: int, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    if mono:
        path = Path("C:/Windows/Fonts/consola.ttf")
    elif bold:
        path = Path("C:/Windows/Fonts/segoeuib.ttf")
    else:
        path = Path("C:/Windows/Fonts/segoeui.ttf")
    return ImageFont.truetype(str(path), size=size)


def wrap(draw: ImageDraw.ImageDraw, text: str, width: int, face: ImageFont.FreeTypeFont) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=face) <= width:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def slide(title: str, body: str, number: str, *, accent: str = MINT, screenshot: Image.Image | None = None) -> Image.Image:
    canvas = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, W, 6), fill=accent)
    draw.text((64, 44), "LINEAGEGUARD  /  DATAHUB AGENT HACKATHON", font=font(15, mono=True), fill=MINT)
    draw.text((1168, 42), number, font=font(18, mono=True), fill="#52655c")

    content_width = 520 if screenshot else 1080
    title_face = font(54, bold=True)
    y = 142
    for line in wrap(draw, title, content_width, title_face):
        draw.text((64, y), line, font=title_face, fill=TEXT)
        y += 62
    body_face = font(24)
    y += 25
    for line in wrap(draw, body, content_width, body_face):
        draw.text((66, y), line, font=body_face, fill=MUTED)
        y += 36

    if screenshot is not None:
        shot = screenshot.copy().convert("RGB")
        shot.thumbnail((610, 520), Image.Resampling.LANCZOS)
        shadow = Image.new("RGBA", (shot.width + 34, shot.height + 34), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle((14, 14, shot.width + 20, shot.height + 20), radius=18, fill=(0, 0, 0, 180))
        shadow = shadow.filter(ImageFilter.GaussianBlur(10))
        x = 625 + (610 - shot.width) // 2
        sy = 120 + (520 - shot.height) // 2
        canvas.paste(shadow, (x - 17, sy - 17), shadow)
        canvas.paste(shot, (x, sy))
        ImageDraw.Draw(canvas).rounded_rectangle((x - 1, sy - 1, x + shot.width, sy + shot.height), radius=9, outline="#2e443a", width=2)

    draw.text((64, 665), "Grounded context  •  deterministic policy  •  reversible action", font=font(16), fill="#5f746a")
    return canvas


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    screenshot = Image.open(ROOT / "assets" / "lineageguard-demo.png")
    # Increase readability when the full interface is scaled into the video.
    screenshot = ImageEnhance.Contrast(screenshot).enhance(1.08)
    slides = [
        slide("Know the blast radius before you merge.", "DataHub-grounded change safety for data pipelines, dashboards and production ML.", "01", screenshot=screenshot),
        slide("Context, not guesswork.", "The agent calls DataHub get_entities, list_schema_fields and get_lineage, then normalizes ownership, tags, schema and downstream dependencies.", "02"),
        slide("One field. Four downstream risks.", "Dropping customer_email reaches dbt, a revenue dashboard, an unowned Airflow feature job and the churn-risk-v4 model.", "03", accent=RED, screenshot=screenshot),
        slide("Fail closed. Explain everything.", "BLOCK · 100/100 risk · four explicit findings · a SHA-256 receipt that can be replayed and audited.", "04", accent=RED),
        slide("Recovery is part of the answer.", "LineageGuard creates owner-scoped tickets for dual-write, backfill, contract tests and rollback—then previews DataHub tags and a review document.", "05"),
        slide("From context graph to accountable action.", "A runnable Apache-2.0 prototype with a zero-install demo and a production path through DataHub's official MCP server.", "06", screenshot=screenshot),
    ]
    durations = [12, 13, 14, 13, 14, 14]
    image_paths: list[Path] = []
    for index, image in enumerate(slides, start=1):
        path = OUT / f"slide-{index:02d}.png"
        image.save(path, optimize=True)
        image_paths.append(path)

    concat = OUT / "slides.txt"
    lines: list[str] = []
    for path, duration in zip(image_paths, durations):
        lines.extend([f"file '{path.as_posix()}'", f"duration {duration}"])
    lines.append(f"file '{image_paths[-1].as_posix()}'")
    concat.write_text("\n".join(lines) + "\n", encoding="utf-8")

    audio = ROOT / "video" / "narration.wav"
    output = ROOT / "video" / "lineageguard-demo.mp4"
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(), "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat),
        "-i", str(audio), "-shortest",
        "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "medium",
        "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(output),
    ]
    subprocess.run(command, check=True)
    with wave.open(str(audio), "rb") as handle:
        duration = handle.getnframes() / handle.getframerate()
    print(f"built={output} bytes={output.stat().st_size} narration_seconds={duration:.2f}")


if __name__ == "__main__":
    main()
