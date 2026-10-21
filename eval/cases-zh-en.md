# 中英混读评测集（30 条）

用法：
1. 同一说话人、同一语气设定，对每个候选模型生成 1–3 次（固定 seed，取最优）；
2. 先做 ASR 回译（Whisper / Qwen3-ASR）算 CER/WER；
3. 再盲听打分：**边界自然度 / 整体自然度 / 音色一致性**，各 1–5 分；
4. 记录到 `results/<model>/<date>.md`。

评分表：

| 指标 | 说明 |
| --- | --- |
| CER/WER | ASR 回译 vs 原文（英文按词、中文按字） |
| 边界 | 中英切换处是否多停顿、变调、换人（5 = 完全听不出接缝） |
| 自然 | 整体像不像真人在说话（5 = 听不出是 AI） |
| 音色 | 与参考音频是否同一人（5 = 完全一致） |

---

## A. 缩写与术语（读音策略必须统一）

| # | 文本 | 考点 | 期望 |
| --- | --- | --- | --- |
| A1 | 这个 API 的 latency 大概两百毫秒，完全可以接受。 | `API` 逐字母 vs "阿皮爱" | A-P-I，英文词连读 |
| A2 | 我们把 GPU 跑满了，batch size 调到 32 才勉强稳住。 | `GPU`、`batch size` | G-P-U；batch size 连读 |
| A3 | 这条 SQL 走了全表扫描，加个 index 应该就好了。 | `SQL` 读法 | 统一 "sequel" 或 S-Q-L，全篇一致 |
| A4 | 你用 Postman 测一下这个 endpoint，记得带上 token。 | 工具名 + 技术词 | Postman 原音，endpoint 不要拆 |
| A5 | 这个 PR 我 review 过了，就一个 nit，改完直接 merge。 | 职场黑话密度 | PR / review / nit / merge 全部英文原音 |

## B. 品牌与产品名

| # | 文本 | 考点 | 期望 |
| --- | --- | --- | --- |
| B1 | 我用 MacBook Pro 跑 Stable Diffusion，风扇直接起飞。 | 品牌连读 | MacBook / Stable Diffusion 不逐词硬拆 |
| B2 | 把这份 deck 发到我的 Notion，顺便 cc 一下老板。 | `cc`、`deck` | "see-see"，deck 原音 |
| B3 | 昨晚在 GitHub 上翻到一个超好用的 repo，star 已经 3 万了。 | `GitHub`、`repo` | GitHub 原音；repo 读 "ri-po" |
| B4 | 这个在 Figma 里调一下就行，不用再开 Photoshop 了。 | 两个产品名 | 都不按拼音读 |

## C. 数字、单位与符号

| # | 文本 | 考点 | 期望 |
| --- | --- | --- | --- |
| C1 | 模型大小 2.3 GB，量化到 4-bit 之后只要 700 MB。 | 小数 + 单位 | "二点三 G B"；4-bit 读 "four bit" |
| C2 | 转化率从 3.5% 涨到 12%，主要靠 landing page 改版。 | 百分比 + 英文短语 | "百分之三点五"；landing page 连读 |
| C3 | 预算大概 1.2 万美金，deadline 是 11 月 15 号。 | 金额 + 日期混排 | 数字用中文读，日期不要读成 "eleven fifteen" |
| C4 | 延迟从 800ms 降到 120ms，QPS 翻了三倍。 | 单位缩写 + QPS | "毫秒" 或 "m s" 统一；Q-P-S |

## D. 代码与技术名词

| # | 文本 | 考点 | 期望 |
| --- | --- | --- | --- |
| D1 | 这个 bug 是因为 useEffect 的依赖数组少写了一个 state。 | 驼峰命名 | "use effect" 自然拆分，不要拼字母 |
| D2 | 用 Docker compose up 一下，k8s 那边我已经改好了。 | 命令 + 缩写 | "docker compose up" 连读；k8s 读 "k-eight-s" |
| D3 | 前端用 TypeScript，后端是 Go，中间走 gRPC。 | 语言名 | TypeScript 不要逐字母；gRPC 读 "g-r-p-c" |
| D4 | 记得把 .env 加进 .gitignore，别把 key 传到远端。 | 符号 + 文件名 | ".env" 读 "dot env"；key 英文原音 |

## E. 口语与语气（最容易暴露"播音腔"）

| # | 文本 | 考点 | 期望 |
| --- | --- | --- | --- |
| E1 | 啊？这个 feature 不是上周就 ship 了吗？ | 惊讶 + 反问 | 句首语气词自然，句尾上扬 |
| E2 | 说实话，这个方案我觉得吧……还差点意思。 | 犹豫、拖音 | 省略号处有真实停顿，不要机械断句 |
| E3 | 你先别急，我这边 confirm 一下就回你。 | 安抚语气 | confirm 轻读，不要重音砸下去 |
| E4 | 哈哈哈这个也太离谱了吧，完全 make sense 不了。 | 笑声 + 吐槽 | 笑声不要读成"哈哈哈"三个字 |
| E5 | OK，那就这样，回头我把 link 发群里。 | 收尾口语 | OK 短促，link 轻读 |

## F. 长句连续混读（测韵律与气息）

| # | 文本 | 考点 | 期望 |
| --- | --- | --- | --- |
| F1 | 我们这周的重点是把 onboarding flow 重新捋一遍，尤其是 first screen 的引导，现在流失率太高了。 | 长句 + 多处切换 | 全程一口气的连贯感，不在英文处断 |
| F2 | 如果用户第一次打开 app 就卡在 permission 那一步，那后面 push notification 的转化基本就废了。 | 条件句 + 术语 | 逻辑重音落在"废了" |
| F3 | 这个项目最开始只有两个人，后来拉了 design 和 QA，现在整个 team 大概十五个人，节奏反而更慢了。 | 数字 + 团队词 | 语速自然加快，不要一字一顿 |
| F4 | 我个人的建议是，先把 MVP 跑通，再去考虑 scaling 的问题，不然很容易 over-engineering。 | 建议语气 + 三个英文词 | 英文词之间不抢重音 |

## G. 边界压力测试（专挑模型的痛点）

| # | 文本 | 考点 | 期望 |
| --- | --- | --- | --- |
| G1 | 用Python写脚本真的爽，import一下就能跑。 | 中英**无空格**紧贴 | 仍能正确切分，不读成 "python写" |
| G2 | 这个 feature 叫 "smart retry"，中文我们一般说"智能重试"。 | 引号 + 中英互译 | 引号不读出来，中英各读各的 |
| G3 | 他说的那个 "basically" 其实就是"基本上"的意思，但语气完全不一样。 | 单词被中文包围 | basically 要读出原味，别带节奏拖腔 |
| G4 | 我们 A/B test 的结果是 B 组赢了，conversion 高了 8 个点。 | 字母 + 斜杠 + 缩写 | "A B test" 自然连读，斜杠不读 |

---

## 附加：基线样本

| # | 文本 | 用途 |
| --- | --- | --- |
| Z1 | 今天天气不错，我们下午去楼下那家咖啡馆坐坐吧。 | 纯中文自然度基线 |
| Z2 | Honestly, I think we should ship it and see what happens. | 纯英文自然度基线 |
| Z3 | 嗯。 | 极短句，测起音与尾音是否干净 |

> 如果 Z1 听起来就像新闻联播，先换音色/参考音频，别急着怀疑混读能力。
