# native-TTS

面向「**中英文自然夹带（code-switching）**、发音不生硬」的 TTS 选型与实现。

当前阶段：**调研 + 选型**（尚未确定最终架构）。

## 目录

| 路径 | 说明 |
| --- | --- |
| [`docs/research/2026-10-natural-tts-zh-en.md`](docs/research/2026-10-natural-tts-zh-en.md) | 2026-10 联网调研：模型对比、自然度关键手段、本机可行性 |
| [`eval/cases-zh-en.md`](eval/cases-zh-en.md) | 中英混读评测集（30 条，含考点与预期读音） |

## 结论速览

- **自然度的瓶颈通常不在声学模型，而在「文本前端 + 整句合成 + 参考音色」**：不要按语言切段再拼接。
- 本地（Apple M2 / 24 GB）：**Qwen3-TTS 0.6B（MLX 8-bit）** 是当前最现实的首选，中英稳定、体积小、支持流式。
- 云端（国内可直连）：**MiniMax Speech 2.6 / 火山引擎豆包 TTS / 阿里云百炼 Qwen3-TTS**；ElevenLabs 表现力强但中文准确率明显偏弱。
- 想要「同一个人自然地中英切换」，最有效的一招是：**用一段中英混合的参考音频做 zero-shot 音色克隆**，而不是给两种语言各配一个音色。

## 下一步

1. 用 `eval/cases-zh-en.md` 在 2–3 个候选上各跑一轮盲听（先 API，后本地）。
2. 打通本地 Qwen3-TTS 0.6B（MLX）推理脚本。
3. 根据听感确定架构（纯本地 / 纯云 / 本地兜底 + 云端高质量）。

## 环境备注（本机网络实测）

- 可访问：ModelScope、阿里云 DashScope、火山引擎、MiniMax、腾讯云、ElevenLabs API、Inworld。
- 不可直连：huggingface.co、pypi.org、github.com、OpenAI、fish.audio。
- 因此：模型走 **ModelScope** 下载，Python 包走 **阿里云 PyPI 镜像**；HF 权重需镜像或手动搬运。
