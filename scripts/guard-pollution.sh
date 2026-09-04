#!/bin/sh
# lectern-site pollution guard
# ─────────────────────────────────────────────
# 背景: lectern landing 的三个 HTML(index/why/roadmap)在 09-04 反复被「看不见的
# 中间态」悄悄写回带 data-page-node-id 残留的版本(roadmap.html 11496 字节/88 处
# 残留最频繁,index/why 偶发)。原因不明(疑似编辑器扩展/同步进程/历史恢复),
# 但污染 id 与单文件母版不重合(0%),与 _archive 备份的污染版 md5 重合。
# 根治:污染种子已隔离到 /Users/ulanxx/ulanxx_workspace/zmzai/_polluted-archive/。
# 此脚本:检测 + 自动恢复,作为最后一道防线。
# 用法:
#   ./scripts/guard-pollution.sh            # 自检,污染则从线上拉回
#   ./scripts/guard-pollution.sh --check    # 只检不修
#   ./scripts/guard-pollution.sh --watch    # 30 秒轮询(用于监控)
#   ./scripts/guard-pollution.sh --install-cron  # 加 5 分钟轮询 cron
# ─────────────────────────────────────────────

set -e

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

FILES="index.html why.html roadmap.html features.html"
ONLINE="https://lectern.zmzai.cloud"

check_one() {
  f="$1"
  if [ ! -f "$f" ]; then return 0; fi
  # awk 计数(避开 BSD grep -c 换行坑)
  res=$(awk '/data-page-node-id/{c++} END{print c+0}' "$f")
  if [ "$res" != "0" ]; then
    echo "  ⚠ $f: $res 处 data-page-node-id 残留"
    return 1
  fi
  return 0
}

restore_one() {
  f="$1"
  if [ ! -f "$f" ]; then return; fi
  res=$(awk '/data-page-node-id/{c++} END{print c+0}' "$f")
  if [ "$res" != "0" ]; then
    echo "  → 从线上拉回 $f ..."
    if curl -fsS --noproxy '*' --max-time 10 "$ONLINE/$f" -o "$f"; then
      new=$(awk '/data-page-node-id/{c++} END{print c+0}' "$f")
      if [ "$new" = "0" ]; then
        echo "    ✓ 恢复成功"
      else
        echo "    ✗ 拉回后仍有 $new 处残留(线上已被污染?)"
      fi
    else
      echo "    ✗ curl 失败,需手动处理"
    fi
  fi
}

case "${1:-check-fix}" in
  --check)
    echo "── pollution 自检(只检不修)──"
    viol=0
    for f in $FILES; do
      if ! check_one "$f"; then viol=1; fi
    done
    [ $viol -eq 0 ] && echo "  ✓ 三 HTML 干净(0 处 data-page-node-id)"
    exit $viol
    ;;

  --check-fix|"")
    echo "── pollution 自检 + 自动恢复 ──"
    viol=0
    for f in $FILES; do
      if ! check_one "$f"; then viol=1; fi
    done
    if [ $viol -eq 0 ]; then
      echo "  ✓ 三 HTML 干净,无需恢复"
      exit 0
    fi
    echo "  尝试从线上自动拉回..."
    for f in $FILES; do restore_one "$f"; done
    echo "  建议: git diff 看变化 + git commit"
    exit 1
    ;;

  --watch)
    echo "── 30 秒轮询(可 Ctrl+C 停止)──"
    while true; do
      viol=0
      for f in $FILES; do
        if ! check_one "$f"; then viol=1; fi
      done
      [ $viol -eq 1 ] && {
        echo "  检出污染,自动恢复..."
        for f in $FILES; do restore_one "$f"; done
      }
      sleep 30
    done
    ;;

  --install-cron)
    cron_line="*/5 * * * * $REPO/scripts/guard-pollution.sh --check-fix >> $REPO/scripts/guard.log 2>&1"
    (crontab -l 2>/dev/null | grep -v 'guard-pollution' ; echo "$cron_line") | crontab -
    echo "  ✓ 已安装 cron:每 5 分钟跑一次,日志 $REPO/scripts/guard.log"
    ;;

  *)
    echo "用法: $0 [--check | --check-fix | --watch | --install-cron]"
    exit 2
    ;;
esac
