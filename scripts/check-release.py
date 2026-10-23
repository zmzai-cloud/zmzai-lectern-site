#!/usr/bin/env python3
"""发版一致性门禁：release.json 是唯一真源，四个页面必须与它一致。

用法：
  python3 scripts/check-release.py          # 离线校验（CI 每次跑）
  python3 scripts/check-release.py --live   # 额外 HEAD 所有下载直链，确认 404 不放过

存在理由：0.12 发版后 features/why/roadmap 三页的导航与页脚仍写着 v0.11.2，
roadmap 的进度戳也停在两个版本前——版本号散在 18 处手工改，必然漏。
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["index.html", "features.html", "why.html", "roadmap.html"]
VER = r"\d+\.\d+\.\d+"
LIVE = "--live" in sys.argv
errors = []


def err(msg: str) -> None:
    errors.append(msg)


rel = json.loads((ROOT / "release.json").read_text(encoding="utf-8"))
v = rel["version"]

texts = {p: (ROOT / p).read_text(encoding="utf-8") for p in PAGES}

# 1. 锚定位置的版本号必须等于 release.json
ANCHORS = {
    "导航下载按钮": rf"下载 v{VER}",
    "页脚版本链接": rf">v{VER}</a>",
    "Release tag 链接": rf"releases/tag/v{VER}",
    "OSS 直链目录": rf"/harness/v{VER}/",
    "安装包文件名": rf"Lectern-(?:Setup-)?{VER}",
}
for label, pattern in ANCHORS.items():
    for page, text in texts.items():
        for hit in re.findall(pattern, text):
            m = re.search(VER, hit)
            if m and m.group(0) != v:
                err(f"{page}: {label} 指向 v{m.group(0)}，release.json 是 v{v}")

# 2. 只允许 release.json 里登记的直链，且每个 artifact 都要被首页引用。
#    按完整 href 属性提取再精确比对：曾经用子串扫描，URL 被同步脚本叠坏成
#    "releaseshttps://..." 时照样匹配到干净尾巴，坏链接漏检上线。
oss_hrefs = set(re.findall(r'href="(' + re.escape(rel["oss_base"]) + r'[^"]*)"', texts["index.html"]))
allowed = {f'{rel["oss_base"]}/v{v}/{a}' for a in rel["artifacts"].values()}
for u in sorted(oss_hrefs - allowed):
    err(f"index.html: 下载直链不在 release.json 的 artifacts 里：{u[-60:]}")
for u in sorted(allowed - oss_hrefs):
    err(f"index.html: release.json 登记的 artifact 未被引用：{u.split('/')[-1]}")

# 3. 站内链接与资源必须存在
for page, text in texts.items():
    for href in set(re.findall(r'href="((?!https?:|#|mailto:)[^"]+)"', text)):
        target = ROOT / href.split("#")[0].split("?")[0].lstrip("/")
        if not target.exists():
            err(f"{page}: 站内链接指向不存在的文件 {href}")
    for src in set(re.findall(r'src="((?!https?:)[^"]+)"', text)):
        if not (ROOT / src.split("?")[0].lstrip("/")).exists():
            err(f"{page}: 脚本/图片资源不存在 {src}")

# 4. theme.css 引用的字体子集必须已生成
css = (ROOT / "theme.css").read_text(encoding="utf-8")
for f in re.findall(r"url\('(/fonts/[^']+)'\)", css):
    if not (ROOT / f.lstrip("/")).exists():
        err(f"theme.css: 字体缺失 {f}（跑 scripts/build-fonts.sh）")
if "cdn.jsdelivr.net" in css:
    err("theme.css: 仍在引用 jsDelivr 字体（首屏会拉 16MB，且大陆可达性不稳）")

# 5. SEO 必备头
for page, text in texts.items():
    for need in ("<link rel=\"canonical\"", "og:image", "name=\"description\"", "apple-touch-icon"):
        if need not in text:
            err(f"{page}: 缺少 {need}")
sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
for page in PAGES + ["changelog.html"]:
    url = rel["site_url"] + ("/" if page == "index.html" else f"/{page}")
    if url not in sitemap:
        err(f"sitemap.xml: 缺少 {url}")

# 6. 无 JS 兜底：reveal 必须门控在 html.js 下
if "html.js .reveal" not in css:
    err("theme.css: .reveal 未被 html.js 门控，JS 失败会整页空白")
for page, text in texts.items():
    if "documentElement.classList.add('js')" not in text:
        err(f"{page}: <head> 缺 html.js 引导脚本")

# 7. 第二屏「产品闭环」守卫：三张卡必须链到 features 里真实存在的锚点，
#    否则首页主叙事会跳空；样式挂 class 不挂 #id，区块改名不会失配。
if not re.search(r'<section[^>]*id="loop"', texts["index.html"]):
    err("index.html: 缺第二屏 #loop（产品闭环）")
for target in ("f-subagents", "f-diff", "f-verify", "f-rewind", "f-resume", "f-audit"):
    if f'href="features.html#{target}"' not in texts["index.html"]:
        err(f"index.html: 卡片缺指向 features.html#{target} 的链接")
    if not re.search(rf'<article[^>]*id="{target}"', texts["features.html"]):
        err(f"features.html: 缺 #{target} 条目（首页卡片会跳空）")
if ".loop-grid" not in css:
    err("theme.css: 产品闭环三卡样式 .loop-grid 缺失")
if ".foundation-grid" not in css:
    err("theme.css: Foundation 四卡样式 .foundation-grid 缺失")
if 'docs-side-group">生产链' not in texts["features.html"]:
    err("features.html: 侧栏缺「生产链」分组")

# 7b. 功能筛选、对照表与下载/更新日志入口
feat = texts["features.html"]
if 'class="docs-filter"' not in feat:
    err("features.html: 缺筛选 chips 栏 .docs-filter")
chip_groups = set(re.findall(r'data-filter="([^"]+)"', feat)) - {"all"}
item_groups = set(re.findall(r'<article class="docs-item"[^>]*data-group="([^"]+)"', feat))
if chip_groups != item_groups:
    err(f"features.html: chips 分组 {sorted(chip_groups)} 与 data-group {sorted(item_groups)} 不一致")
if len(re.findall(r'<article class="docs-item"', feat)) != 17:
    err("features.html: 功能条目不是 17 项")
if feat.count('class="docs-preview"') != 4:
    err("features.html: CSS 示意预览应为 4 块（回卷另有交互演示）")
if 'class="docs-demo"' not in feat:
    err("features.html: 回卷交互演示缺失")
if "html.filters-ready .docs-filter" not in css:
    err("theme.css: 筛选栏未由 filters-ready 门控（无 JS 时应隐藏）")
why = texts["why.html"]
if 'class="compare-table"' not in why:
    err("why.html: 缺横向对照表 .compare-table")
if f"对比基于 v{v}" not in why:
    err(f"why.html: 对照表版本戳未对齐 v{v}")
if not re.search(r'<p class="dl-release[^"]*"[^>]*>v' + re.escape(v) + r' · ' + re.escape(rel["release_date"]) + r' · <a href="changelog.html">', texts["index.html"]):
    err("index.html: 下载区版本行缺日期或更新日志链接")
for page, text in texts.items():
    if '<a href="changelog.html">更新日志</a>' not in text:
        err(f"{page}: 页脚缺更新日志入口")

# 7c. 更新日志页：最新版本/日期/说明必须与 release.json 一致，资源版本不得落后
cl_path = ROOT / "changelog.html"
if not cl_path.exists():
    err("changelog.html: 文件缺失")
else:
    cl = cl_path.read_text(encoding="utf-8")
    first_ver = re.search(r'<h2 class="cl-ver">v([^<]+)</h2>', cl)
    if not first_ver or first_ver.group(1) != v:
        err(f"changelog.html: 第一条版本不是 v{v}")
    if f'<span class="cl-date">{rel["release_date"]}</span>' not in cl:
        err(f"changelog.html: 最新版本日期不是 {rel['release_date']}")
    if rel["release_note"] not in cl:
        err("changelog.html: 页首说明与 release.json release_note 不一致")
    for need in ("<link rel=\"canonical\"", "og:image", "name=\"description\"", "apple-touch-icon"):
        if need not in cl:
            err(f"changelog.html: 缺少 {need}")
    if "documentElement.classList.add('js')" not in cl:
        err("changelog.html: <head> 缺 html.js 引导脚本")
    for rev in set(re.findall(r'\?v=([^"]+)', cl)):
        if rev != rel["asset_rev"]:
            err(f"changelog.html: 资源版本 {rev} 与 release.json asset_rev {rel['asset_rev']} 不一致")
    for href in set(re.findall(r'href="((?!https?:|#|mailto:)[^"]+)"', cl)):
        target = ROOT / href.split("#")[0].split("?")[0].lstrip("/")
        if not target.exists():
            err(f"changelog.html: 站内链接指向不存在的文件 {href}")

# 8. 交互护栏：当前页要标 aria-current；hover 态规则必须包在 (hover: hover) 里，
#    裸 hover 在触屏上点击后会"粘住"（sticky hover）。
for page, text in texts.items():
    if 'aria-current="page"' not in text:
        err(f'{page}: 导航缺 aria-current="page"')
for line in css.splitlines():
    if ":hover" in line and "@media (hover" not in line and line.lstrip().startswith((".", "a", "s", "#")):
        err(f"theme.css: hover 规则未包进 @media (hover: hover)：{line.strip()[:60]}")

# 9. 404 页：不收录；错误页会在任意层级响应，站内链接必须绝对路径；
#    资源版本必须跟 release.json 一起走，否则 404 会钉死旧样式
nf = (ROOT / "404.html").read_text(encoding="utf-8")
if 'name="robots" content="noindex' not in nf:
    err("404.html: 缺 robots noindex，错误页会被搜索引擎收录")
for href in set(re.findall(r'href="((?!#|https?:|mailto:)[^"]+)"', nf)):
    if not href.startswith("/"):
        err(f"404.html: 站内链接必须用绝对路径（错误页在任意层级响应）：{href}")
    else:
        target = ROOT / href.split("#")[0].split("?")[0].lstrip("/")
        if not target.exists():
            err(f"404.html: 站内链接指向不存在的文件 {href}")
for rev in set(re.findall(r'\?v=([^"]+)', nf)):
    if rev != rel["asset_rev"]:
        err(f"404.html: 资源版本 {rev} 与 release.json asset_rev {rel['asset_rev']} 不一致")
if '<a href="/changelog.html">更新日志</a>' not in nf:
    err("404.html: 页脚缺绝对路径的更新日志入口")

if LIVE:
    # 只探站外 OSS 直链：它们必须先于落地页存在。本站新资源（og-image/sitemap/fonts）
    # 由这次部署才推上去，在这里探必然 404——那由 deploy.yml 的冒烟步骤负责。
    for u in sorted(allowed):
        req = urllib.request.Request(u, method="HEAD", headers={"User-Agent": "check-release"})
        try:
            code = urllib.request.urlopen(req, timeout=25).status
        except Exception as e:
            code = f"ERR {e}"
        if code != 200:
            err(f"--live: {u} -> {code}")
        else:
            print(f"  200 {u}")

print(f"check-release: v{v} · {len(PAGES)} 页 · {len(errors)} 个问题" if not errors else "")
for e in errors:
    print("  ✗", e)
sys.exit(1 if errors else 0)
