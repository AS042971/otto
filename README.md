# 电棍活字印刷

音源来自：https://github.com/DSP-8192/HuoZiYinShua

因为原项目作者只支持以本地 `GUI` 的方式合成，~而且他的代码看起来有一股 C++ 的味~，所以说我就重写了一个基于 `pydub` 和 `FastAPI` 的服务端。而且本项目为 `fully-typed` 所以可读性来说，我认为还是不错的。

你可以把它集成到其它的 `App` 中，并且**没有什么语言的限制**，理论上你可以在任何支持 `HTTP` 交互的语言中使用。

## 部署

推荐 `Python 3.10`，我并不打算进行向下兼容，尽管理论上最低支持 `Python 3.9`，但你还是最好**创建虚拟环境**并且使用 `Python 3.10` 来避免版本问题。

1. 安装依赖。

   ```bash
   pip install -r requirements.txt
   ```

2. 修改 `config.json` 中的 `port` 可以更改端口，默认为 `8002`。其它的配置项可参考代码中的注释。

3. 启动服务端。你有两种方式可以选择：

   + 使用 `uvicorn`，参考 [uvicorn 文档](http://www.uvicorn.org/deployment/)来部署。

   + 直接运行 `otto.py`，使用默认运行配置。

     ```bash
     python otto.py
     ```

4. 你可以使用 `pm2` 等工具来使其在后台运行，本项目就不再多介绍。

## 使用

你可以直接访问 `GET /otto?text=文本` 来获得语音，也可以 `GET /otto/figure?text=文本` 来查看指定音频的波形。

我推荐你在 `App` 中使用 `POST` 方法，因为直接 `GET` 方法可能导致一些特殊字符，比如加号，不能正确地被接收。

这里以 [nonebot2](https://github.com/nonebot/nonebot2) 的 QQ 机器人为例，来演示如何将其集成到你的机器人中。

```python
"""
支持的命令，加不加空格无所谓:
- otto text
- otto fig text
"""

import aiohttp

from nonebot import on_command
from nonebot.adapters import Message
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11.message import MessageSegment

from urllib.parse import urljoin


otto = on_command('otto')
baseurl = 'http://localhost:8002'


async def get_bytes(path: str, text: str) -> bytes:
    async with aiohttp.ClientSession() as session:
        async with session.post(urljoin(baseurl, path), json={'text': text}) as resp:
            return await resp.read()


@otto.handle()
async def handle_otto(args: Message = CommandArg()):
    text = args.extract_plain_text()
    if text.startswith('fig'):
        image = await get_bytes('/otto/figure', text.removeprefix('fig').strip())
        await otto.finish(MessageSegment.image(image))
        return

    record = await get_bytes('/otto', text)
    await otto.finish(MessageSegment.record(record))

```

这样就能在 QQ 中生成电棍语音了。

如果你不会用 `nonebot2`，请参考他们的官方文档，本项目与其无关。因为这个插件东西实在是太小了，几行就写完了，所以我就不再单独发插件。


## 拓展

下方配置属于高级自定义配置，可以什么都不动，来保证能运行基本功能。

### 特殊字符

例如，为了支持它读 `+` 加号，需要增加以下内容：

```json
{
  "special": {
    "\\+": "jia.wav"
  }
}
```

这是由于 `special` 下的键都以正则表达式的形式匹配，所以你要记得用反斜杠来转义。


### 英语单词

对于普通的英语单词就没那么多要求了，直接在 `special` 下写就可，例如：

```json
{
  "special": {
    "apple": [
      "a.wav",
      "pu.wav",
      "lu.wav"
    ]
  }
}
```

这个值可以是一个字符串或者一个数组，按顺序写入 `assets` 目录下的音频文件名即可。


### 随机音效

你可以将数组第一个元素设置为 `RANDOM` 来使得这个数组是以随机抽取的模式进行加载音频的，例如对于鬼叫的定义如下：

```json
{
  "special": {
    "鬼叫|硅胶|啊啊啊": [
      "RANDOM",
      "鬼叫1.wav",
      "鬼叫2.wav",
      "鬼叫3.wav",
      "鬼叫4.wav",
      "鬼叫5.wav",
      "鬼叫6.wav"
    ]
  }
}
```

同理，我们可以用正则表达式来定义。这会使得三个以上重复的 `啊` 也会使用鬼叫的音频，而单个的 `啊` 则不会，这是因为在这里我们按照正则表达式的长度来确定其优先级。

## 协议

本项目使用 `MIT` 协议。注意，本协议不包括 `assets` 目录下的音频。


关注[电棍](https://space.bilibili.com/628845081)谢谢喵。
