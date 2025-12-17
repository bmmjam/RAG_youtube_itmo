import json

from pytube import YouTube


with open('dataset/sources.txt', 'r') as f:
    urls = [line.strip() for line in f if line.strip()]

video_info = []
for url in urls:
    yt = YouTube(url)
    info = {
        'video_id': yt.video_id,
        'title': yt.title,
        'description': yt.description,
        'length': yt.length,  # в секундах
        'publish_date': str(yt.publish_date),  # преобразуем в строку
    }
    video_info.append(info)

with open('dataset/meta/video_info.json', 'w', encoding='utf-8') as f:
    json.dump(video_info, f, ensure_ascii=False, indent=4)

print("Метаданные сохранены в dataset/meta/video_info.json")
