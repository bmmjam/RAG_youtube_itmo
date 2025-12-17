import json
import subprocess
from pathlib import Path

DATASET_DIR = Path("dataset")
META_DIR = DATASET_DIR / "meta"
META_DIR.mkdir(parents=True, exist_ok=True)

with open(DATASET_DIR / "sources.txt") as f:
    urls = [line.strip() for line in f if line.strip()]

video_info = []

for url in urls:
    print(f"[INFO] Processing: {url}")

    cmd = [
        "yt-dlp",
        "--dump-single-json",
        "--skip-download",
        "--no-warnings",
        "--socket-timeout", "15",
        "--retries", "1",
        url,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,   # ← ВАЖНО
            check=True,
        )
        data = json.loads(result.stdout)

        video_info.append({
            "video_id": data.get("id"),
            "title": data.get("title"),
            "description": data.get("description"),
            "duration": data.get("duration"),
            "upload_date": data.get("upload_date"),
            "channel": data.get("channel"),
            "webpage_url": data.get("webpage_url"),
        })

    except Exception as e:
        print(f"[ERROR] Failed for {url}: {e}")

with open(META_DIR / "video_info.json", "w", encoding="utf-8") as f:
    json.dump(video_info, f, ensure_ascii=False, indent=2)

print("Метаданные сохранены в dataset/meta/video_info.json")

