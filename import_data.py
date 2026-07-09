#!/usr/bin/env python3
"""导入现有日记数据到服务器 SQLite 数据库"""
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import asyncio
from server import get_db, write_password, save_images

async def main():
    # 设置默认密码: 1049
    write_password("1049")
    print("密码已设置: 1049")

    db = await get_db()
    total = 0
    part = 1
    while True:
        path = f"/Users/Admin/cry/diary_part{part}.json"
        if not os.path.exists(path):
            break
        print(f"导入 {path}...")
        with open(path) as f:
            entries = json.load(f)
        for e in entries:
            images = save_images(e.get("images", []))
            import json as j
            images_json = j.dumps(images, ensure_ascii=False)
            await db.execute(
                "INSERT OR REPLACE INTO diaries VALUES (?,?,?,?,?)",
                (e["id"], e.get("createdAt",""), e.get("updatedAt",""),
                 e.get("content",""), images_json)
            )
            total += 1
        print(f"  已导入 {total} 条")
        part += 1

    await db.commit()
    print(f"\n✅ 共导入 {total} 条日记")

if __name__ == "__main__":
    asyncio.run(main())
