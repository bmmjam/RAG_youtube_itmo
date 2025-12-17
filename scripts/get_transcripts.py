import json
import subprocess
import os
from pathlib import Path
import whisper

DATASET_RAW = Path("dataset/raw")
DATASET_META = Path("dataset/meta/video_info.json")

DATASET_RAW.mkdir(parents=True, exist_ok=True)

model = whisper.load_model("medium")

with open(DATASET_META, "r", encoding="utf-8") as f:
    video_info = json.load(f)

for info in video_info:
    video_id = info["video_id"]
    url = f"https://www.youtube.com/watch?v={video_id}"

    audio_path = DATASET_RAW / f"{video_id}.wav"
    transcript_path = DATASET_RAW / f"{video_id}_transcript.json"

    if transcript_path.exists():
        print(f"[SKIP] Transcript exists for {video_id}")
        continue

    print(f"[INFO] Downloading audio: {video_id}")

    try:
        subprocess.run(
            [
                "yt-dlp",
                "-f", "bestaudio",
                "--extract-audio",
                "--audio-format", "wav",
                "--audio-quality", "0",
                "-o", str(audio_path),
                url,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        print(f"[ERROR] Failed to download audio for {video_id}")
        continue

    print(f"[INFO] Transcribing: {video_id}")

    result = model.transcribe(
        str(audio_path),
        fp16=False,
        verbose=False
    )

    with open(transcript_path, "w", encoding="utf-8") as f:
        json.dump(result["segments"], f, ensure_ascii=False, indent=2)

    audio_path.unlink(missing_ok=True)

print("✅ Transcripts saved to dataset/raw/")

