import json
import os

MIN_CHUNK_WORDS = 300
MAX_CHUNK_WORDS = 600

for file in os.listdir('dataset/raw/'):
    if file.endswith('_transcript.json'):
        video_id = file.split('_transcript.json')[0]
        with open(f'dataset/raw/{file}', 'r', encoding='utf-8') as f:
            segments = json.load(f)
        
        chunks = []
        current_chunk = ""
        current_start = segments[0]['start']
        current_end = 0
        chunk_id = 0
        
        for seg in segments:
            words = seg['text'].split()
            if len(current_chunk.split()) + len(words) > MAX_CHUNK_WORDS:
                chunks.append({
                    'text': current_chunk.strip(),
                    'video_id': video_id,
                    'time_range': {'start': current_start, 'end': current_end},
                    'chunk_id': chunk_id
                })
                chunk_id += 1
                current_chunk = ""
                current_start = seg['start']
            
            current_chunk += " " + seg['text']
            current_end = seg['end']
        
        if current_chunk:
            chunks.append({
                'text': current_chunk.strip(),
                'video_id': video_id,
                'time_range': {'start': current_start, 'end': current_end},
                'chunk_id': chunk_id
            })
        
        # Сохраняем
        with open(f'dataset/chunks/{video_id}_chunks.json', 'w', encoding='utf-8') as f:
            json.dump(chunks, f, ensure_ascii=False, indent=4)

print("Чанки сохранены в dataset/chunks/")
