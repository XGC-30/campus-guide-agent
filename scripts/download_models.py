#!/usr/bin/env python
"""
下载所需模型 — BGE Embedding + BGE Re-ranker

使用方式:
  python scripts/download_models.py              # 下载全部
  python scripts/download_models.py --embed-only # 仅下载嵌入模型
  python scripts/download_models.py --rerank-only # 仅下载重排模型

模型列表:
  - BAAI/bge-large-zh-v1.5       (~1.3GB) 中文嵌入模型
  - BAAI/bge-reranker-v2-m3      (~1.1GB) 中文重排模型
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
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

EMBED_MODELS = [
    "BAAI/bge-large-zh-v1.5",
    "BAAI/bge-small-zh-v1.5",
]

RERANK_MODELS = [
    "BAAI/bge-reranker-v2-m3",
]


def download_embed_models(verbose: bool = False):
    """下载嵌入模型"""
    from sentence_transformers import SentenceTransformer

    for model_name in EMBED_MODELS:
        console.print(f"📥 下载嵌入模型: {model_name}")
        try:
            model = SentenceTransformer(model_name)
            console.print(f"  ✅ 完成 ({model.get_sentence_embedding_dimension()} 维)")
        except Exception as e:
            console.print(f"  ❌ 失败: {e}")

        if verbose:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            console.print(f"     设备: {device}")


def download_rerank_models():
    """下载重排模型"""
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    for model_name in RERANK_MODELS:
        console.print(f"📥 下载重排模型: {model_name}")
        try:
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSequenceClassification.from_pretrained(model_name)
            console.print(f"  ✅ 完成")
        except Exception as e:
            console.print(f"  ❌ 失败: {e}")


def check_ollama():
    """检查 Ollama 是否安装 + Qwen 模型是否已拉取"""
    import subprocess

    console.print("🔍 检查 Ollama ...")
    try:
        result = subprocess.run(
            ["ollama", "list"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            models = result.stdout
            console.print(f"  ✅ Ollama 已安装")
            if "qwen" in models.lower():
                console.print(f"  ✅ Qwen 模型已就绪")
            else:
                console.print(f"  ⚠️  Qwen 模型未拉取，请运行: ollama pull qwen2.5:7b")
        else:
            console.print(f"  ❌ Ollama 未运行，请先启动")
    except FileNotFoundError:
        console.print(f"  ⚠️  Ollama 未安装: https://ollama.com")
    except Exception as e:
        console.print(f"  ⚠️  检查失败: {e}")


def main():
    parser = argparse.ArgumentParser(description="下载所需模型")
    parser.add_argument("--embed-only", action="store_true")
    parser.add_argument("--rerank-only", action="store_true")
    parser.add_argument("--check", action="store_true", help="仅检查状态")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    console.print(f"[bold]Campus Guide Agent — 模型下载[/bold]\n")

    if args.check:
        check_ollama()
        return

    if not args.rerank_only:
        download_embed_models(args.verbose)
        console.print()

    if not args.embed_only:
        download_rerank_models()
        console.print()

    check_ollama()

    console.print(f"\n✅ 模型下载完成")


if __name__ == "__main__":
    main()
