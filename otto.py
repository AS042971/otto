import io
import re
import json

import uvicorn

from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pypinyin import lazy_pinyin

from pydub import AudioSegment
from pydub.effects import normalize

from functools import reduce
from typing import Iterable, Union


ROOT = Path(__file__).parent
ASSETS_DIR = ROOT / 'assets'

CONFIG = json.loads((ROOT / 'config.json').read_text('utf8'))

# Pinyin audio list.
PINYIN: dict[str, str] = CONFIG['pinyin']

# Special audio list.
SPECIAL: dict[str, Union[str, list[str]]] = CONFIG['special']

# Silent audio segment duration(ms) for missing pinyin.
MISSING_SILENT_DURATION: int = CONFIG['silentDuration']

# Target sample rate.
SAMPLE_RATE: int = CONFIG['sampleRate']


# Port.
PORT: int = CONFIG['port']


def make_text_fragments(text: str) -> list[str]:
    return [t for t in re.split(f'({"|".join(SPECIAL.keys())})', text) if t]


def load_audio_file(filename: Union[str, Iterable[str]]) -> AudioSegment:
    if isinstance(filename, str):
        return normalize(
            AudioSegment.from_file(ASSETS_DIR / filename)
            .set_channels(1)
            .set_frame_rate(SAMPLE_RATE)
        )

    return reduce(lambda a, b: a + b, (load_audio_file(file) for file in filename))


def load_pinyin(pinyin: str) -> AudioSegment:
    if pinyin not in PINYIN:
        return AudioSegment.silent(MISSING_SILENT_DURATION, SAMPLE_RATE)
    return load_audio_file(PINYIN[pinyin])


def load_audio_fragment(fragment: str) -> AudioSegment:
    if fragment in SPECIAL:
        return load_audio_file(SPECIAL[fragment])
    return reduce(lambda a, b: a + b, (load_pinyin(pinyin) for pinyin in lazy_pinyin(fragment)))


def make_audio(text: str) -> AudioSegment:
    fragments = make_text_fragments(text)
    audio = reduce(lambda a, b: a + b, (load_audio_fragment(frag) for frag in fragments))
    return audio


app = FastAPI()


@app.get('/otto')
async def handle_otto(text: str):
    file = io.BytesIO()
    data = make_audio(text)
    data.export(file, format='wav')
    file.seek(0, 0)
    return StreamingResponse(file, media_type='audio/wav')


if __name__ == '__main__':
    uvicorn.run('__main__:app', port=PORT)
