#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT_DIR/.run"
LOG_DIR="$ROOT_DIR/logs"
BACKEND_PID_FILE="$RUN_DIR/backend.pid"
FRONTEND_PID_FILE="$RUN_DIR/frontend.pid"

log() {
  printf '[smart-labor] %s\n' "$*"
}

pid_is_alive() {
  local pid="${1:-}"
  [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1
}

read_pid_file() {
  local pid_file="$1"
  [[ -f "$pid_file" ]] || return 0
  tr -cs '0-9' '\n' < "$pid_file" | sed '/^$/d'
}

collect_descendants() {
  local parent="$1"
  local children
  local child

  command -v pgrep >/dev/null 2>&1 || return 0
  children="$(pgrep -P "$parent" 2>/dev/null || true)"
  for child in $children; do
    collect_descendants "$child"
    printf '%s\n' "$child"
  done
}

stop_one() {
  local name="$1"
  local pid_file="$2"
  local pids
  local pid
  local live_roots
  local descendants
  local targets
  local target
  local still_alive
  local i

  pids="$(read_pid_file "$pid_file" || true)"
  if [[ -z "$pids" ]]; then
    log "${name} 未记录 PID，跳过"
    rm -f "$pid_file"
    return 0
  fi

  live_roots=""
  for pid in $pids; do
    if pid_is_alive "$pid"; then
      live_roots="$live_roots $pid"
    fi
  done

  if [[ -z "$live_roots" ]]; then
    log "${name} PID 已失效，清理记录：$(printf '%s\n' "$pids" | tr '\n' ' ')"
    rm -f "$pid_file"
    return 0
  fi

  descendants=""
  for pid in $live_roots; do
    descendants="$descendants $(collect_descendants "$pid" || true)"
  done
  targets="$descendants $live_roots"

  log "停止 ${name}，PID：$(printf '%s\n' "$live_roots" | tr '\n' ' ')"
  for target in $targets; do
    pid_is_alive "$target" && kill "$target" >/dev/null 2>&1 || true
  done

  for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
    still_alive=""
    for target in $targets; do
      if pid_is_alive "$target"; then
        still_alive="$still_alive $target"
      fi
    done

    [[ -z "$still_alive" ]] && break
    sleep 0.5
  done

  if [[ -n "${still_alive:-}" ]]; then
    log "${name} 未在超时时间内退出，强制结束：$still_alive"
    for target in $still_alive; do
      pid_is_alive "$target" && kill -9 "$target" >/dev/null 2>&1 || true
    done
  fi

  rm -f "$pid_file"
}

mkdir -p "$RUN_DIR" "$LOG_DIR"

stop_one "前端页面" "$FRONTEND_PID_FILE"
stop_one "后端 API" "$BACKEND_PID_FILE"

log "停止完成"
printf '日志目录：%s\n' "$LOG_DIR"
