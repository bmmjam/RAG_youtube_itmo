import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler

import httpx
import openai
import yt_dlp
from dotenv import load_dotenv
from openai import OpenAI


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(module)s: %(message)s",
    handlers=[
        RotatingFileHandler(
            os.path.join(os.path.dirname(__file__), "../app/logs/app.log"), maxBytes=5000000, backupCount=2
        ),
        logging.StreamHandler(),
    ],
)
load_dotenv()
PROXY = os.getenv("PROXY")
http_client = httpx.Client(proxies=PROXY)
client = OpenAI(http_client=http_client)


@dataclass()
class ParserTranscribe:
    """
    A pipeline for downloading and transcribing audio from YouTube videos.
    Has two public methods:
    - get_transcribe_video(url_of_video: str) - downloads and transcribes audio
    and saves data to a json file
    - get_video_urls(channel_url: str) - get list of all video urls from youtube-channel
    """

    path_to_save: str  # Путь к папке с аудио
    json_video_info_path: str  # Путь к json-файлу
    segment_time: int = 900  # Длительность сегмента при нарезке аудио
    max_attempts: int = 5  # максимальное количество попыток
    delay: int = 10  # задержка между попытками в секундах

    def _get_video_info(self, video_url: str) -> dict:
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(self.path_to_save, "%(id)s.%(ext)s"),
            "quiet": True,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)

        audio_path = os.path.join(self.path_to_save, f"{info['id']}.mp3")

        return {
            "url": video_url,
            "title": info.get("title"),
            "description": info.get("description"),
            "audio_path": audio_path,
        }

    def _download_channel_audio_track(self, url_of_video: str) -> str:
        """
        Download audio track from YouTube-video and save info to json.
        Return path to downloaded audio track
        """
        if os.path.exists(self.json_video_info_path):
            with open(self.json_video_info_path, "r", encoding="utf-8") as f:
                video_info = json.load(f)
        else:
            video_info = []
        url_info = self._get_video_info(url_of_video)
        # print(f"Path to mp4 file: {url_info['audio_path']}\n")
        logging.info("Path to mp4 file: %s\n", url_info['audio_path'])

        video_info_item = {"url": [], "title": [], "description": [], "audio_path": [], "text": []}
        for key, value in url_info.items():
            video_info_item[key].append(value)

        # Проверяем, что такого url в json нет
        exist_url = True
        if video_info:
            for itm in video_info:
                exist_url = exist_url and (itm["url"][0] != video_info_item["url"][0])
        if exist_url:
            video_info.append(video_info_item)

        with open(self.json_video_info_path, "w", encoding="utf-8") as f:
            json.dump(video_info, f, ensure_ascii=False, indent=4)

        return video_info_item["audio_path"][0]

    def _split_audio(self, file_path, output_pattern):
        """
        Разделяет аудиофайл на сегменты с использованием утилиты ffmpeg.

        Parameters
        ----------
        file_path : str
            Путь к исходному аудиофайлу, который необходимо разделить.
        output_pattern : str
            Шаблон имени выходного файла. Должен содержать %03d для нумерации сегментов
            (например, "output_segment%03d.mp3").

        Returns
        -------
        None

        """
        cmd = [
            "ffmpeg",
            "-i",
            file_path,
            "-f",
            "segment",
            "-segment_time",
            str(self.segment_time),
            "-c:a",
            "libmp3lame",
            output_pattern,
        ]
        subprocess.run(cmd, check=False)

    def _transcribe_with_whisper(self, audio_path):
        """
        Транскрибирует аудиофайл с использованием модели Whisper от OpenAI.

        Функция пытается транскрибировать аудио многократно
        (до max_attempts раз) в случае ошибок API.

        Parameters
        ----------
        audio_path : str
            Путь к аудиофайлу, который необходимо транскрибировать.

        Returns
        -------
        str
            Транскрибированный текст аудиофайла.

        Raises
        ------
        openai.APITimeoutError
            Если после всех попыток транскрибировать аудио возникает ошибка.

        """

        for attempt in range(self.max_attempts):
            try:
                with open(audio_path, "rb") as audio_file:
                    transcript = client.audio.transcriptions.create(
                        file=audio_file, model="whisper-1", response_format="text", language=["ru"]
                    )
                return transcript
            except openai.APITimeoutError as e:
                print(f"Ошибка при обращении к API (попытка {attempt + 1}): {e}")
                if attempt < self.max_attempts - 1:  # если это не последняя попытка
                    print(f"Ожидание {self.delay} секунд перед следующей попыткой...")
                    time.sleep(self.delay)
                else:
                    print("Превышено максимальное количество попыток.")
                    raise  # повторно вызываем исключение, чтобы сообщить о проблеме
        return None

    def _get_transcribe(self, audio_path: str):
        file_name = os.path.basename(audio_path)

        if not file_name.endswith((".mp3", ".wav", ".m4a")):
            logging.warning("Unsupported audio format: %s", file_name)
            return

        output_pattern = os.path.join(self.path_to_save, f"{file_name[:-4]}_segment%03d.mp3")

        self._split_audio(audio_path, output_pattern)

        transcriptions = []
        segment_files = sorted(f for f in os.listdir(self.path_to_save) if f.startswith(file_name[:-4] + "_segment"))

        for i, segment_file in enumerate(segment_files):
            logging.info("Transcribe %s segment", i)
            segment_path = os.path.join(self.path_to_save, segment_file)
            transcriptions.append(self._transcribe_with_whisper(segment_path))
            os.remove(segment_path)

        os.remove(audio_path)

        with open(self.json_video_info_path, "r", encoding="utf-8") as f:
            data_list = json.load(f)

        for item in data_list:
            if item["audio_path"][0] == audio_path:
                item["text"] = transcriptions
                break

        with open(self.json_video_info_path, "w", encoding="utf-8") as f:
            json.dump(data_list, f, ensure_ascii=False, indent=4)

    def get_transcribe_video(self, url_of_video: str):
        """Основная функция для полного запуска пайплайна транскрибации видео по ссылке"""
        audio_path = self._download_channel_audio_track(url_of_video)
        self._get_transcribe(audio_path)


if __name__ == "__main__":
    parser = ParserTranscribe("../data/audio", "../data/video_info.json")
