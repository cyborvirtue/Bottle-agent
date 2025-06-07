#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any


def load_config(config_path: str = None) -> Dict[str, Any]:
    """加载配置文件
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        配置字典
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
    
    config_path = Path(config_path)
    
    # 默认配置
    default_config = {
        "llm": {
            "provider": "openai",  # openai, anthropic, local
            "model": "gpt-3.5-turbo",
            "api_key": os.getenv("OPENAI_API_KEY"),
            "base_url": None,
            "temperature": 0.7,
            "max_tokens": 2000
        },
        "embedding": {
            "provider": "openai",  # openai, huggingface, local
            "model": "text-embedding-ada-002",
            "api_key": os.getenv("OPENAI_API_KEY"),
            "base_url": None
        },
        "paper_search": {
            "arxiv": {
                "base_url": "http://export.arxiv.org/api/query",
                "max_results": 10,
                "sort_by": "relevance",  # relevance, lastUpdatedDate, submittedDate
                "sort_order": "descending"
            },
            "semantic_scholar": {
                "base_url": "https://api.semanticscholar.org/graph/v1",
                "api_key": os.getenv("SEMANTIC_SCHOLAR_API_KEY"),
                "max_results": 10
            }
        },
        "rag": {
            "vector_db": {
                "provider": "faiss",  # faiss, chroma
                "storage_path": "data/vector_db"
            },
            "chunk_size": 1000,
            "chunk_overlap": 200,
            "top_k": 5,
            "similarity_threshold": 0.7
        },
        "knowledge_base": {
            "storage_path": "data/knowledge_bases",
            "supported_formats": [".pdf", ".txt", ".md", ".docx"]
        },
        "ui": {
            "web": {
                "host": "127.0.0.1",
                "port": 8501,
                "debug": False
            }
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file": "logs/bottle_agent.log"
        },
        "debug": False
    }
    
    # 如果配置文件存在，加载并合并
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = yaml.safe_load(f) or {}
            
            # 递归合并配置
            config = merge_configs(default_config, user_config)
        except Exception as e:
            print(f"⚠️  配置文件加载失败，使用默认配置: {e}")
            config = default_config
    else:
        print(f"⚠️  配置文件不存在: {config_path}，使用默认配置")
        config = default_config
    
    # 创建必要的目录
    create_directories(config)
    
    return config


def merge_configs(default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """递归合并配置字典
    
    Args:
        default: 默认配置
        user: 用户配置
        
    Returns:
        合并后的配置
    """
    result = default.copy()
    
    for key, value in user.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    
    return result


def create_directories(config: Dict[str, Any]) -> None:
    """创建必要的目录
    
    Args:
        config: 配置字典
    """
    directories = [
        config["rag"]["vector_db"]["storage_path"],
        config["knowledge_base"]["storage_path"],
        Path(config["logging"]["file"]).parent
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)


def save_config(config: Dict[str, Any], config_path: str = None) -> None:
    """保存配置到文件
    
    Args:
        config: 配置字典
        config_path: 配置文件路径
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
    
    config_path = Path(config_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, indent=2)