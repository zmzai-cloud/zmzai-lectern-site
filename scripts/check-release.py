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

# 2. 只允许 release.json 里登记的直链，且每个 artifact 都要被首页引用
oss_urls = set(re.findall(re.escape(rel["oss_base"]) + r"/[A-Za-z0-9._/\-]+", texts["index.html"]))
allowed = {f'{rel["oss_base"]}/v{v}/{a}' for a in rel["artifacts"].values()}
for u in sorted(oss_urls - allowed):
    err(f"index.html: 下载直链不在 release.json 的 artifacts 里：{u.split('/')[-1]}")
for u in sorted(allowed - oss_urls):
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
for page in PAGES:
    url = rel["site_url"] + ("/" if page == "index.html" else f"/{page}")
    if url not in sitemap:
        err(f"sitemap.xml: 缺少 {url}")

# 6. 无 JS 兜底：reveal 必须门控在 html.js 下
if "html.js .reveal" not in css:
    err("theme.css: .reveal 未被 html.js 门控，JS 失败会整页空白")
for page, text in texts.items():
    if "documentElement.classList.add('js')" not in text:
        err(f"{page}: <head> 缺 html.js 引导脚本")

# 7. 武器区白底翻转必须挂在 class 上：0.11 把该 section 从 #v10 改名 #v11，
#    规则失配后近白文字直接压在白底上，整块主打区几乎看不见。
if ".arsenal-band" not in css:
    err("theme.css: 武器区翻转规则不再挂在 .arsenal-band 上（改回 #id 作用域会随改名失效）")
if not re.search(r'<section[^>]*class="[^"]*\barsenal-band\b', texts["index.html"]):
    err('index.html: 武器区 section 缺 class="arsenal-band"，白底翻转不生效')

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
