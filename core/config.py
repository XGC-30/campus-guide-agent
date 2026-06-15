"""
配置加载器 — 支持多层配置合并（默认 → 大学 → 环境变量）
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv

load_dotenv()

# 项目根目录
ROOT_DIR = Path(__file__).parent.parent


def _resolve_env_vars(value: Any) -> Any:
    """递归解析字符串中的 ${ENV_VAR} 占位符"""
    if isinstance(value, str):
        pattern = re.compile(r"\$\{(\w+)\}")
        matches = pattern.findall(value)
        for var in matches:
            env_val = os.environ.get(var, "")
            value = value.replace(f"${{{var}}}", env_val)
        return value
    elif isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_resolve_env_vars(v) for v in value]
    return value


def _deep_merge(base: dict, override: dict) -> dict:
    """深度合并两个字典，override 覆盖 base"""
    result = base.copy()
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def load_config(university: Optional[str] = None) -> Dict[str, Any]:
    """
    加载配置（优先级从低到高）：
    1. config/default.yaml — 框架默认值
    2. config/universities/<name>.yaml — 大学特定配置
    3. 环境变量 — .env 文件
    """
    # 加载默认配置
    default_path = ROOT_DIR / "config" / "default.yaml"
    if not default_path.exists():
        raise FileNotFoundError(f"默认配置不存在: {default_path}")

    with open(default_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 加载大学特定配置
    uni_name = university or os.environ.get("CGA_UNIVERSITY", "demo_university")
    uni_path = ROOT_DIR / "config" / "universities" / f"{uni_name}.yaml"

    if uni_path.exists():
        with open(uni_path, "r", encoding="utf-8") as f:
            uni_config = yaml.safe_load(f)
        config = _deep_merge(config, uni_config)
    else:
        # 不抛异常，降级使用默认配置
        import warnings
        warnings.warn(f"大学配置 '{uni_name}.yaml' 不存在，使用默认配置")

    # 解析环境变量占位符
    config = _resolve_env_vars(config)

    # LLM mode 环境变量覆盖
    llm_mode = os.environ.get("CGA_LLM_MODE")
    if llm_mode:
        config["models"]["llm"]["mode"] = llm_mode

    return config


def list_universities() -> list[str]:
    """列出所有已配置的大学"""
    uni_dir = ROOT_DIR / "config" / "universities"
    if not uni_dir.exists():
        return []
    return [
        p.stem for p in uni_dir.glob("*.yaml")
        if p.stem not in ("default", "schema")
    ]
