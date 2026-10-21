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

## 本地跑通（已验证）

模型：`Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit`（MLX，1.29 GB）+ 自带 `speech_tokenizer`。

```bash
# 首次准备（已完成）
python3 -m venv .venv
.venv/bin/python -m pip install -U mlx-audio -i https://mirrors.aliyun.com/pypi/simple/
.venv/bin/python scripts/fetch_modelscope.py \
  mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit \
  models/Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit

# 合成本地音频
.venv/bin/python scripts/say.py --norm \
  "这个 API 的 latency 大概两百毫秒，完全可以接受。" \
  --out outputs/smoke.wav
afplay outputs/smoke.wav
```

实测（M2 / 24 GB）：

| 项 | 结果 |
| --- | --- |
| 输出 | 4.88 s @ 24 kHz，峰值 0.66、RMS 0.11（非静音） |
| 首次加载 | 约 30–60 s（含权重加载与编译） |
| 显存/内存 | 模型常驻约 2 GB 级 |
| RTF | 待批量测（`scripts/run_eval.py` 待补） |

> `models/` 已在 `.gitignore` 中，权重不进仓库。

## 网页版（已可用）

```bash
./start.command          # 双击也可以；自动打开 http://127.0.0.1:8765
# 或手动：
.venv/bin/python app/server.py
```

功能：音色下拉（带描述）、语言 auto/中/英、风格预设 + 自定义指令、文本规范化开关、生成/试听/下载、最近 8 条历史（可重播）。

接口（方便以后接菜单栏或别的程序）：

```
GET  /api/health
GET  /api/voices
GET  /api/history
POST /api/tts   {text, voice, lang, instruct, normalize}
```

实测（M2）：4.3 秒音频耗时约 3.1 秒；11.6 秒音频耗时约 8.2 秒（RTF ≈ 0.7，含文本处理）。

## 下一步

1. 用 `eval/cases-zh-en.md` 跑完整 30 条，测 RTF 与中英边界听感。
2. 按听感决定：内置音色够用 / 需要双语参考音频克隆。
3. 根据听感确定架构（纯本地 / 纯云 / 本地兜底 + 云端高质量）。

## 环境备注（本机网络实测）

- 可访问：ModelScope、阿里云 DashScope、火山引擎、MiniMax、腾讯云、ElevenLabs API、Inworld。
- 不可直连：huggingface.co、pypi.org、github.com、OpenAI、fish.audio。
- 因此：模型走 **ModelScope** 下载，Python 包走 **阿里云 PyPI 镜像**；HF 权重需镜像或手动搬运。
