import io
import re
import json
import random
import uvicorn

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.backends.backend_agg import FigureCanvasAgg

from pydub import AudioSegment
from pydub.effects import normalize

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from typing import Union
from pathlib import Path
from pydantic import BaseModel
from pypinyin import lazy_pinyin
from functools import lru_cache


ROOT = Path(__file__).parent
ASSETS_DIR = ROOT / 'assets'

# Initialize matplotlib.
matplotlib.use('agg')

FONT_PROP = FontProperties(fname=ASSETS_DIR / 'font.otf')


CONFIG = json.loads((ROOT / 'config.json').read_text('utf8'))

# Silent audio segment duration(ms) for missing pinyin.
MISSING_SILENT_DURATION: int = CONFIG['silentDuration']

# Target sample rate.
SAMPLE_RATE: int = CONFIG['sampleRate']

# Server port.
PORT: int = CONFIG['port']

# Pinyin audio files.
PINYIN: dict[str, str] = CONFIG['pinyin']

# Special audio files.
SPECIAL_DICT: dict[str, Union[str, list[str]]] = CONFIG['special']

# Use sorted list to ensure that longer words are ahead of shorter ones.
# noinspection PyTypeChecker
SPECIAL_LIST: list[tuple[str, Union[str, list[str]]]] = sorted(
    SPECIAL_DICT.items(),
    key=lambda item: len(item[0]),
    reverse=True
)

# All regexes in the special dictionary.
SPECIAL_REGEXES: list[tuple[str, re.Pattern]] = [
    (regex, re.compile(regex))
    for regex, _ in SPECIAL_LIST
]

# The pattern with special regexes to cut text.
SPECIAL_PATTERN = re.compile(f'({"|".join(regex for regex, _ in SPECIAL_LIST)})')


def cut_text(text: str) -> list[str]:
    """
    Cuts text into fragments.
    Special ones are represented by their regexes.
    :param text: the text to cut.
    :return: text fragments.
    """

    def replace_regex(fragment: str) -> str:
        # Use regex to represent the fragment.
        for regex, pattern in SPECIAL_REGEXES:
            if pattern.fullmatch(fragment):
                return regex
        return fragment

    return [replace_regex(t) for t in SPECIAL_PATTERN.split(text) if t]


def load_audio_file(filename: Union[str, list[str]]) -> AudioSegment:
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

    # Load a random audio from the list.
    if filename[0] == 'RANDOM':
        return load_audio_file(random.choice(filename[1:]))

    return sum(load_audio_file(file) for file in filename)


@lru_cache()
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
    Loads audio for a fragment processed by `cut_text`.
    :param fragment: the fragment to load.
    :return: the audio segment.
    """
    if fragment in SPECIAL_DICT:
        return load_audio_file(SPECIAL_DICT[fragment])
    return sum(load_pinyin_audio(p) for p in lazy_pinyin(fragment))


def make_audio(text: str) -> AudioSegment:
    """
    Makes an audio for any text.
    :param text: the text to make an audio.
    :return: the audio segment.
    """
    fragments = cut_text(text)
    return sum(load_fragment_audio(frag) for frag in fragments)


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


@app.get('/otto/figure')
async def handle_figure(text: str):
    samples = make_audio(text).get_array_of_samples()
    fig = Figure()
    ax: plt.Axes = fig.subplots()
    ax.plot(samples)
    ax.set_title(text, fontproperties=FONT_PROP)
    ax.set_xlim(0, len(samples))

    image = io.BytesIO()
    FigureCanvasAgg(fig).print_jpg(image)
    image.seek(0, 0)
    return StreamingResponse(image, media_type='image/jpeg')


@app.post('/otto')
async def handle_post_otto(body: Body):
    return await handle_otto(body.text)


@app.post('/otto/figure')
async def handle_post_figure(body: Body):
    return await handle_figure(body.text)


if __name__ == '__main__':
    uvicorn.run('__main__:app', port=PORT)
