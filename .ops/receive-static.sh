#!/usr/bin/env bash
# =============================================================================
# receive-static.sh — 香港服务器「静态站点」部署接收器
#
# 由 GitHub Actions 通过受限 SSH 密钥调用：/root/.ssh/authorized_keys 里
# command= 指向本脚本，钥匙泄漏也拿不到 shell，只能往固定目录写静态文件。
#
# 用法（客户端）：
#   tar -czf - index.html theme.css ... | ssh -i key root@<host>
#
# 子命令（由 forced command 固定传入，见 authorized_keys）：
#   lectern   解包到 /var/www/lectern
#
# 与 relay 的 receive-deploy.sh 的分工：那个管 pm2 应用（release 目录 + 软链切换
# + 重启），这个只管静态文件（备份 + 解包），无进程需要重启。
# =============================================================================
set -euo pipefail

APP="${1:-}"

case "$APP" in
  lectern) TARGET="/var/www/lectern" ;;
  *) echo "ERROR: unknown app '$APP'" >&2; exit 1 ;;
esac

TS=$(date '+%Y%m%d-%H%M%S')
# 备份必须在 web root 之外：此前写在 $TARGET/.bak-* 里，Caddy 直接对外服务，
# 旧版落地页能被公网抓走（2026-10-11 排查发现 /.bak-20260924-*/index.html 返回 200）。
ARCHIVE_ROOT="/var/www/lectern-archive/$APP"
BAK="$ARCHIVE_ROOT/$TS"
KEEP=10
TMP=$(mktemp -d /tmp/static-deploy.XXXXXX)
trap 'rm -rf "$TMP"' EXIT

cat > "$TMP/site.tgz"
if [ ! -s "$TMP/site.tgz" ]; then
  echo "ERROR: empty payload" >&2
  exit 1
fi
if ! tar -tzf "$TMP/site.tgz" >/dev/null 2>&1; then
  echo "ERROR: bad tarball" >&2
  exit 1
fi

# 只放行静态后缀，挡掉任何可执行文件混入；同时挡掉 macOS AppleDouble（._xxx）
while read -r name; do
  case "$name" in
    */) continue ;;   # 目录条目（如 fonts/）
    ._*|*/._*) echo "ERROR: AppleDouble entry in payload: $name (打包时设 COPYFILE_DISABLE=1)" >&2; exit 1 ;;
    *.html|*.css|*.js|*.png|*.svg|*.ico|*.txt|*.json|*.xml|*.woff2) ;;
    *) echo "ERROR: disallowed file in payload: $name" >&2; exit 1 ;;
  esac
done < <(tar -tzf "$TMP/site.tgz")

mkdir -p "$BAK"
for f in $(tar -tzf "$TMP/site.tgz"); do
  case "$f" in */) continue ;; esac
  if [ -f "$TARGET/$f" ]; then
    mkdir -p "$BAK/$(dirname "$f")"
    cp -p "$TARGET/$f" "$BAK/$f"
  fi
done

tar -xzf "$TMP/site.tgz" -C "$TARGET"

# 保留最近 $KEEP 份，超出的旧备份自动清理
ls -1dt "$ARCHIVE_ROOT"/*/ 2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm -rf

echo "OK deployed $APP -> $TARGET (backup: $BAK, keeping last $KEEP)"
