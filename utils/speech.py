import json, os
from pathlib import Path
import subprocess, tempfile

import openai
from openai import BadRequestError

# --- API KEY SETUP ---------------------------------------------------------
if "OPENAI_API_KEY" in os.environ:
    openai.api_key = os.environ["OPENAI_API_KEY"]
else:
    try:
        cfg = json.load(open("config.json"))
        openai.api_key = cfg["openai_api_key"]
    except Exception:
        raise RuntimeError("OpenAI APIキーが設定されていません。環境変数 OPENAI_API_KEY を設定するか config.json に記入してください。")

# ---------------------------------------------------------------------------

# supported container/codec combos openai reliably accepts
SUPPORTED_EXT = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm"}

def _convert_to_mp3(src: Path) -> Path:
    """Convert audio to mp3 16kHz mono using ffmpeg and return new Path."""
    dst = Path(tempfile.gettempdir()) / (src.stem + "_conv.mp3")
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(src),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-codec:a",
        "libmp3lame",
        "-b:a",
        "128k",
        str(dst),
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError("ffmpeg 変換に失敗しました。ffmpeg がインストールされているか確認してください。\n" + result.stderr.decode(errors="ignore"))
    return dst

def _convert_to_wav(src: Path) -> Path:
    """Convert audio to wav 16kHz mono using ffmpeg and return new Path."""
    dst = Path(tempfile.gettempdir()) / (src.stem + "_conv.wav")
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(src),
        "-ac",
        "1",
        "-ar",
        "16000",
        str(dst),
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError("ffmpeg 変換に失敗しました。ffmpeg がインストールされているか確認してください。\n" + result.stderr.decode(errors="ignore"))
    return dst

def _ensure_supported(path: Path) -> Path:
    if path.suffix.lower() in SUPPORTED_EXT:
        return path
    # fallback convert
    return _convert_to_mp3(path)

audio_model = "whisper-1"

def _transcribe_once(path: Path):
    with open(path, "rb") as f:
        return openai.audio.transcriptions.create(model=audio_model, file=f).text.strip()

def transcribe(file_path: Path) -> str:
    path = _ensure_supported(file_path)
    try:
        return _transcribe_once(path)
    except BadRequestError:
        # force convert to wav and retry
        wav = _convert_to_wav(file_path)
        return _transcribe_once(wav)
