import re
import json
import os

def clean_text(text):
    parasites = r'\b(эээ|ну|вот|типа|как бы|ээ|эм|м|гм)\b'
    text = re.sub(parasites, '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(\w+)\s+\1\b', r'\1', text)
    text = re.sub(r'[^а-яА-Яa-zA-Z0-9\s.,!?]', '', text)
    text = text.lower()
    text = ' '.join(text.split())
    
    return text

for file in os.listdir('dataset/raw/'):
    if file.endswith('_transcript.json'):
        with open(f'dataset/raw/{file}', 'r', encoding='utf-8') as f:
            transcript = json.load(f)
        
        for segment in transcript:
            segment['text'] = clean_text(segment['text'])
        
        with open(f'dataset/raw/{file}', 'w', encoding='utf-8') as f:
            json.dump(transcript, f, ensure_ascii=False, indent=4)

print("Очистка завершена")
