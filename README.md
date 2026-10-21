# native-TTS

面向「**中英文自然夹带（code-switching）**、发音不生硬」的本地 TTS。

- 模型：Qwen3-TTS 0.6B（MLX 8-bit，Apache-2.0）
- 运行：Apple Silicon 本地推理，不联网、不上传文本
- 形态：网页版 + 右键朗读 + 命令行

---

## 一、快速开始

### 1. 确认环境（只需一次）

```bash
cd /Users/Admin/Documents/code/native-TTS
ls .venv/bin/python models/Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit/model.safetensors
```

两条都存在就说明环境已就绪，直接跳到下一步。
如果换了一台机器，见文末「从零安装」。

### 2. 启动

```bash
./start.command
```

也可以双击 `start.command`。它会：

1. 启动本地服务（`127.0.0.1:8765`）
2. 自动在浏览器打开页面
3. 右上角显示「模型加载中…」，约 5–15 秒后变成「● 模型就绪」

不想用脚本就手动跑：

```bash
.venv/bin/python app/server.py
# 然后浏览器打开 http://127.0.0.1:8765
```

### 3. 停止

在启动它的终端里按 `Ctrl+C`。或者：

```bash
kill $(lsof -ti tcp:8765)
```

> 服务只监听本机 `127.0.0.1`，同一局域网的其他设备访问不到。

> 想选中文字直接右键朗读？装一次即可，见 [第五节](#五右键朗读选中即读)。

---

## 二、网页版怎么用

页面从上到下就四块：

```
① 音色 / 语言 / 风格  →  ② 输入文本  →  ③ 生成  →  ④ 试听 & 历史
```

### ① 选音色和风格

| 控件 | 说明 |
| --- | --- |
| 音色 | 9 个内置音色，下拉里带中文描述（见下方音色表） |
| 语言 | 默认「自动」；中英混读**不要**手动指定，否则另一种语言会带怪口音 |
| 文本规范化 | 默认开：清理全半角、emoji、中英之间补空格 |
| 风格 | 默认 / 自然聊天 / 温柔 / 播报 / 激动，点一下即生效 |
| 自定义风格 | 右侧输入框，例如「英文用自然的美式发音」 |

### ② 输入文本

- 直接输入，中英混排没问题；点「填入示例」可以看一个现成例子
- 下方会实时显示字数和预估时长
- 单次上限 **2000 字**；长文建议按段落分批生成

### ③ 生成

点击「生成」按钮，或按 **`⌘ + Enter`**。

生成期间按钮变灰、出现进度条。M2 上大约是 **0.7 倍实时**（10 秒音频约 7 秒生成）。

### ④ 试听与下载

生成完会自动播放，同时出现播放器：

| 操作 | 说明 |
| --- | --- |
| 下载 wav | 保存到浏览器下载目录 |
| 复制文件路径 | 复制音频在本机的绝对路径 |
| 用当前设置重生成 | 换 seed 再抽一版，不用重新输入 |

历史区保留最近 **8 条**（磁盘上最多 50 条），点左侧 ▶ 可以重播。

所有音频都在 `outputs/web/` 下，文件名格式 `{id}-{音色}.wav`。

---

## 三、音色表

| 音色 | 特点 | 母语/口音 | 适合 |
| --- | --- | --- | --- |
| `Serena` | 年轻女声，温暖柔和 | 中文 | **中英混读默认**，最稳 |
| `Vivian` | 年轻女声，明亮、略带锋利感 | 中文 | 有活力的口播 |
| `Uncle_Fu` | 成熟男声，低沉醇厚 | 中文 | 叙述、纪录片 |
| `Dylan` | 年轻男声，清亮自然 | 中文（北京） | 京味儿闲聊 |
| `Eric` | 男声，活泼、略带沙哑 | 中文（四川） | 方言感内容 |
| `Ryan` | 男声，节奏感强、有推动力 | 英文 | 英文为主的内容 |
| `Aiden` | 美式男声，阳光、中频清晰 | 英文 | 英文播客 |
| `Ono_Anna` | 日系女声，轻快俏皮 | 日文 | 日语内容 |
| `Sohee` | 韩系女声，温暖有情绪 | 韩文 | 韩语内容 |

选音色的经验：

- **中英混读为主** → `Serena` / `Vivian` / `Uncle_Fu`，英文词带轻微中文口音，整体最自然
- **英文为主** → `Ryan` / `Aiden`，英文更地道，中文会带外国口音
- **不要**用 `Ono_Anna` / `Sohee` 读中文，日韩口音会出戏

---

## 四、命令行用法

不想开网页时，可以直接出音频：

```bash
# 最常用
.venv/bin/python scripts/say.py --norm "这个 API 的 latency 大概两百毫秒。" --out outputs/a.wav
afplay outputs/a.wav

# 换音色 + 风格
.venv/bin/python scripts/say.py --voice Ryan \
  --instruct "像跟同事聊天，英文用自然的美式发音" \
  "这个 bug 我今天必须 fix 掉。" --out outputs/b.wav

# 同一句话试完全部 9 个音色（只加载一次模型）
.venv/bin/python scripts/say.py --all-voices outputs/voices "同一句话，九个音色"

# 查看音色
.venv/bin/python scripts/say.py --list-voices
```

常用参数：

| 参数 | 说明 |
| --- | --- |
| `--voice` | 音色名，默认 `Vivian` |
| `--lang` | `auto`（推荐）/ `chinese` / `english` |
| `--instruct` | 自然语言风格指令 |
| `--norm` | 先做文本规范化 |
| `--out` | 输出路径，默认 `outputs/out.wav` |
| `--all-voices DIR` | 用全部音色各生成一份到目录 |
| `--seed` | 固定随机种子，便于复现 |
| `--temperature` | 采样温度，越高越有变化 |

---

## 五、右键朗读（选中即读）

选中一段文字 → 右键 → **服务（Services）** → **用 native-TTS 朗读**。

### 安装（一次）

```bash
./services/install.sh
```

然后打开 **系统设置 → 键盘 → 键盘快捷键 → 服务 → 文本**，确认「用 native-TTS 朗读」已勾选。

### 使用

1. 在任意 App 里选中文字（Safari、备忘录、VS Code、PDF…）
2. 右键 → 服务 → 用 native-TTS 朗读
3. 第一次会自动在后台启动服务、加载模型（约 10 秒），之后直接出声

再点一次会打断上一次朗读，换成新选中的内容。长文本会自动按句子分块（约 800 字一块）连续播放。

### 配一个快捷键（推荐）

系统设置 → 键盘 → 键盘快捷键 → 服务 → 文本 → 找到「用 native-TTS 朗读」→ 双击右侧 → 按 `⌥⌘S`。

之后：选中文字 → `⌥⌘S`，比右键快得多。

### 换音色 / 风格

默认用 `Serena`。新建 `~/.config/native-tts/config.json`：

```json
{"voice": "Serena", "lang": "auto", "instruct": "像跟朋友聊天，轻松自然", "normalize": true}
```

下一次朗读生效，不用重启服务。可选音色见上方音色表。

### 卸载

```bash
./services/uninstall.sh
```

日志：`/tmp/native-tts-speak.log`（朗读）、`/tmp/native-tts-server.log`（后台服务）。

---

## 六、常见问题

| 现象 | 原因 / 处理 |
| --- | --- |
| 页面打不开 | 服务没启动，或端口被占：`lsof -ti tcp:8765` 查进程 |
| 右上角一直「模型加载中」 | 首次加载需 5–15 秒；超过 1 分钟看终端报错 |
| 提示「模型加载失败」 | 检查 `models/.../model.safetensors` 和 `speech_tokenizer/` 是否完整 |
| 点生成没反应 | 文本为空，或模型未就绪（按钮是灰的） |
| 生成很慢 | 首次生成有编译开销；后续约 0.7 倍实时。长文本会线性变慢 |
| 没有声音 | 系统音量/输出设备；或浏览器拦截自动播放，点播放器 ▶ |
| 英文发音怪 | 换成 `Ryan` / `Aiden`，或在风格里写「英文用自然的美式发音」 |
| 中文像播音腔 | 换 `Serena`，风格选「自然聊天」，减少逗号 |
| 文本超限 | 单次 2000 字，分段生成 |
| 右键菜单里没有「用 native-TTS 朗读」 | 到「系统设置 → 键盘 → 键盘快捷键 → 服务 → 文本」勾选；仍没有就重跑 `./services/install.sh` 并重启一次 |
| 右键朗读第一次很慢 | 后台服务没启动，正在加载模型；加载完会常驻，后续直接出声 |
| 右键朗读失败 | 看日志：`tail -20 /tmp/native-tts-speak.log` |

---

## 七、项目结构

```
native-TTS/
├── start.command              # 双击启动网页版
├── app/
│   ├── server.py              # 本地服务（模型常驻 + HTTP API）
│   └── static/                # 单页 UI（HTML/CSS/JS）
├── services/
│   ├── install.sh             # 安装右键服务（写入 ~/Library/Services）
│   ├── uninstall.sh           # 卸载右键服务
│   └── template/              # Automator .workflow 模板
├── scripts/
│   ├── say.py                 # 命令行合成
│   ├── speak_stdin.py         # 右键朗读：stdin → 合成 → afplay
│   ├── normalize_text.py      # 文本规范化
│   └── fetch_modelscope.py    # 模型下载（多连接 + 断点续传）
├── models/                    # 模型权重（.gitignore，不入库）
├── outputs/                   # 生成的音频（.gitignore）
├── eval/cases-zh-en.md        # 中英混读评测集
└── docs/research/             # 调研笔记
```

HTTP 接口（右键服务和别的程序都用它）：

```
GET  /api/health              -> {status, error}
GET  /api/voices              -> [{name, desc, native}]
GET  /api/history             -> 最近 50 条
GET  /audio/<file>.wav        -> 音频
POST /api/tts                 -> {id, url, path, duration, ...}
     body: {text, voice, lang, instruct, normalize}
```

---

## 八、从零安装（换机器时）

前置：macOS + Apple Silicon，已装 Homebrew / Python 3.10+。

```bash
cd native-TTS

# 1) Python 环境（本机网络下 PyPI 需走阿里云镜像）
python3 -m venv .venv
.venv/bin/python -m pip install -U mlx-audio -i https://mirrors.aliyun.com/pypi/simple/

# 2) 模型（走 ModelScope，多连接下载）
.venv/bin/python scripts/fetch_modelscope.py \
  mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit \
  models/Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit

# 3) 冒烟测试
.venv/bin/python scripts/say.py --norm "测试一下，hello world。" --out outputs/smoke.wav
afplay outputs/smoke.wav
```

模型合计约 **1.9 GB**（主模型 1.29 GB + 声码器 0.68 GB）。

---

## 九、调研结论速览

- **自然度的瓶颈通常不在声学模型，而在「文本前端 + 整句合成 + 参考音色」**：不要按语言切段再拼接。
- 本机首选 **Qwen3-TTS 0.6B（MLX 8-bit）**：中英 WER 第一梯队、1 GB 级权重、支持流式。
- 云端可直连备选：MiniMax Speech 2.6 / 火山引擎豆包 / 阿里云百炼 Qwen3-TTS。
- ElevenLabs 表现力强，但公开测试集中文 WER 约 16%，中文为主的内容不建议。
- 想要「同一个人自然地中英切换」，最有效的一招是：**用一段中英混合的参考音频做 zero-shot 克隆**。

详细对比、数据来源与评测方法：

| 文档 | 说明 |
| --- | --- |
| [`docs/research/2026-10-natural-tts-zh-en.md`](docs/research/2026-10-natural-tts-zh-en.md) | 模型对比、自然度关键手段、本机可行性 |
| [`eval/cases-zh-en.md`](eval/cases-zh-en.md) | 中英混读评测集（30 条，含考点与预期读音） |

---

## 十、环境备注（本机网络实测）

- 可访问：ModelScope、阿里云 DashScope、火山引擎、MiniMax、腾讯云、ElevenLabs API、Inworld
- 不可直连：huggingface.co、pypi.org、github.com、OpenAI、fish.audio
- 因此：模型走 **ModelScope**，Python 包走 **阿里云 PyPI 镜像**
