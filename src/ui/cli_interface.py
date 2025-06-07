#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命令行界面模块
提供交互式命令行界面
"""

import cmd
import sys
from typing import Dict, Any
from pathlib import Path


class CLIInterface(cmd.Cmd):
    """命令行界面"""
    
    intro = """
🍾 欢迎使用 Bottle-Agent！

可用命令:
  search <查询>          - 搜索论文
  create_kb <名称> <路径> - 创建知识库
  list_kb               - 列出所有知识库
  query <知识库> <问题>   - RAG问答
  info <知识库>          - 查看知识库信息
  delete_kb <知识库>     - 删除知识库
  update_kb <知识库>     - 更新知识库
  config                - 查看配置
  help                  - 显示帮助
  quit                  - 退出

输入 'help <命令>' 查看详细帮助。
"""
    
    prompt = "(bottle-agent) "
    
    def __init__(self, search_engine, kb_manager, config):
        super().__init__()
        self.search_engine = search_engine
        self.kb_manager = kb_manager
        self.config = config
    
    def do_search(self, arg):
        """搜索论文: search <查询> [来源] [数量]
        
        示例:
          search diffusion models
          search "graph neural networks" arxiv 5
          search transformer semantic_scholar 10
        """
        if not arg.strip():
            print("❌ 请输入搜索查询")
            return
        
        parts = arg.split()
        query = parts[0] if len(parts) == 1 else ' '.join(parts[:-2]) if len(parts) > 2 else ' '.join(parts[:-1]) if len(parts) > 1 else arg
        source = "arxiv"
        max_results = None
        
        # 解析参数
        if len(parts) > 1:
            if parts[-1].isdigit():
                max_results = int(parts[-1])
                if len(parts) > 2:
                    source = parts[-2]
                    query = ' '.join(parts[:-2])
                else:
                    query = ' '.join(parts[:-1])
            elif parts[-1] in ["arxiv", "semantic_scholar"]:
                source = parts[-1]
                query = ' '.join(parts[:-1])
        
        print(f"🔍 搜索论文: {query}")
        print(f"📚 来源: {source}")
        if max_results:
            print(f"📊 最大结果数: {max_results}")
        print()
        
        try:
            results = self.search_engine.search(query, source, max_results)
            self.search_engine.display_results(results)
        except Exception as e:
            print(f"❌ 搜索失败: {e}")
    
    def do_create_kb(self, arg):
        """创建知识库: create_kb <名称> <文件夹路径> [描述]
        
        示例:
          create_kb llm /path/to/llm/papers "大语言模型相关论文"
          create_kb cv ~/papers/computer_vision
        """
        parts = arg.split()
        if len(parts) < 2:
            print("❌ 用法: create_kb <名称> <文件夹路径> [描述]")
            return
        
        name = parts[0]
        folder_path = parts[1]
        description = ' '.join(parts[2:]) if len(parts) > 2 else ""
        
        # 展开路径
        folder_path = Path(folder_path).expanduser().resolve()
        
        success = self.kb_manager.create_knowledge_base(name, str(folder_path), description)
        if success:
            print(f"\n✅ 知识库 '{name}' 创建成功！")
        else:
            print(f"\n❌ 知识库 '{name}' 创建失败")
    
    def do_list_kb(self, arg):
        """列出所有知识库: list_kb"""
        kb_list = self.kb_manager.list_knowledge_bases()
        
        if not kb_list:
            print("📭 没有找到知识库")
            return
        
        print(f"📚 共有 {len(kb_list)} 个知识库:\n")
        
        for kb_name in kb_list:
            kb_info = self.kb_manager.get_knowledge_base_info(kb_name)
            if kb_info:
                print(f"🔸 {kb_name}")
                print(f"   📝 描述: {kb_info.description or '无描述'}")
                print(f"   📁 路径: {kb_info.folder_path}")
                print(f"   📊 文档数: {kb_info.document_count}, 块数: {kb_info.chunk_count}")
                print(f"   📅 创建时间: {kb_info.created_at[:19]}")
                print()
    
    def do_query(self, arg):
        """RAG问答: query <知识库名称> <问题>
        
        示例:
          query llm "什么是transformer架构？"
          query cv 图像分类的最新方法有哪些
        """
        parts = arg.split(maxsplit=1)
        if len(parts) < 2:
            print("❌ 用法: query <知识库名称> <问题>")
            return
        
        kb_name = parts[0]
        question = parts[1].strip('"\'')
        
        print(f"🧠 知识库: {kb_name}")
        print(f"❓ 问题: {question}")
        print("\n🤔 思考中...\n")
        
        try:
            answer = self.kb_manager.query(kb_name, question)
            print("📝 回答:")
            print("=" * 50)
            print(answer)
            print("=" * 50)
        except Exception as e:
            print(f"❌ 查询失败: {e}")
    
    def do_info(self, arg):
        """查看知识库信息: info <知识库名称>
        
        示例:
          info llm
        """
        if not arg.strip():
            print("❌ 请指定知识库名称")
            return
        
        kb_name = arg.strip()
        kb_info = self.kb_manager.get_knowledge_base_info(kb_name)
        
        if not kb_info:
            print(f"❌ 知识库 '{kb_name}' 不存在")
            return
        
        print(f"📚 知识库信息: {kb_name}")
        print("=" * 40)
        print(f"📝 描述: {kb_info.description or '无描述'}")
        print(f"📁 文件夹路径: {kb_info.folder_path}")
        print(f"📊 文档数量: {kb_info.document_count}")
        print(f"🧩 文档块数量: {kb_info.chunk_count}")
        print(f"📅 创建时间: {kb_info.created_at}")
        print(f"🔄 更新时间: {kb_info.updated_at}")
        print("=" * 40)
    
    def do_delete_kb(self, arg):
        """删除知识库: delete_kb <知识库名称>
        
        示例:
          delete_kb old_kb
        """
        if not arg.strip():
            print("❌ 请指定知识库名称")
            return
        
        kb_name = arg.strip()
        
        # 确认删除
        confirm = input(f"⚠️  确定要删除知识库 '{kb_name}' 吗？(y/N): ")
        if confirm.lower() not in ['y', 'yes']:
            print("❌ 取消删除")
            return
        
        success = self.kb_manager.delete_knowledge_base(kb_name)
        if success:
            print(f"✅ 知识库 '{kb_name}' 删除成功")
        else:
            print(f"❌ 知识库 '{kb_name}' 删除失败")
    
    def do_update_kb(self, arg):
        """更新知识库: update_kb <知识库名称>
        
        示例:
          update_kb llm
        """
        if not arg.strip():
            print("❌ 请指定知识库名称")
            return
        
        kb_name = arg.strip()
        
        print(f"🔄 更新知识库: {kb_name}")
        success = self.kb_manager.update_knowledge_base(kb_name)
        if success:
            print(f"✅ 知识库 '{kb_name}' 更新成功")
        else:
            print(f"❌ 知识库 '{kb_name}' 更新失败")
    
    def do_config(self, arg):
        """查看配置信息: config"""
        print("⚙️  当前配置:")
        print("=" * 40)
        print(f"🤖 LLM提供商: {self.config['llm']['provider']}")
        print(f"🤖 LLM模型: {self.config['llm']['model']}")
        print(f"🧮 嵌入提供商: {self.config['embedding']['provider']}")
        print(f"🧮 嵌入模型: {self.config['embedding']['model']}")
        print(f"📚 向量数据库: {self.config['rag']['vector_db']['provider']}")
        print(f"📊 块大小: {self.config['rag']['chunk_size']}")
        print(f"🔍 Top-K: {self.config['rag']['top_k']}")
        print(f"📁 知识库存储路径: {self.config['knowledge_base']['storage_path']}")
        print("=" * 40)
    
    def do_quit(self, arg):
        """退出程序: quit"""
        print("👋 再见！")
        return True
    
    def do_exit(self, arg):
        """退出程序: exit"""
        return self.do_quit(arg)
    
    def do_EOF(self, arg):
        """处理Ctrl+D"""
        print("\n👋 再见！")
        return True
    
    def emptyline(self):
        """处理空行"""
        pass
    
    def default(self, line):
        """处理未知命令"""
        print(f"❌ 未知命令: {line}")
        print("输入 'help' 查看可用命令")
    
    def run(self):
        """运行命令行界面"""
        try:
            self.cmdloop()
        except KeyboardInterrupt:
            print("\n👋 再见！")
        except Exception as e:
            print(f"❌ 程序错误: {e}")
            sys.exit(1)