#!/usr/bin/env python3
"""把 release.json 的版本号与下载直链同步进各页面（含 404 与更新日志）。

发版流程：改 release.json → python3 scripts/sync-version.py → git diff 复核。
只动「锚定位置」（下载直链、tag 链接、CTA、pill、footer、资源版本号），
正文里提到历史版本的叙述（如「已上线（0.10）」）一律不碰。
更新日志只同步资源版本与页首说明，历史条目的 Release 链接必须原样保留。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["index.html", "features.html", "why.html", "roadmap.html", "404.html"]
CHANGELOG = "changelog.html"
VER = r"\d+\.\d+\.\d+"

rel = json.loads((ROOT / "release.json").read_text(encoding="utf-8"))
v = rel["version"]
tag_url = f"https://github.com/zmzai-cloud/zmzai-lectern/releases/tag/v{v}"

RULES = [
    ("资源版本参数", rf'(<link rel="stylesheet" href="/theme\.css\?v=)[^"]+', r'\g<1>' + rel["asset_rev"]),
    ("资源版本参数", rf'(<script src="/theme\.js\?v=)[^"]+', r'\g<1>' + rel["asset_rev"]),
    ("Release tag 链接", rf'href="https://github\.com/zmzai-cloud/zmzai-lectern/releases/tag/v{VER}"', f'href="{tag_url}"'),
    # 只换版本段，不换目录前缀。曾经误写成把整段换成 oss（完整 URL），每次运行
    # 都会往每个直链前多叠一个 "releaseshttps://..."，下载链接越同步越坏。
    ("OSS 直链目录", rf'/harness/v{VER}/', f"/harness/v{v}/"),
    ("macOS/Windows 包名", rf'Lectern-(Setup-)?{VER}(\.exe|-arm64(?:-mac)?\.dmg|-arm64\.dmg|-arm64-mac\.zip|-win\.zip)', r'Lectern-\g<1>' + v + r'\g<2>'),
    ("导航下载按钮", rf'下载 v{VER}', f"下载 v{v}"),
    ("页脚版本链接", rf'>v{VER}</a>', f">v{v}</a>"),
    ("下载表平台行", rf'· v{VER}</small>', f"· v{v}</small>"),
    ("CTA 说明行", rf'v{VER} · Apple Silicon', f"v{v} · Apple Silicon"),
    ("Hero 版本 pill", rf'(<span class="pill-dot"[^>]*></span>)v{VER}[^<]*', r"\g<1>" + rel["pill"]),
    ("发版说明行", r'(<p class="dl-release[^"]*"[^>]*>).*?(</p>)', r"\g<1>" + f"v{v} · {rel['release_date']} · " + '<a href="changelog.html">更新了什么 →</a>' + r"\g<2>"),
    ("路线页版本戳", rf'v{VER} 已发布', f"v{v} 已发布"),
    ("路线页月份戳", rf'v{VER} · \d{{4}}-\d{{2}}', f"v{v} · {rel['release_date'][:7]}"),
    ("对照表版本戳", rf'对比基于 v{VER}', f"对比基于 v{v}"),
    ("JSON-LD 版本", r'("softwareVersion": ")[^"]+', r"\g<1>" + v),
    ("JSON-LD 日期", r'("datePublished": ")[^"]+', r"\g<1>" + rel["release_date"]),
]

CHANGELOG_ONLY = [
    ("更新日志页首", r'(<p class="cl-now-text"[^>]*>).*?(</p>)', r"\g<1>" + rel["release_note"] + r"\g<2>"),
]


def main() -> int:
    total = {}

    def apply(name: str, rules) -> None:
        path = ROOT / name
        text = path.read_text(encoding="utf-8")
        original = text
        for label, pattern, repl in rules:
            text, n = re.subn(pattern, repl, text)
            if n:
                total[label] = total.get(label, 0) + n
        if text != original:
            path.write_text(text, encoding="utf-8")
            print(f"  更新 {name}")

    for name in PAGES:
        apply(name, RULES)
    apply(CHANGELOG, RULES[:2] + CHANGELOG_ONLY)

    all_rules = RULES + CHANGELOG_ONLY
    print("同步完成（release.json = v%s）：" % v)
    for label in dict.fromkeys(r[0] for r in all_rules):
        print(f"  {label:14} {total.get(label, 0)} 处")
    missing = [r[0] for r in all_rules if total.get(r[0], 0) == 0]
    if missing:
        print("\n⚠ 以下锚点一次都没命中，检查 release.json 或页面结构是否改动：", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
