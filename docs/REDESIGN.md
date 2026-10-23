# Lectern 落地页重构方案

> 状态：**方案**；第 1 步（自定义 404 + Caddy `handle_errors`）已实施，其余未动手
> 基线：v0.16.0（release.json，2026-10-21）· 2026-10-23 定稿
> 方向：**产品证据优先**——让页面先回答「是什么、长什么样、怎么拿到」，再讲能力细节。

---

## 1. 一句话结论

现在的首页是「一篇讲述产品能力的文章」，重构目标是「一次下载决策」。
保留全部设计语言（墨骨 / 反白带 / MiSans / 印章红 / 2px 锐角），只重排区块、替换证据、压缩叙述。

## 2. 现状诊断

| # | 问题 | 证据 |
|---|------|------|
| 1 | 首屏右侧是 CSS 手绘的 `workbench-scene`，不是真实产品 | [index.html:82](../index.html#L82) `.workbench-scene` |
| 2 | 第二屏在讲 5 个版本前的发布说明 | [index.html:110](../index.html#L110) `id="v11"`，eyebrow「0.11 · R0 生产链路收口」 |
| 3 | 页面节奏是文章，不是决策：hero → 版本说明 → 底座 → 流程 → 下载 | 下载区在第 4 屏，而下载是页面唯一目的 |
| 4 | 首页底座铺了 7 条 feature-row，和 features.html 重复 | [index.html:174](../index.html#L174) 起 |
| 5 | features.html 15 项功能只能顺序读，没有分组筛选 | `.docs-side` 有分组，但只存在于侧栏 |
| 6 | why.html 的差异靠长文，缺一张可扫读的对照表 | [why.html:71](../why.html#L71) `#compare` |
| 7 | 无 404 页、无 changelog；release_note 只在下载区出现一行 | `.ops/Caddyfile` 无 `handle_errors` |

## 3. 不动的部分（硬约束）

- **设计 token / 排版 / 字体 / 导航 / 页脚**。不换色板，不引入新字体，不改 `Navbar` 与 `footer` 结构。
- **发版管线**。`release.json` → `scripts/sync-version.py` → `scripts/check-release.py` 是全站版本真源，重构时必须保留它依赖的锚点结构：
  - 下载按钮文案 `下载 vX.Y.Z`
  - 下载表 `<small>… · vX.Y.Z</small>`
  - `.dl-release` 段落
  - Hero `.release-pill`
  - 页脚 `>vX.Y.Z</a>`、JSON-LD、路线页版本戳
  - 若某个锚点被删/改结构，必须同步改 `sync-version.py` 的 RULES；规则一次都没命中会返回 1，但**不会被 CI 拦截**（CI 只跑 check-release）。
- **静态架构**。不加框架、不加构建步骤、不引第三方脚本。
- **URL 兼容**。`#v11`、`#features`、`#workflow`、`#download`、`#ecosystem` 若被外部引用，替换区块时保留 id 或留零高度锚点；动手前先 grep 全仓与访问日志。
- **缓存规则**。任何 `theme.css` / `theme.js` 改动必须同步 bump `release.json.asset_rev`，否则用户拿不到新样式。

## 4. 新首页结构

| 屏 | 现状 | 重构后 | 改动 |
|----|------|--------|------|
| 1 | Hero：文案 + CSS 演示 | Hero：文案（5 栏）+ 真实截图（7 栏）+ 证据行 | 重做右半 |
| 2 | `#v11` 0.11 发布说明 | `#loop` 三卡产品闭环：派任务 / 审改动 / 验结果 | 整体替换 |
| 3 | Foundation 7 行列表 | Foundation 4 卡网格 | 压缩 |
| 4 | Workflow 三步（演示图） | 三步上手（第一步即下载） | 改文案 |
| 5 | Download 表格 | Download + 更新日志入口 + 选型提示 | 增强 |
| 6 | Ecosystem | 不动 | — |
| 7 | CTA | 不动（仅跟版本走） | — |

### 4.1 Hero

- 栅格从 `1fr 1fr` 改为 `5fr 7fr`（`minmax(0, …)` 防溢出），文案列不再和截图等宽。
- 右侧 `.workbench-scene` 换成**真实应用截图**：
  - 一行会话、右侧 diff 看板、底部时间轴必须同时可见——这是产品最强的三个证据。
  - 1px `--color-line-strong` 边框 + `--radius-sm`，**不加**假浏览器 chrome、不加阴影光晕、不加透视倾斜。
  - `width`/`height` 显式声明，`loading="eager"`、`fetchpriority="high"`、`decoding="async"`。
  - 图内不出现版本号、用户名、真实路径；演示仓库用 `lectern-demo`。
- 文案列：
  - H1 保留「桌面级 Agent 工作台。」（已被品牌确认）。
  - 描述压到两行内：一句定位 + 一句差异（本机执行 / 独立工作区 / 合并前真跑验证）。
  - 按钮保留 macOS 主按钮 + Windows 次按钮；下方 `hero-meta` 保留系统要求。
  - 新增**证据行**（`hero-meta` 下一行，mono 小字）：`源码开放 · 本机执行 · 数据不离开电脑`。
    - 不写测试数量，除非能从 CI 自动读取；手写数字必然过期。
- `.run-circuit` 从横贯整幅的装饰带压缩为 hero 底部一行 32px 的状态条；或直接删除（它现在是视觉噪音，且与工作流区块语义重复）。
- 现有 `.workbench-scene` 的播放器代码**不删**，移到 4.9 的演示区块复用。

### 4.2 第二屏：`#v11` → `#loop`

删除 0.11 版本叙事（内容迁往 features.html，见 4.6）。新区块：

- Eyebrow：`How it works`
- H2：`从一句话，<em>到可合并的改动。</em>`
- 三张卡（`.loop-grid`，桌面三列、≤900px 单列）：

| 卡 | 标题 | 正文（约 40 字） | 证据行 | 链接 |
|----|------|------------------|--------|------|
| 01 | 派任务 | 一句话交代目标，Agent 在独立工作区里读代码、改文件、跑测试；复杂任务可派只读子代理并行探索。 | `worktree · subagents` | `features.html#f-subagents` |
| 02 | 审改动 | 每处写盘与命令先过权限，Diff 实时进右侧看板；不满意可拖时间轴回卷，从任意一轮重来。 | `diff · rewind · audit` | `features.html#f-diff` |
| 03 | 验结果 | 合并前对实际合并出的代码真跑验证；失败则分支一动不动，证据绑定 commit 指纹。 | `verify merge · receipt` | `features.html#f-verify` |

- 卡片视觉：顶部 1px 线 + 编号（mono）+ 标题（serif）+ 两行正文 + 底部 mono 标签。不用图标、不用 emoji、不用玻璃拟态。
- 桌面端在卡片上方加一条极简流向线（`派任务 → 审改动 → 验结果`），纯 CSS，不加动效；reduced-motion 下静止。
- 旧的 0.11 三块内容不要丢弃：
  - 「子代理生产链路」→ features.html 已有 `#f-subagents`，补齐 4 条机制要点（现有条目偏短）。
  - 「Host 命令可靠性」→ 新增 `features.html#f-host`。
  - 「合并结果实检」→ 新增 `features.html#f-verify`。
  - 三块统一归入新的侧栏分组「生产链」，放在「交付与执行」之后。

### 4.3 Foundation 压缩为 4 卡

保留：会话回卷、断点续传、Diff 审阅、权限审计。
移除（仅留在 features.html 详情页）：增量投影、命令面板、托盘常驻。

- 新类 `.foundation-grid`：桌面 4 列、≤1000px 2 列、≤640px 1 列。
- 每卡：编号 01–04、名称、一句 25–35 字的说明、`了解更多 →` 链到对应 `#f-*`。
- 删除 `.feature-proof` 的代码示意块——它与 4.2 的「审改动」重复；保留会显得页面自我重复。

### 4.4 Workflow 改为「三步上手」

文案从「能力描述」改为「用户动作」：

1. **装好**（`download`）：选平台下载，拖进 Applications。卡片内直接放主下载按钮。
2. **交代任务**（`prompt`）：打开一个项目目录，用一句话说清目标和验收标准。
3. **审阅落地**（`review`）：看 diff、跑测试、决定是否提交；不满意就回卷。

保留 `.flow-grid` 三列与 vignette 结构，只换标题、正文和第一步的 CTA。折叠重复的权限说明（4.2 已讲）。

### 4.5 Download 增强

- `.dl-release` 保留（sync-version 锚点），但文案由长句改为：`vX.Y.Z · 2026-10-21 · 更新了什么 →`，链接到 `/changelog`。
  - 需要新增锚点规则；`release_note` 移到 changelog 页首。
- 表格每行补：产物体积（如 `~120 MB`）、架构、系统要求；体积随手写会过期，若无法自动生成则不做。
- 表格下方加一行选型提示（`.dl-note`）：`Apple Silicon 选 .dmg；Intel Mac 暂不支持；Windows 10 1809 以下请升级。`
- SHA256 链接保留；补一句 `shasum -a 256 文件名` 的校验命令（`code` 样式已有）。
- 下载区顶部与底部都不再重复版本说明。

### 4.6 features.html

- **筛选 chips**：在 `#features-docs` 顶部加一行 sticky chips（`全部 / 会话 / 执行与审阅 / 效率 / 数据与安全 / 交付与执行 / 生产链 / 对话体验`）。
  - 点击按分组显示/隐藏 `.docs-item` 与侧栏项；`aria-pressed` 标注状态；无 JS 时全部可见。
  - 与现有 `.docs-side` 分组共用一份 `data-group` 属性，避免两处维护。
- **预览位**：只给 5 项加小块视觉证据（多会话、回卷、Diff、子代理、浏览器验证），其余保持纯文本。
  - 预览用 CSS 示意或截图缩略图，统一 16:10、同一底色；不逐项配图（15 张图会拖垮页面）。
- **生产链分组**：迁入 4.2 的三块内容，`#f-host`、`#f-verify` 新增，`#f-subagents` 补全。
- 顶部导语保持版本中立（当前「十五项功能」与实际条目一致，别再写死版本号）。

### 4.7 why.html

在 `#compare` 现有内容之后加一张三列对照表：

| 维度 | Lectern | IDE 插件 | 云端 Agent |
|------|---------|----------|------------|
| 执行位置 | 本机 | 本机 | 云端 |
| 独立工作区 | 每任务隔离 | 无 | 部分 |
| 合并前验证 | 对合并结果真跑 | 无 | 无 |
| 会话回卷 | 任意一轮截断重来 | 无 | 有限 |
| 数据留存 | 全部在本机 | 本机 | 上传云端 |
| 并行子代理 | 有 | 无 | 有 |

- 只写可验证事实；不确定的格子留 `—`，不写“最强/唯一”。
- 移动端表格横向滚动，首列 sticky。
- 表下方一行注明对比时间与版本（`对比基于 v0.16.0`），走 sync-version 锚点或手动跟版本。

### 4.8 404 与 changelog

**404.html**

- 复用导航与页脚，正文：大号 `404`（serif）+ 一句「这个地址没有内容。」+ 三个入口（首页 / 功能 / 下载）。
- 服务器：`.ops/Caddyfile` 增加 `handle_errors { rewrite * /404.html; file_server }`（仅 404 分支）。
  - `.ops/Caddyfile` 不在 CI 部署清单里，需手动 scp 到服务器并 reload；改完 curl 一个不存在路径验证状态码仍是 404 但内容为自定义页。
- 新页面需同步：`deploy.yml` tar 清单 + 冒烟路径、`check-release.py` 的 `PAGES`（如需版本校验）、`sitemap.xml`（404 不收录）。

**changelog.html**

- 版本倒序，每条：版本号 / 日期 / 3–5 条改动 / GitHub Release 链接。
- 数据源：先手写静态页；每次发版与 `release.json` 同批更新。
- 下载区与页脚各加一个「更新日志」入口。
- 同样需加入 deploy tar 与冒烟。

### 4.9 演示区块（可选，最后做）

- 把 4.1 移出的 `.workbench-scene` 播放器放到新位置：`#demo`，标题「看它跑完一轮」。
- 增强：点击时间轴 tick 跳到对应步骤；hover 高亮当轮消息；播放结束后按钮变「重播」（已有逻辑）。
- 仅当 hero 已换成真实截图后再做，避免和首屏抢注意力。

### 4.10 截图管线

- 目录 `shots/`：`hero.webp`、`diff.webp`、`subagents.webp`、`browser-qa.webp`。
- 脚本 `scripts/capture-shots.mjs`：
  - 启动打包后的 Electron，载入种子仓库（固定 `lectern-demo`），用 CDP `Page.captureScreenshot` 输出 2x PNG → 转 WebP。
  - 截图前固定：窗口 1440×900、系统深浅色、字体已加载、版本号区域裁掉或替换为占位。
  - 产物预算：hero ≤ 200KB，其余单张 ≤ 80KB，合计 ≤ 400KB。
- `deploy.yml` 打包清单加 `shots/`，冒烟检查 `hero.webp` 200 且 `content-type: image/webp`。
- 无截图资产时：hero 暂留现有 CSS 演示，其余区块照常推进；**不要用生成图冒充产品截图**。

## 5. 风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| 改结构碰坏 sync-version 锚点 | 下次发版版本号不同步，线上直链过期 | 每步改完本地跑 `python3 scripts/sync-version.py` 看是否命中；给 check-release 增加 `sync-version --check` 干跑门禁 |
| `asset_rev` 忘 bump | 用户继续吃旧 CSS | 把 theme.css/js 的 sha256 前缀写进 release.json，CI 比对（后续增强） |
| 新页面漏进 deploy tar | 线上 404/500 | 冒烟路径同时加进 CI；部署后 curl 验证 |
| 截图过期（版本号/UI 变化） | 首屏证据失真 | 发版清单加「重截」一项；图内不出现版本号 |
| Hero 大图拖慢 LCP | 移动端体验下降 | 预算 200KB、显式尺寸、`fetchpriority=high`，LCP 实测 < 2.0s |
| 对照表措辞不实 | 品牌可信度受损 | 只写可验证事实，不确定留 `—` |
| `#v11` 外链失效 | 少量旧链接跳空 | 上线前查访问日志；保留零高度锚点 |
| 筛选 chips 无 JS 不可用 | 渐进增强失败 | 默认全显，JS 仅做隐藏；chips 在无 JS 时隐藏 |

## 6. 明确不做

- 不换设计语言、不换字体、不加第二强调色。
- 不加轮播、自动播放视频、粒子/光晕背景、滚动劫持。
- 不做明暗主题切换（站点是暖纸 + 反白带的固定节奏）。
- 不引入前端框架或构建步骤。
- 不加统计脚本 / cookie banner（要加单独讨论）。
- 不在首页罗列全部 15 项功能。
- 不做假的“用户数 / 下载量 / 评分”。

## 7. 实施顺序

每步可独立上线，前一步不阻塞后一步（除注明依赖）：

1. **404 + Caddy handle_errors**（零依赖，先补洞）
2. **Hero 左半**：5/7 栅格、文案压缩、证据行、run-circuit 收敛
3. **第二屏替换**：`#v11` → `#loop` 三卡；同批把 0.11 内容迁入 features.html 生产链分组
4. **Foundation 4 卡 + Workflow 三步上手**
5. **features 筛选 chips**（含 `data-group` 统一）
6. **why 对照表**
7. **Download 增强 + changelog.html**
8. **截图管线 + Hero 右半替换**（依赖 4.10 与真实截图）
9. **演示区块改造**（可选，依赖 2 与 8）

## 8. 验收标准

- 1440×900 与 390×844 首屏都能看到：产品是什么、给谁用、主下载按钮。
- 下载入口在 2 屏内可达；键盘 Tab 顺序正确。
- 无 JS 时：导航、下载链接、全部功能内容可用。
- 移动端无横向溢出；对照表可横滚。
- `sync-version.py` 全规则命中；`check-release.py` 通过；所有新页面在冒烟清单。
- 性能预算：首屏传输 ≤ 900KB（字体 560 + CSS 60 + 图 200 + HTML 30），LCP < 2.0s，CLS < 0.02。
- 全站不出现旧版本号（除 changelog 与路线页历史叙述）。
- reduced-motion 下无自动播放、无位移动效。
