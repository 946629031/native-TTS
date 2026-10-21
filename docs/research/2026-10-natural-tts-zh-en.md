# 2026-10 调研：如何生成「中英夹带也不生硬」的自然语音

> 调研时间：2026-10-21 ｜ 目标设备：Apple M2 / 24 GB / macOS 14.4
> 结论会随模型迭代变化，本文所有数字均标注来源，未标注的为工程经验。

---

## 0. TL;DR

1. **"不自然"的元凶，八成不是声学模型，而是三件事**：
   - 按语言把句子切成两段，分别合成再拼起来 → 音色、语速、底噪、韵律全部断裂；
   - 文本没做规范化（数字、单位、缩写、全半角、奇怪符号）；
   - 用了「中文播音腔」音色去读口语化文案。
2. **正确姿势：整句丢给一个多语种端到端模型，一次生成。** 2026 年的模型（Qwen3-TTS、VoxCPM2、CosyVoice3、Fish S2）都是多语种联合训练，天然支持句内切换。
3. **想要"同一个人自然地中英切换"，最有效的一招是：用一段中英混合的参考音频做 zero-shot 克隆**（10–30 秒，里面既有中文也有英文）。模型会把这个人的两套口音一起学走，而不是"中文音色 + 英文音色"两个人。
4. **本机（M2 24 GB）首选 Qwen3-TTS 0.6B（MLX 8-bit）**：中英 WER 都在第一梯队、1 GB 级权重、支持流式、Apache 系许可（以仓库 LICENSE 为准）。
5. **云端（国内可直连）**：MiniMax Speech 2.6 / 火山引擎豆包 / 阿里云百炼 Qwen3-TTS。**ElevenLabs 的中文准确率是硬伤**（公开测试集中文 WER 16.0%，见 §2），表现力强但不适合中文为主的内容。
6. **验收方式**：固定 30 条混读测试集（见 `eval/cases-zh-en.md`），ASR 回译算错字率 + 盲听打分，别凭"感觉还行"。

---

## 1. 把"自然"拆成可优化的 5 层

| 层 | 出问题时的表现 | 主要手段 |
| --- | --- | --- |
| 文本规范化 | 数字读错、"3.5%" 读成"三点五百分号"、英文缩写逐字母念 | TN 规则 / 大模型预处理 |
| 语言与发音 | 多音字错、英文词被按拼音读、重音位置怪 | 拼音/IPA 覆盖、自定义词典 |
| 韵律与语气 | 每个字一样重、句尾上扬、像播报 | 参考音频、自然语言指令、口语化标点 |
| 音色与切换 | 中英像两个人、切换处音色跳变 | 整句合成 + 双语参考音色 |
| 拼接与后处理 | 段与段之间呼吸声断裂、响度忽大忽小 | 语义分段、交叉淡化、响度归一 |

**核心原则：能一次生成，就不要切开拼。**

---

## 2. 候选方案矩阵（2026-10）

### 2.1 开源 / 可本地部署

| 模型 | 参数 | 语言 | 中英混读 | 克隆 | 许可 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| **Qwen3-TTS 0.6B / 1.7B** | 0.6B / 1.7B | 中英日韩德法俄葡西意 | 强（联合训练） | 3 秒 zero-shot | 开源（以仓库 LICENSE 为准） | 12Hz tokenizer，流式首包 ~97ms；MLX 已有 8bit 权重 |
| **VoxCPM2** | 2B | 30 语种 + 9 种中文方言 | 强 | 是（含"极致克隆"续写模式） | **Apache-2.0** | 原生 **48 kHz**；音色设计；4090 RTF≈0.30，M4 Pro Metal RTF≈1.76（Q8_0） |
| **IndexTTS 2.5** | ~1.5B | 中英日西阿 | 强 | 是 | 开源（商用需确认） | 强项是**情绪 + 时长控制**，适合配音/对口型；Mac 可跑 MPS 但慢 |
| **CosyVoice 3 (0.5B)** | 0.5B | 中英日韩 + 方言 | 强 | 3 秒 | 开源（商用需确认） | 细粒度控制最全：`[breath]`、拼音纠正 `[j][ǐ]`、 instruct 方言 |
| **Fish Audio S2 / S2-Pro** | 4B | 83 语种 | 很强（中文 WER 0.73，公开测试集第一） | 10–30 秒 | 开源权重（商用看条款） | 盲测排名高；API $15/M UTF-8 bytes；4B 在 24 GB Mac 上偏重 |

### 2.2 商业 API

| 服务 | 代表模型 | 中文 | 句内切语言 | 价格量级 | 本机可直连 |
| --- | --- | --- | --- | --- | --- |
| 阿里云百炼 | Qwen3-TTS-Flash / Instruct | 很强 | 支持（`language=Auto`） | 低 | ✅ |
| MiniMax | Speech 2.6 HD | 很强（中文 WER 2.25） | 支持 | ~$100/M 字符 | ✅ |
| 火山引擎 | 豆包语音合成 | 很强（中文母语腔） | 支持 | 低–中 | ✅ |
| 腾讯云 | 语音合成 TTS | 强 | 支持（SSML） | 低 | ✅ |
| Inworld | Realtime TTS 1.5 Max | 中上 | **明确宣传 mid-utterance switching** | 中 | ✅ |
| ElevenLabs | v3 / v4 | **弱**（中文 WER 16.0） | 支持但中文发音差 | $50–135/M 字符 | API 可达 |
| Fish Audio | S2.1 Pro | 很强 | 支持 | 有免费档（Fair Use） | ❌ 站点被墙 |

### 2.3 关键数字（公开测试集，越低越好）

**Minimax-MLS 多语种测试集 — 中文 WER / 英文 WER**（来源：VoxCPM2 官方 README 引用表）

| 模型 | 中文 WER | 英文 WER |
| --- | --- | --- |
| Fish Audio S2 | **0.730** | 1.620 |
| Qwen3-TTS | 0.928 | **0.934** |
| VoxCPM2 | 1.136 | 2.289 |
| MiniMax | 2.252 | 2.164 |
| ElevenLabs | **16.026** | 2.339 |

**Seed-TTS-eval（零样本克隆）**

| 模型 | test-zh CER | test-en WER | SIM(zh) |
| --- | --- | --- | --- |
| Qwen3-TTS 1.7B | 1.22 | 1.23 | 77.0 |
| VoxCPM2 | **0.97** | 1.84 | **79.5** |
| IndexTTS2 | 1.03 | 2.23 | 76.5 |
| CosyVoice3 1.5B | 1.12 | 2.22 | 78.1 |

**Artificial Analysis Speech Arena（2026 年，主观偏好 ELO）**：Inworld Realtime TTS 1.5 Max ≈ 1208、MiniMax Speech 2.6 HD ≈ 1156、ElevenLabs / Fish 紧随其后。ELO 衡量的是"像不像真人"，**不衡量中文读对没读对**——两者要分开看。

> 结论：**中文准确率** 看 WER/CER；**自然度/表现力** 看 ELO 和盲听。ElevenLabs 是典型"听起来很神、中文一读就露馅"。

---

## 3. 让中英夹带不生硬的 9 个手段（按性价比排序）

### ① 整句合成，绝不按语言切段
```
❌ 合成("这个 API 的延迟") + 合成("大概 200 毫秒") + 拼起来
✅ 合成("这个 API 的延迟大概两百毫秒。")
```
切段会带来：音色漂移、语速不一致、段首段尾多余停顿、底噪拼接痕迹。2026 年的多语种模型完全有能力一次处理整句。

### ② 双语参考音频做克隆（最有效的一招）
准备 10–30 秒参考音频，要求：
- 同一说话人，**中文和英文都出现**（例如 "我用 Python 写了个 script，跑起来还挺顺的"）；
- 16 kHz 以上、无背景音乐、无混响、语速自然；
- 文本转写要和音频**逐字对应**（多数模型的 clone 质量强依赖 `ref_text` 准确）。

这样模型学到的是"这个人的中文腔 + 这个人的英文腔"，切换时才不会像换人。

> 如果参考音频只有中文，英文部分通常会带明显的中式口音——这不一定是 bug，但要在整段里保持一致，别一会儿美音一会儿中式。

### ③ 用自然语言指令控制语气
支持 instruct 的模型（Qwen3-TTS、VoxCPM2、CosyVoice3、MiniMax）直接写：
```
"像跟同事聊天一样，语速稍快，英文单词用自然的美式发音，不要播音腔。"
```
比调 speed/pitch 有效得多。

### ④ 文本规范化（TN）——最容易被忽略
上线前必须处理：

| 类型 | 原始 | 期望读法 |
| --- | --- | --- |
| 数字+单位 | `2.3GB` / `200ms` | "二点三 G B" / "两百毫秒" |
| 百分比 | `3.5%` | "百分之三点五" |
| 缩写 | `API` `GPU` `SQL` | 逐字母 / "sequel"（要统一） |
| 品牌 | `GitHub` `Notion` `MacBook` | 英文原音，不要按拼音 |
| 全半角 | `ＡＩ`、`，` vs `,` | 统一半角英文标点 / 中文标点 |
| 奇怪符号 | `~` `·` `｜` emoji | 删除或替换为停顿 |
| 中英边界 | `用Python写` | 建议加空格：`用 Python 写`（对 tokenizer 更友好） |

### ⑤ 发音覆盖（有就一定要用）
- **CosyVoice3**：拼音级纠正 `报道[j][ǐ]予好评`、`[breath]` 控制换气；
- **ElevenLabs**：IPA `/.../`、`<lexeme><grapheme>SQL</grapheme><alias>sequel</alias></lexeme>`；
- **Azure / 腾讯云**：SSML `<phoneme>`、自定义词典；
- **Qwen3-TTS / VoxCPM2**：暂无统一音素标记，靠参考音频 + 文本改写（把 `SQL` 写成 `sequel`）。

### ⑥ 标点即韵律，别滥用逗号
- 一个逗号 ≈ 一次短停顿；中文文案里逗号过多会读成"机器断句"；
- 想连贯就别断，想强调才用破折号/句号；
- 中英之间**不要**加中文逗号（`API，的延迟` 会多出停顿）。

### ⑦ 长文本按"语义 + 呼吸"分段，而不是按字数
每段 1–3 句、20–60 字；段间保留上下文（VoxCPM2 的 continuation、CosyVoice 的 prompt 续写）。
拼接处：10–30 ms 交叉淡化 + 统一响度，能消掉 90% 的"拼接感"。

### ⑧ 固定 seed，多生成几次挑最好的
生成模型有随机性，官方也建议 1–3 次取优（VoxCPM2 README 明确写了）。批处理时把 seed 记进文件名，方便复现与 A/B。

### ⑨ 后处理统一标准
- 响度：播客 −16 LUFS，短视频 −14 LUFS（单声道/立体声统一）；
- 采样率：按下游统一（48 kHz 生成 → 44.1 kHz 交付需用高质量重采样）；
- 去首尾静音、去爆音、轻降噪（别过度，会出"水下感"）。

---

## 4. 本机可行性（M2 / 24 GB）

| 方案 | 权重占用 | 预期速度 | 判断 |
| --- | --- | --- | --- |
| Qwen3-TTS 0.6B 8-bit（MLX） | ~1 GB | 快，可流式 | ✅ **首选** |
| Qwen3-TTS 1.7B 8-bit（MLX） | ~2.5 GB | 中等 | ✅ 质量更好时用 |
| VoxCPM2 4/8-bit（MLX） | ~2–4 GB | M4 Pro 上 RTF≈1.76，M2 更慢 | ⚠️ 可用但慢，适合离线出片 |
| IndexTTS 2.5（MPS） | ~4 GB | 慢 | ⚠️ 只在需要情绪/时长控制时 |
| Fish S2 4B | ~8 GB+ | 很慢 | ❌ 本机不现实，走 API |

**安装前置**（本机目前缺 `uv`、`ffmpeg`）：
```bash
brew install uv ffmpeg
# 模型走 ModelScope（HF 本机不可直连）
pip install -U modelscope -i https://mirrors.aliyun.com/pypi/simple/
```

**Qwen3-TTS 最简跑通（MLX）**：
```bash
uv tool install --force mlx-audio --prerelease=allow
mlx_audio.tts.generate \
  --model mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit \
  --text "这个 API 的 latency 大概两百毫秒，完全可以接受。" \
  --voice Vivian --lang_code Auto --play
```

**VoxCPM2（MPS）**：
```python
from voxcpm import VoxCPM
import soundfile as sf
m = VoxCPM.from_pretrained("openbmb/VoxCPM2", load_denoiser=False)  # 建议用 ModelScope 先下到本地
wav = m.generate(
    text="(像同事聊天，语速稍快，英文用自然美式发音)我把这个 feature 的 deadline 挪到下周三了。",
    reference_wav_path="ref_bilingual.wav",
    cfg_value=2.0, inference_timesteps=10, seed=42,
)
sf.write("out.wav", wav, m.tts_model.sample_rate)
```

> 注：`mlx-community/*` 权重在 HF 上，本机需先通过 ModelScope / 镜像获取；若拿不到，可先用 DashScope 的 Qwen3-TTS API 验证听感，再解决本地权重。

---

## 5. 推荐路线

**阶段 1（1–2 天）：先验证听感，别急着搭工程**
- 用 `eval/cases-zh-en.md` 的 30 条文本，在 **Qwen3-TTS-Flash（百炼）/ MiniMax / 豆包** 各跑一遍；
- 同一段双语参考音频做克隆，对比"有克隆 vs 无克隆"；
- 盲听打分，选出 1 个主模型 + 1 个备选。

**阶段 2（3–5 天）：本地跑通 + 建立回归**
- MLX 跑 Qwen3-TTS 0.6B，测 RTF 与内存；
- 把 TN 规则、标点策略、分段策略写成脚本；
- 固化评测：ASR 回译 CER/WER + 边界听感分。

**阶段 3：封装**
- 形态待定（CLI / 菜单栏 / 本地 HTTP 服务）；
- 架构建议：**本地优先 + 云端兜底**（网络/质量不达标时切 API），接口层统一成 `synthesize(text, voice, style) -> wav`。

**成本粗算**（云端）：按 1 万字/天、MiniMax ~$100/M 字符 ≈ **$1/天**；Qwen3-TTS-Flash / 豆包更便宜。本地边际成本≈电费，但 M2 出片速度是瓶颈。

---

## 6. 评测协议（建议固化）

| 维度 | 方法 | 及格线 |
| --- | --- | --- |
| 读对没 | ASR 回译（Whisper / Qwen3-ASR）算 CER/WER | 中文 CER < 2%，英文 WER < 3% |
| 切换自然 | 中英边界处 1–5 分盲听（是否多停顿/变调/换人） | ≥ 4.0 |
| 整体自然 | MOS 1–5，至少 5 人盲听 | ≥ 4.0 |
| 音色一致 | 与参考音频的说话人相似度（可选 speaker embedding） | 主观"像同一个人" |
| 工程 | RTF、首包延迟、峰值内存 | 本地 RTF < 1 可接受 |

**注意**：WER 低 ≠ 自然。反过来，ELO 高 ≠ 中文读对。两个指标必须一起看。

---

## 7. 风险与待确认

- **许可**：CosyVoice3 / IndexTTS 的权重许可与商用条款需逐个确认；VoxCPM2 明确 Apache-2.0。
- **声音克隆合规**：参考音频必须是本人授权；生成内容建议显式标注 AI 合成。
- **网络**：本机无法直连 HF / OpenAI / fish.audio，选型时要考虑权重与 API 的可获得性。
- **方言**：如需粤语/四川话，CosyVoice3 与 VoxCPM2 覆盖更好；Qwen3-TTS 有方言音色（北京/四川）。
- **数字未实测**：表中 RTF/ELO/WER 均来自公开资料，**本机 M2 的实际 RTF 必须自测**。

---

## 8. 参考链接

- Qwen3-TTS：https://github.com/QwenLM/Qwen3-TTS ｜ 技术报告 arXiv:2601.15621
- VoxCPM2：https://github.com/OpenBMB/VoxCPM ｜ arXiv:2606.06928
- IndexTTS 2.5：https://github.com/index-tts/index-tts ｜ arXiv:2601.03888
- CosyVoice 3：https://github.com/FunAudioLLM/CosyVoice ｜ arXiv:2505.17589
- Fish Audio S2：https://arxiv.org/abs/2603.08823
- MLX-Audio：https://github.com/Blaizzy/mlx-audio
- Artificial Analysis Speech Arena（ELO 榜）
- ElevenLabs 发音控制（IPA / lexeme）：https://elevenlabs.io/docs/zh/overview/capabilities/text-to-speech/best-practices
- Azure SSML 发音：https://learn.microsoft.com/zh-cn/azure/ai-services/speech-service/speech-synthesis-markup-pronunciation
