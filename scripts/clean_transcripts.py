import json
import os
import re

def clean_text(text):
    # English filler words and hesitations
    parasites = r'\b(um|uh|er|ah|like|you know|well|so|actually|basically|literally|right|okay|ok)\b'
    text = re.sub(parasites, '', text, flags=re.IGNORECASE)
    
    # Remove repeated words (stuttering)
    text = re.sub(r'\b(\w+)\s+\1\b', r'\1', text)
    
    # Remove special characters but keep English letters, numbers, and basic punctuation
    text = re.sub(r'[^a-zA-Z0-9\s.,!?\'"-]', '', text)
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove extra whitespace
    text = ' '.join(text.split())

    return text

def clean_transcript_files():
    if not os.path.exists('dataset/raw/'):
        print("Error: dataset/raw/ directory does not exist!")
        return
    
    processed_count = 0
    
    for file in os.listdir('dataset/raw/'):
        if file.endswith('_transcript.json'):
            try:
                filepath = os.path.join('dataset/raw/', file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    transcript = json.load(f)
                
                # Clean each segment
                for segment in transcript:
                    if 'text' in segment:
                        segment['text'] = clean_text(segment['text'])
                
                # Save cleaned transcript
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(transcript, f, ensure_ascii=False, indent=4)
                
                processed_count += 1
                print(f"✓ Cleaned: {file}")
                
            except Exception as e:
                print(f"✗ Error processing {file}: {str(e)}")
    
    print(f"\nCleaning completed! Processed {processed_count} files.")

for file in os.listdir('dataset/raw/'):
    if file.endswith('_transcript.json'):
        with open(f'dataset/raw/{file}', 'r', encoding='utf-8') as f:
            transcript = json.load(f)

        for segment in transcript:
            segment['text'] = clean_text(segment['text'])

        with open(f'dataset/raw/{file}', 'w', encoding='utf-8') as f:
            json.dump(transcript, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    clean_transcript_files()
