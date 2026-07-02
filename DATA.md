# 数据获取指南

## 完整流程（5 分钟 / 每学期）

校园数据通过微信小程序 API 抓取，自动转为知识库 Markdown 文件。

### 工具准备（仅首次）

```bash
npm install -g whistle
w2 start
```

浏览器打开 `http://127.0.0.1:8899` → 顶部 **HTTPS** 标签 → 勾选：
- `☑ Enable HTTPS`
- `☑ Capture TUNNEL CONNECTs`

下载 RootCA 证书 → 传到手机 → 安装为 **CA 证书**（不是 VPN 证书）。

### 手机代理配置

```
1. 电脑连 WiFi，查看 IP: ipconfig | findstr "IPv4"
2. 手机连同一 WiFi → 代理 → 手动
   服务器: 192.168.1.xx（电脑 IP）
   端口: 8899
3. 验证: 手机浏览器打开 https://www.baidu.com
   Whistle Network 面板出现请求 → 成功
```

### 每次数据更新

**Step 1: 抓包**
```
Whistle → Clear 清空 → 手机打开小程序 → 依次点进每个商家/窗口
```

**Step 2: 导出**
```
Whistle → Ctrl+A 全选 → 右键 → Export All → 存为 whistle.har
```

**Step 3: 转换**
```bash
python scripts/extract_har.py whistle.har
# → data/hnie/food/食堂指南.md
```

**Step 4: 入库**
```bash
python scripts/init_db.py --university hnie
```

### 脚本说明

| 脚本 | 用途 |
|---|---|
| `scripts/extract_har.py` | Whistle HAR → Markdown 知识库文件 |
| `scripts/decode_whistle.py` | 单个 JSON 响应解码预览 |
| `scripts/init_db.py` | Markdown → Chunk → Embedding → Chroma |
| `scripts/download_models.py` | 下载 BGE 嵌入/重排模型 |

### 抓包失败排查

| 症状 | 原因 | 解决 |
|---|---|---|
| 手机浏览器也抓不到 | 证书没装对 | 重新装为 CA 证书 |
| HTTP 能抓 HTTPS 不行 | HTTPS 没开启 | Whistle HTTPS 标签勾选 |
| 手机连不上代理 | 电脑防火墙/网线 | 拔网线连 WiFi |
| 小程序请求看不到 | 微信不走系统代理 | 用微信开发者工具 |
