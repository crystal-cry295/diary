"""
日记云储存服务 — FastAPI + SQLite
"""
import os, json, base64, hashlib, time, re
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import aiosqlite

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "diary.db"
IMG_DIR = BASE_DIR / "images"
IMG_DIR.mkdir(exist_ok=True)
HTML_PATH = BASE_DIR / "index.html"

PWD_FILE = BASE_DIR / ".password"

# ==================== 数据库 ====================
async def get_db():
    db = await aiosqlite.connect(str(DB_PATH))
    await db.execute("CREATE TABLE IF NOT EXISTS diaries (id TEXT PRIMARY KEY, createdAt TEXT, updatedAt TEXT, content TEXT, images TEXT)")
    await db.commit()
    return db

# ==================== 密码 ====================
def read_password():
    if PWD_FILE.exists():
        return PWD_FILE.read_text().strip()
    return None

def write_password(pwd):
    PWD_FILE.write_text(pwd)

# ==================== 图片辅助 ====================
def save_images(images_data: list) -> list:
    """保存 base64 图片到磁盘，返回相对路径列表"""
    saved = []
    for img in images_data:
        data = img.get("data", "")
        if not data.startswith("data:"):
            saved.append(img)
            continue
        # 提取 base64
        m = re.match(r'data:image/(\w+);base64,(.+)', data)
        if not m:
            continue
        ext = m.group(1) if m.group(1) != "jpeg" else "jpg"
        raw = base64.b64decode(m.group(2))
        fname = f"{int(time.time()*1000)}_{len(raw)}.{ext}"
        fpath = IMG_DIR / fname
        fpath.write_bytes(raw)
        saved.append({"name": fname, "path": f"/img/{fname}"})
    return saved

def image_urls(saved: list) -> list:
    """将存储的图片转为前端可用的 URL 路径"""
    result = []
    for img in saved:
        if "path" in img:
            # 同时提供 url 和 data fallback，data 用服务器路径
            result.append({"url": img["path"], "data": img["path"], "name": img.get("name", "")})
        elif "data" in img and img["data"].startswith("data:"):
            result.append(img)
        else:
            result.append(img)
    return result

def load_images_as_base64(saved: list) -> list:
    """仅在新建/导入时用于保存 base64，列表接口不再使用"""
    return image_urls(saved)

# ==================== API ====================

@app.get("/api/password/status")
async def password_status():
    return {"hasPassword": read_password() is not None}

@app.post("/api/password/set")
async def password_set(data: dict):
    if read_password():
        raise HTTPException(400, "密码已存在")
    pwd = data.get("password", "")
    if not re.match(r'^\d{4}$', pwd):
        raise HTTPException(400, "密码须为4位数字")
    write_password(pwd)
    return {"ok": True}

@app.post("/api/password/verify")
async def password_verify(data: dict):
    saved = read_password()
    if not saved:
        raise HTTPException(400, "密码未设置")
    if data.get("password") != saved:
        raise HTTPException(401, "密码错误")
    return {"ok": True}

@app.get("/api/diaries")
async def list_diaries():
    db = await get_db()
    async with db.execute("SELECT * FROM diaries ORDER BY createdAt DESC") as cur:
        rows = await cur.fetchall()
    entries = []
    for r in rows:
        images = json.loads(r[4]) if r[4] else []
        entries.append({
            "id": r[0], "createdAt": r[1], "updatedAt": r[2],
            "content": r[3], "images": image_urls(images)
        })
    return entries

@app.post("/api/diaries")
async def create_diary(data: dict):
    eid = data.get("id") or f"d{int(time.time()*1000)}"
    images = save_images(data.get("images", []))
    images_json = json.dumps(images, ensure_ascii=False)
    db = await get_db()
    await db.execute(
        "INSERT OR REPLACE INTO diaries VALUES (?,?,?,?,?)",
        (eid, data.get("createdAt",""), data.get("updatedAt",""), data.get("content",""), images_json)
    )
    await db.commit()
    return {"ok": True, "id": eid}

@app.put("/api/diaries/{eid}")
async def update_diary(eid: str, data: dict):
    images = save_images(data.get("images", []))
    images_json = json.dumps(images, ensure_ascii=False)
    db = await get_db()
    await db.execute(
        "UPDATE diaries SET content=?, images=?, updatedAt=? WHERE id=?",
        (data.get("content",""), images_json, data.get("updatedAt",""), eid)
    )
    await db.commit()
    return {"ok": True}

@app.delete("/api/diaries/{eid}")
async def delete_diary(eid: str):
    # 先读取图片路径，删除磁盘文件
    db = await get_db()
    async with db.execute("SELECT images FROM diaries WHERE id=?", (eid,)) as cur:
        row = await cur.fetchone()
    if row and row[0]:
        for img in json.loads(row[0]):
            if "name" in img:
                fpath = IMG_DIR / img["name"]
                if fpath.exists():
                    fpath.unlink()
    await db.execute("DELETE FROM diaries WHERE id=?", (eid,))
    await db.commit()
    return {"ok": True}

@app.get("/img/{fname}")
async def serve_image(fname: str):
    fpath = IMG_DIR / fname
    if not fpath.exists():
        raise HTTPException(404)
    return FileResponse(fpath)

@app.post("/api/import")
async def import_diaries(data: dict):
    """批量导入"""
    entries = data.get("entries", [])
    if not entries:
        raise HTTPException(400, "无数据")
    db = await get_db()
    count = 0
    for entry in entries:
        eid = entry.get("id", f"d{int(time.time()*1000)}_{count}")
        images = save_images(entry.get("images", []))
        images_json = json.dumps(images, ensure_ascii=False)
        await db.execute(
            "INSERT OR REPLACE INTO diaries VALUES (?,?,?,?,?)",
            (eid, entry.get("createdAt",""), entry.get("updatedAt",""),
             entry.get("content",""), images_json)
        )
        count += 1
    await db.commit()
    return {"ok": True, "imported": count}

# ==================== 前端 ====================
@app.get("/")
async def index():
    return FileResponse(HTML_PATH, media_type="text/html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
