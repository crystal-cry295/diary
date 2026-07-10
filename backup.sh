#!/bin/bash
# 每日备份脚本：导出全部日记为 JSON，保留最近 30 天备份
BACKUP_DIR=/Users/Admin/cry/server/backups
mkdir -p "$BACKUP_DIR"

DATE=$(date +%Y%m%d)
BACKUP_FILE="$BACKUP_DIR/diary_$DATE.json"

# 调用 API 导出（如果服务器在跑）
if curl -s -m 10 http://localhost:8080/api/diaries > "$BACKUP_FILE" 2>/dev/null; then
  # 验证 JSON 有效
  if /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -c "import json; json.load(open('$BACKUP_FILE'))" 2>/dev/null; then
    ENTRIES=$(/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -c "import json; print(len(json.load(open('$BACKUP_FILE'))))")
    echo "[$(date)] 备份成功: $ENTRIES 条 → $BACKUP_FILE" >> "$BACKUP_DIR/backup.log"

    # 保留最近 30 天，删旧的
    ls -t "$BACKUP_DIR"/diary_*.json 2>/dev/null | tail -n +31 | xargs rm -f 2>/dev/null
  else
    echo "[$(date)] 备份失败: JSON 无效" >> "$BACKUP_DIR/backup.log"
  fi
else
  echo "[$(date)] 备份失败: 服务器无响应" >> "$BACKUP_DIR/backup.log"
fi
