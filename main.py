#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bottle-Agent: 轻量学术搜索与RAG agent
主入口文件，支持命令行快速启动
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config.settings import load_config
from src.paper_search.search_engine import PaperSearchEngine
from src.rag_system.knowledge_base import KnowledgeBaseManager
from src.llm.llm_client import LLMClient
from src.rag_system.embedding_client import EmbeddingClient
from src.ui.cli_interface import CLIInterface
try:
    from src.ui.web_interface import run_streamlit_app
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False
    print("⚠️  Streamlit未安装，Web界面不可用")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Bottle-Agent: 轻量学术搜索与RAG agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python main.py --mode cli                    # 启动命令行界面
  python main.py --mode web                    # 启动Web界面
  python main.py --search "diffusion models"   # 直接搜索论文
  python main.py --rag --kb llm --query "什么是transformer"  # RAG问答
        """
    )
    
    # 运行模式
    parser.add_argument(
        "--mode", 
        choices=["cli", "web"], 
        default="cli",
        help="运行模式: cli(命令行) 或 web(网页界面)"
    )
    
    # 论文搜索功能
    parser.add_argument(
        "--search", 
        type=str,
        help="直接搜索论文，输入查询关键词"
    )
    
    # RAG功能
    parser.add_argument(
        "--rag", 
        action="store_true",
        help="启用RAG问答模式"
    )
    
    parser.add_argument(
        "--kb", 
        type=str,
        help="指定知识库名称（用于RAG模式）"
    )
    
    parser.add_argument(
        "--query", 
        type=str,
        help="RAG问答查询内容"
    )
    
    # 知识库管理
    parser.add_argument(
        "--create-kb", 
        type=str,
        help="创建新知识库，指定知识库名称"
    )
    
    parser.add_argument(
        "--kb-path", 
        type=str,
        help="知识库对应的文件夹路径"
    )
    
    parser.add_argument(
        "--list-kb", 
        action="store_true",
        help="列出所有知识库"
    )
    
    # 配置选项
    parser.add_argument(
        "--config", 
        type=str,
        default="config/config.yaml",
        help="配置文件路径"
    )
    
    args = parser.parse_args()
    
    # 加载配置
    config = load_config(args.config)
    
    # 初始化组件
    search_engine = PaperSearchEngine(config)
    kb_manager = KnowledgeBaseManager(config)
    
    try:
        # 处理直接搜索
        if args.search:
            print(f"🔍 搜索论文: {args.search}")
            results = search_engine.search(args.search)
            search_engine.display_results(results)
            return
        
        # 处理RAG问答
        if args.rag:
            if not args.kb or not args.query:
                print("❌ RAG模式需要指定知识库(--kb)和查询内容(--query)")
                return
            
            print(f"🧠 RAG问答 - 知识库: {args.kb}, 查询: {args.query}")
            answer = kb_manager.query(args.kb, args.query)
            print(f"\n📝 回答:\n{answer}")
            return
        
        # 处理知识库管理
        if args.create_kb:
            if not args.kb_path:
                print("❌ 创建知识库需要指定文件夹路径(--kb-path)")
                return
            
            print(f"📚 创建知识库: {args.create_kb} -> {args.kb_path}")
            kb_manager.create_knowledge_base(args.create_kb, args.kb_path)
            print("✅ 知识库创建完成")
            return
        
        if args.list_kb:
            print("📚 已有知识库:")
            kb_list = kb_manager.list_knowledge_bases()
            for kb in kb_list:
                print(f"  - {kb}")
            return
        
        # 启动交互界面
        if args.mode == "web":
            run_web_interface(config)
        else:
            print("💻 启动命令行界面...")
            cli = CLIInterface(search_engine, kb_manager, config)
            cli.run()
            
    except KeyboardInterrupt:
        print("\n👋 再见！")
    except Exception as e:
        print(f"❌ 错误: {e}")
        if config.get('debug', False):
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()