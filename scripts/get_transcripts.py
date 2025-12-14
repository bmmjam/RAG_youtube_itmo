import json

import whisper
from pytube import YouTube


model = whisper.load_model("medium")

with open('dataset/meta/video_info.json', 'r', encoding='utf-8') as f:
    video_info = json.load(f)

for info in video_info:
    url = f"https://www.youtube.com/watch?v={info['video_id']}"
    yt = YouTube(url)

    audio_stream = yt.streams.filter(only_audio=True).first()
    audio_path = f"temp_{info['video_id']}.mp4"
    audio_stream.download(filename=audio_path)

    result = model.transcribe(audio_path, verbose=True, fp16=False)

    transcript = result['segments']  # Каждый: {'id':, 'start':, 'end':, 'text':}

    with open(f"dataset/raw/{info['video_id']}_transcript.json", 'w', encoding='utf-8') as f:
        json.dump(transcript, f, ensure_ascii=False, indent=4)

    import os

    os.remove(audio_path)

print("Транскрипты сохранены в dataset/raw/")
