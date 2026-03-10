import json
from pathlib import Path

from PIL import Image, ImageDraw

from advanced_testing import AdvancedTestRunner, build_sample_single_input


def ensure_sample_packaging_image(image_path: Path):
    if image_path.exists():
        return

    image = Image.new("RGB", (320, 320), color=(255, 235, 200))
    draw = ImageDraw.Draw(image)
    draw.rectangle((30, 30, 290, 290), fill=(255, 140, 90))
    draw.text((70, 120), "KIDS", fill=(255, 255, 255))
    draw.text((60, 160), "ANTI CAVITY", fill=(255, 255, 255))
    image.save(image_path)


def main():
    base_dir = Path(__file__).resolve().parent
    output_dir = base_dir / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    image_path = output_dir / "sample_packaging.png"
    ensure_sample_packaging_image(image_path)

    runner = AdvancedTestRunner(base_dir / "persona_samples_complete.json")
    report = runner.run_packaging_review(build_sample_single_input(), image_path)

    json_path = output_dir / "packaging_review_report.json"
    md_path = output_dir / "packaging_review_report.md"

    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    with open(md_path, "w", encoding="utf-8") as handle:
        handle.write(runner.render_packaging_markdown(report))

    print("Packaging review report generated.")
    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")


if __name__ == "__main__":
    main()
