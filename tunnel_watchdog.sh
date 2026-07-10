#!/bin/bash
export PATH=/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:$PATH
LOG=/Users/Admin/cry/server/tunnel_url.txt
ERR_LOG=/Users/Admin/cry/server/tunnel_error.log

while true; do
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 连接隧道..." >> "$ERR_LOG"

  # 启动 SSH 隧道，捕获 URL
  ssh -n -o StrictHostKeyChecking=no -o ServerAliveInterval=60 \
    -o ConnectTimeout=15 -o ConnectionAttempts=2 \
    -o ExitOnForwardFailure=yes \
    -R 80:localhost:8080 serveo.net 2>&1 | while IFS= read -r line; do
    echo "[$(date '+%H:%M:%S')] $line" >> "$ERR_LOG"
    # 提取 serveo URL
    url=$(echo "$line" | grep -oE 'https://[a-z0-9]+[^ ]*serveo[^ ]*' | head -1)
    if [ -n "$url" ]; then
      echo "$url" > "$LOG"
      echo "[$(date '+%Y-%m-%d %H:%M:%S')] URL: $url" >> "$ERR_LOG"
    fi
  done

  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 隧道断开，10秒后重连..." >> "$ERR_LOG"
  sleep 10
done
