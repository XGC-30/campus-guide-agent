"""
命令行交互界面 — 用于终端快速测试

用法:
  python -m app.cli                          # 使用默认配置
  python -m app.cli --university demo        # 指定大学
  python -m app.cli --init                   # 初始化向量数据库
  python -m app.cli --list-universities       # 列出所有已配置的大学
"""

import argparse
import sys
from pathlib import Path

# 确保项目根目录在 Python path 中
sys.path.insert(0, str(Path(__file__).parent.parent))

# Windows GBK 终端兼容：强制 UTF-8 输出
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from core.config import list_universities, load_config
from core.pipeline.rag_chain import CampusRAGPipeline

console = Console()


def cmd_init(university: str):
    """初始化向量数据库"""
    from core.ingest.splitter import CampusTextSplitter
    from core.ingest.markdown_loader import MarkdownLoader
    from core.retrieval.embedder import EmbedderFactory
    from core.retrieval.vector_store import VectorStoreFactory

    config = load_config(university)

    with console.status("📥 加载文档..."):
        loader = MarkdownLoader(data_dir="data")
        raw_docs = loader.load()
        console.print(f"  ✅ 加载了 {len(raw_docs)} 个文档")

    with console.status("✂️  切分文档..."):
        chunk_cfg = config.get("chunking", {})
        splitter = CampusTextSplitter(
            default_chunk_size=chunk_cfg.get("default", {}).get("chunk_size", 500),
            default_chunk_overlap=chunk_cfg.get("default", {}).get("chunk_overlap", 80),
            overrides=chunk_cfg.get("overrides", {}),
        )
        chunks = splitter.split(raw_docs)
        console.print(f"  ✅ 切分为 {len(chunks)} 个文档块")

    with console.status("🔢 向量化入库..."):
        emb_cfg = config["models"]["embedding"]
        embeddings = EmbedderFactory.create(
            model_name=emb_cfg["model_name"],
            device=emb_cfg.get("device", "cpu"),
            normalize=emb_cfg.get("normalize", True),
        )
        vs_cfg = config["vectorstore"]
        vs = VectorStoreFactory.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_dir=vs_cfg["persist_dir"],
            collection_name=vs_cfg.get("collection_name", "campus_knowledge"),
        )
        console.print(f"  ✅ 向量数据库已创建: {vs_cfg['persist_dir']}")

    console.print(Panel.fit(
        f"🎉 知识库初始化完成！\n"
        f"   - 大学：{config['university']['name']}\n"
        f"   - 原始文件：{len(raw_docs)} 个\n"
        f"   - 文档块：{len(chunks)} 个\n"
        f"   - 数据库路径：{vs_cfg['persist_dir']}",
        title="初始化报告",
        border_style="green",
    ))


def cmd_chat(university: str):
    """进入命令行对话模式"""
    console.print(Panel.fit(
        "🎓 校园新生指南 · 小园\n"
        "输入你的问题，我会尽力回答！\n"
        "按 Ctrl+C 退出",
        border_style="cyan",
    ))

    with console.status("🔄 加载 RAG 管道..."):
        pipeline = CampusRAGPipeline(university)
    console.print(f"✅ 已就绪 (LLM: {pipeline.llm})\n")

    while True:
        try:
            query = console.input("[bold cyan]你> [/bold cyan]")
            if not query.strip():
                continue
            if query.lower() in ("exit", "quit", "q", "退出"):
                console.print("👋 再见，祝你校园生活愉快！")
                break

            with console.status("🤔 思考中..."):
                response = pipeline.invoke(query)

            console.print()
            console.print(Markdown(f"**小园>** {response}"))
            console.print()

        except KeyboardInterrupt:
            console.print("\n👋 再见！")
            break
        except Exception as e:
            console.print(f"[red]⚠️ 出错了: {e}[/red]")


def cmd_list_universities():
    """列出所有已配置的大学"""
    universities = list_universities()
    if not universities:
        console.print("[yellow]⚠️ 没有找到大学配置文件[/yellow]")
        return

    table = Table(title="已配置的大学")
    table.add_column("配置 ID", style="cyan")
    table.add_column("配置文件路径", style="dim")

    for uni in universities:
        table.add_row(uni, f"config/universities/{uni}.yaml")

    console.print(table)
    console.print(f"\n共 {len(universities)} 所大学")


def main():
    parser = argparse.ArgumentParser(
        description="Campus Guide Agent - 校园新生指南 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                            # 进入聊天模式
  %(prog)s --init                     # 初始化知识库
  %(prog)s --university demo          # 指定大学
  %(prog)s --list-universities        # 列出所有大学
        """,
    )
    parser.add_argument("--university", "-u", type=str, default=None, help="大学配置 ID")
    parser.add_argument("--init", action="store_true", help="初始化向量数据库")
    parser.add_argument("--list-universities", "-l", action="store_true", help="列出所有大学")

    args = parser.parse_args()

    if args.list_universities:
        cmd_list_universities()
    elif args.init:
        cmd_init(args.university or "demo_university")
    else:
        cmd_chat(args.university or "demo_university")


if __name__ == "__main__":
    main()
