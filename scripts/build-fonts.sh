#!/usr/bin/env bash
# 重建自托管子集字体：MiSans(400/500/600) + Noto Serif SC(700) + JetBrains Mono(400/500)
#
# 为什么要子集：MiSans 全量 woff2 每个约 4.9MB、无 unicode-range 分片，
# 三权重 + 衬线一次拉走 16MB。子集只保留 *.html 里实际出现的字符（约 890 个），
# 合计 560KB。缺字按字体栈逐字回退 PingFang SC，不会出豆腐块。
#
# 用法：./scripts/build-fonts.sh
#   需要 python3 venv 装 fonttools + brotli（脚本会自建 .ops/venv）
#   源字体在 cdn.jsdelivr.net；本机不通时设 FONTS_HOST=<可通的机器> 走 ssh 代取
set -euo pipefail
cd "$(dirname "$0")/.."

SRC_DIR=".ops/fonts"
OUT_DIR="fonts"
VENV=".ops/venv"
CDN="https://cdn.jsdelivr.net"
SOURCES=(
  "$CDN/gh/dsrkafuu/misans@main/raw/Normal/woff2/MiSans-Regular.woff2"
  "$CDN/gh/dsrkafuu/misans@main/raw/Normal/woff2/MiSans-Medium.woff2"
  "$CDN/gh/dsrkafuu/misans@main/raw/Normal/woff2/MiSans-Semibold.woff2"
  "$CDN/npm/@fontsource/noto-serif-sc/files/noto-serif-sc-chinese-simplified-700-normal.woff2"
  "$CDN/npm/@fontsource/jetbrains-mono/files/jetbrains-mono-latin-400-normal.woff2"
  "$CDN/npm/@fontsource/jetbrains-mono/files/jetbrains-mono-latin-500-normal.woff2"
)

mkdir -p "$SRC_DIR" "$OUT_DIR"

if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q --disable-pip-version-check fonttools brotli
fi

for url in "${SOURCES[@]}"; do
  name="$(basename "$url")"
  [ -s "$SRC_DIR/$name" ] && continue
  if [ -n "${FONTS_HOST:-}" ]; then
    ssh -o BatchMode=yes "root@$FONTS_HOST" "curl -sL --max-time 120 '$url' -o /tmp/$name" </dev/null
    scp -q -o BatchMode=yes "root@$FONTS_HOST:/tmp/$name" "$SRC_DIR/$name"
  else
    curl -sL --max-time 120 "$url" -o "$SRC_DIR/$name"
  fi
  [ -s "$SRC_DIR/$name" ] || { echo "ERROR: 取不到源字体 $name" >&2; exit 1; }
done

python3 - "$SRC_DIR/charset.txt" <<'PY'
import glob, sys
chars = set()
for f in glob.glob('*.html'):
    chars |= set(open(f, encoding='utf-8').read())
chars |= set(chr(i) for i in range(32, 127))
chars |= set('·—…“”‘’、。，：；！？（）《》【】「」『』％°×÷→←↑↓✓✗●○＋－⏎▌│─┌┐└　 ')
chars = {c for c in chars if c not in '\t\r\n' and ord(c) > 31}
open(sys.argv[1], 'w', encoding='utf-8').write(''.join(sorted(chars)))
print(f'charset: {len(chars)} chars')
PY

map_pairs() {
  cat <<'EOF'
MiSans-Regular.woff2 misans-regular.woff2
MiSans-Medium.woff2 misans-medium.woff2
MiSans-Semibold.woff2 misans-semibold.woff2
noto-serif-sc-chinese-simplified-700-normal.woff2 noto-serif-sc-700.woff2
EOF
}

while read -r src out; do
  [ -z "$src" ] && continue
  "$VENV/bin/python" -m fontTools.subset "$SRC_DIR/$src" \
    --text-file="$SRC_DIR/charset.txt" --flavor=woff2 --layout-features='*' \
    --output-file="$OUT_DIR/$out"
  printf '  %-36s %s -> %s bytes\n' "$out" "$(wc -c <"$SRC_DIR/$src" | tr -d ' ')" "$(wc -c <"$OUT_DIR/$out" | tr -d ' ')"
done < <(map_pairs)

cp "$SRC_DIR/jetbrains-mono-latin-400-normal.woff2" "$OUT_DIR/jetbrains-mono-400.woff2"
cp "$SRC_DIR/jetbrains-mono-latin-500-normal.woff2" "$OUT_DIR/jetbrains-mono-500.woff2"

echo "OK $OUT_DIR ($(du -sh "$OUT_DIR" | cut -f1))"
