"""Whistle JSON 解码 — Unicode → 中文"""
import json
import sys
from pathlib import Path

# Windows GBK 终端 → UTF-8
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def decode(filepath: str):
    raw = Path(filepath).read_text()
    # ponytail: strip HTTP headers if Whistle exported them
    if raw.startswith("HTTP/"):
        raw = raw.split("\n\n", 1)[1]
    data = json.loads(raw)

    # 只关注 data 数组里的核心字段
    if isinstance(data, dict) and "data" in data:
        items = data["data"] if isinstance(data["data"], list) else [data["data"]]
    else:
        items = data if isinstance(data, list) else [data]

    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        # 只打印有用字段
        fields = {k: v for k, v in item.items()
                  if isinstance(v, (str, int, float)) and k not in ("settings", "openid")}
        print(f"\n--- [{i}] ---")
        for k, v in fields.items():
            if isinstance(v, str) and len(v) > 200:
                v = v[:200] + "..."
            print(f"  {k}: {v}")

if __name__ == "__main__":
    decode(sys.argv[1])
