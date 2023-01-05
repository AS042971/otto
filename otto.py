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

from pydantic import BaseModel


ROOT = Path(__file__).parent
ASSETS_DIR = ROOT / 'assets'

CONFIG = json.loads((ROOT / 'config.json').read_text('utf8'))

# Pinyin audio files.
PINYIN: dict[str, str] = CONFIG['pinyin']

# Special audio files.
SPECIAL: dict[str, Union[str, list[str]]] = CONFIG['special']

# Silent audio segment duration(ms) for missing pinyin.
MISSING_SILENT_DURATION: int = CONFIG['silentDuration']

# Target sample rate.
SAMPLE_RATE: int = CONFIG['sampleRate']

# Server port.
PORT: int = CONFIG['port']

# Special fragments mapping, especially for those with `\` to avoid being treated as regex.
FRAGMENTS_MAP: dict[str, str] = CONFIG['fragmentsMap']


def break_text(text: str) -> list[str]:
    """
    Breaks text into fragments.
    :param text: the text to break.
    :return: text fragments.
    """
    return [FRAGMENTS_MAP.get(t, t) for t in re.split(f'({"|".join(SPECIAL.keys())})', text) if t]


def merge_segments(segments: Iterable[AudioSegment]) -> AudioSegment:
    """
    Merge all segments.
    :param segments: audio segments.
    :return: merged audio segments.
    """
    return reduce(lambda a, b: a + b, segments)


def load_audio_file(filename: Union[str, Iterable[str]]) -> AudioSegment:
    """
    Loads audio file or a list of audio files.
    :param filename: file name or a list of file names.
    :return: the audio segment.
    """
    if isinstance(filename, str):
        return normalize(
            AudioSegment.from_file(ASSETS_DIR / filename)
            .set_channels(1)
            .set_frame_rate(SAMPLE_RATE)
        )

    return merge_segments(load_audio_file(file) for file in filename)


def load_pinyin_audio(pinyin: str) -> AudioSegment:
    """
    Loads pinyin. It will return a silent segment if not existing.
    :param pinyin: the pinyin to load.
    :return: the audio segment.
    """
    if pinyin not in PINYIN:
        return AudioSegment.silent(MISSING_SILENT_DURATION, SAMPLE_RATE)
    return load_audio_file(PINYIN[pinyin])


def load_fragment_audio(fragment: str) -> AudioSegment:
    """
    Loads audio for a fragment broken by `break_text`.
    :param fragment: the fragment to load.
    :return: the audio segment.
    """
    if fragment in SPECIAL:
        return load_audio_file(SPECIAL[fragment])
    return merge_segments(load_pinyin_audio(p) for p in lazy_pinyin(fragment))


def make_audio(text: str) -> AudioSegment:
    """
    Makes an audio for any text.
    :param text: the text to make an audio.
    :return: the audio segment.
    """
    fragments = break_text(text)
    return merge_segments(load_fragment_audio(frag) for frag in fragments)


app = FastAPI()


class Body(BaseModel):
    text: str


@app.get('/otto')
async def handle_otto(text: str):
    file = io.BytesIO()
    data = make_audio(text)
    data.export(file, format='wav')
    file.seek(0, 0)
    return StreamingResponse(file, media_type='audio/wav')


@app.post('/otto')
async def handle_post_otto(body: Body):
    return await handle_otto(body.text)


if __name__ == '__main__':
    uvicorn.run('__main__:app', port=PORT)
