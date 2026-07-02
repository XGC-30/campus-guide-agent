"""Whistle HAR → Markdown 知识库文件"""
import json
import sys
import os
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TARGET_HOST = "cowsms.com"
OUT_DIR = Path("data/hnie/food")


def parse_har(har_path: str):
    har = json.loads(Path(har_path).read_text(encoding="utf-8"))
    entries = har.get("log", {}).get("entries", [])

    # 收集所有 item_rooms（去重）
    rooms = {}
    items_by_room = {}

    for entry in entries:
        url = entry.get("request", {}).get("url", "")
        if TARGET_HOST not in url:
            continue

        text = entry.get("response", {}).get("content", {}).get("text", "")
        if not text:
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        if data.get("status") != "success":
            continue

        records = data.get("data", [])
        if not isinstance(records, list):
            records = [records]

        if "item_rooms" in url:
            for r in records:
                if isinstance(r, dict):
                    rooms[r.get("key", "")] = r
        elif "items" in url:
            for item in records:
                if isinstance(item, dict):
                    rid = str(item.get("room_id", ""))
                    items_by_room.setdefault(rid, []).append(item)

    # 输出 Markdown
    os.makedirs(OUT_DIR, exist_ok=True)

    lines = [
        "# hnies 校园美食指南\n",
        "> 数据来源：小程序自动抓取\n",
    ]
    for room_key, room in rooms.items():
        settings = json.loads(room.get("settings", "{}"))
        deliver = settings.get("deliver_title", "")
        notice = settings.get("notice", "")
        phone = settings.get("seller", {}).get("phone", "")
        location = settings.get("location", {}).get("poiname", "")

        lines.append(f"## {room['room_name']}\n")
        if deliver:
            lines.append(f"- 配送区域：{deliver}")
        if location:
            lines.append(f"- 地址：{location}")
        if phone:
            lines.append(f"- 电话：{phone}")
        if notice:
            lines.append(f"- 公告：{notice}")
        lines.append(f"- 评分：{int(room.get('star', 0))/10000:.1f}（{room.get('star_count', 0)} 评价）")
        lines.append("")

        # 菜品
        NOISE_WORDS = ["本店的", "商家", "品牌", "采购", "实拍", "备注", "厨房",
                       "打包区", "切菜区", "清洗区", "货架区", "调料", "食用油",
                       "丢餐", "收餐", "骑手", "校内", "配送至楼下"]
        for item in items_by_room.get(room.get("id", ""), []):
            name = item.get("name", "")
            price = item.get("price", 0)
            # 筛掉公告、非菜品、价格离谱的
            if not price or price > 5000 or price <= 0:
                continue
            if any(w in name for w in NOISE_WORDS):
                continue
            yuan = price / 100
            tag = item.get("tag", "")
            tag_str = f" {tag}" if tag else ""
            lines.append(f"- {name} ¥{yuan:.2f}{tag_str}")

        lines.append("")

    out_path = OUT_DIR / "食堂指南.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"写入 {out_path} ({len(rooms)} 家店) ")


if __name__ == "__main__":
    parse_har(sys.argv[1])
