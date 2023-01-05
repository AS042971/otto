# 电棍活字印刷

音源来自：https://github.com/DSP-8192/HuoZiYinShua

因为原项目作者只支持以本地 `GUI` 的方式合成，~而且他的代码看起来有一股 C++ 的味~，所以说我就重写了一个基于 `pydub` 和 `FastAPI` 的服务端，源码阅读起来我自认为还是没什么压力的。

你可以把它集成到其它的 `App` 中，并且**没有什么语言的限制**，理论上你可以在任何支持 `HTTP` 交互的语言中使用。

## 部署

1. 安装依赖。

   ```bash
   pip install -r requirements.txt
   ```

2. 修改`config.json` 中的 `port` 可以更改端口，默认为 `8002`。其它的配置项可参考代码中的注释。

3. 启动服务端。你有两种方式可以选择：

   + 使用 `uvicorn`，参考 [uvicorn 文档](http://www.uvicorn.org/deployment/)来部署。

   + 直接运行 `otto.py`，使用默认运行配置。

     ```bash
     python otto.py
     ```

4. 你可以使用 `pm2` 等工具来使其在后台运行，本项目就不再多介绍。

## 使用

你可以直接访问 `http://localhost:8002/otto?text=实例文本` 来获得语音，或者集中到其它的 `App` 中使用。


这里以 [nonebot2](https://github.com/nonebot/nonebot2) 的 QQ 机器人为例，来演示如何将其集成到你的机器人中。

```python
import aiohttp
from nonebot import on_command
from nonebot.adapters import Message
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11.message import MessageSegment

otto = on_command('otto')


@otto.handle()
async def handle_otto(args: Message = CommandArg()):
    text = args.extract_plain_text()
    async with aiohttp.ClientSession() as session:
        async with session.get(f'http://localhost:8002/otto?text={text}') as resp:
            content = await resp.read()
    await otto.finish(MessageSegment.record(content))
```

这样就能在 QQ 中生成电棍语音了。

如果你不会用 `nonebot2`，请参考他们的官方文档，本项目与其无关。因为这个插件东西实在是太小了，几行就写完了，所以我就不再单独发插件。


## 协议

本项目使用 `MIT` 协议。注意，本协议不包括 `assets` 目录下的音频。


关注[电棍](https://space.bilibili.com/628845081)谢谢喵。
