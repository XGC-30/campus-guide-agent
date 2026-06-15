#!/usr/bin/env python
"""
初始化向量数据库 — 将 Markdown 知识文件入库

使用方式:
  python scripts/init_db.py                          # 使用 demo_university
  python scripts/init_db.py --university my_uni      # 指定大学
  python scripts/init_db.py --verbose                # 显示详细信息
  python scripts/init_db.py --reset                  # 清空旧库重新入库

工作流程:
  1. 加载 data/ 目录下所有 .md 文件
  2. 两轮切分（标题 + 字符级）
  3. 向量化（BGE Embedding）
  4. 存入 Chroma 向量数据库
"""

import argparse
import shutil
import sys
from pathlib import Path

# 确保项目根目录在 Python path 中
sys.path.insert(0, str(Path(__file__).parent.parent))

# Windows GBK 终端兼容：强制 UTF-8 输出
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.panel import Panel

from core.config import load_config
from core.ingest.markdown_loader import MarkdownLoader
from core.ingest.splitter import CampusTextSplitter
from core.retrieval.embedder import EmbedderFactory
from core.retrieval.vector_store import VectorStoreFactory

console = Console()


def main():
    parser = argparse.ArgumentParser(description="初始化校园知识向量数据库")
    parser.add_argument("--university", "-u", type=str, default="demo_university")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--reset", "-r", action="store_true", help="清空旧库")
    parser.add_argument("--data-dir", "-d", type=str, default="data")
    args = parser.parse_args()

    console.print(Panel.fit(
        "🏗️  Campus Guide Agent — 知识库初始化",
        border_style="blue",
    ))

    # ── 加载配置 ──
    config = load_config(args.university)
    uni_name = config["university"]["name"]
    console.print(f"🏫 大学: {uni_name}")
    console.print(f"📂 数据目录: {args.data_dir}")

    # ── 如果 reset，删除旧库 ──
    persist_dir = config["vectorstore"]["persist_dir"]
    if args.reset and Path(persist_dir).exists():
        shutil.rmtree(persist_dir)
        console.print(f"🗑️  已清空旧数据库: {persist_dir}")

    # ── Step 1: 加载文档 ──
    console.print("\n[bold]Step 1/3:[/bold] 加载 Markdown 文档")
    loader = MarkdownLoader(data_dir=args.data_dir)
    raw_docs = loader.load()
    console.print(f"  ✅ 加载了 [cyan]{len(raw_docs)}[/cyan] 个文件")

    if args.verbose:
        for doc in raw_docs:
            source = doc.metadata.get("source_name", "?")
            category = doc.metadata.get("category", "?")
            size = len(doc.page_content)
            console.print(f"     📄 {source} [{category}] ({size} 字符)")

    # ── Step 2: 切分文档 ──
    console.print("\n[bold]Step 2/3:[/bold] 切分文档")
    chunk_cfg = config.get("chunking", {})
    splitter = CampusTextSplitter(
        default_chunk_size=chunk_cfg.get("default", {}).get("chunk_size", 500),
        default_chunk_overlap=chunk_cfg.get("default", {}).get("chunk_overlap", 80),
        overrides=chunk_cfg.get("overrides", {}),
    )
    chunks = splitter.split(raw_docs)
    console.print(f"  ✅ 切分为 [cyan]{len(chunks)}[/cyan] 个文档块")

    if args.verbose:
        # 按分类统计
        from collections import Counter
        cat_counts = Counter(c.metadata.get("category", "未知") for c in chunks)
        for cat, count in cat_counts.most_common():
            console.print(f"     📦 {cat}: {count} 块")

    # ── Step 3: 向量化入库 ──
    console.print("\n[bold]Step 3/3:[/bold] 向量化并存入数据库")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("加载嵌入模型...", total=None)
        emb_cfg = config["models"]["embedding"]
        embeddings = EmbedderFactory.create(
            model_name=emb_cfg["model_name"],
            device=emb_cfg.get("device", "cpu"),
            normalize=emb_cfg.get("normalize", True),
        )
        progress.update(task, description=f"  模型: {emb_cfg['model_name']}")

        task2 = progress.add_task("向量化文档...", total=None)
        vs_cfg = config["vectorstore"]
        vectorstore = VectorStoreFactory.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_dir=persist_dir,
            collection_name=vs_cfg.get("collection_name", "campus_knowledge"),
        )
        progress.update(task2, description=f"  ✅ 已存入 {len(chunks)} 个向量")

    # ── 完成报告 ──
    console.print()
    console.print(Panel.fit(
        f"[bold green]🎉 知识库初始化完成[/bold green]\n\n"
        f"  🏫 大学: [cyan]{uni_name}[/cyan]\n"
        f"  📄 原始文件: [cyan]{len(raw_docs)}[/cyan] 个\n"
        f"  ✂️  文档块: [cyan]{len(chunks)}[/cyan] 个\n"
        f"  💾 数据库路径: [cyan]{persist_dir}[/cyan]\n"
        f"  🔤 嵌入模型: [cyan]{emb_cfg['model_name']}[/cyan]\n\n"
        f"[dim]下一步: streamlit run app/webui.py[/dim]",
        border_style="green",
    ))

    # 统计表
    table = Table(title="分类统计")
    table.add_column("分类", style="cyan")
    table.add_column("文档块数", justify="right")

    from collections import Counter
    for cat, count in Counter(c.metadata.get("category", "未知") for c in chunks).most_common():
        table.add_row(cat, str(count))
    console.print(table)


if __name__ == "__main__":
    main()
