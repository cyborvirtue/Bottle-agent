#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG知识库管理模块
支持多知识库管理、文档处理、向量检索
"""

import os
import json
import pickle
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import logging
from datetime import datetime

import faiss
import numpy as np
from dataclasses import dataclass, asdict

from .data_structures import DocumentChunk, Document
from .document_processor import DocumentProcessor
from .embedding_client import EmbeddingClient
from .agent_manager import AgentManager
from ..llm.llm_client import LLMClient


@dataclass
class KnowledgeBaseInfo:
    """知识库信息"""
    name: str
    description: str
    folder_path: str
    created_at: str
    updated_at: str
    document_count: int
    chunk_count: int


class KnowledgeBaseManager:
    """知识库管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.rag_config = config["rag"]
        self.kb_config = config["knowledge_base"]
        
        # 初始化组件
        self.document_processor = DocumentProcessor(config)
        self.embedding_client = EmbeddingClient(config)
        self.llm_client = LLMClient(config)
        
        # 存储路径
        self.storage_path = Path(self.kb_config["storage_path"])
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化Agent管理器
        self.agent_manager = AgentManager(str(self.storage_path / "agents"))
        
        # 加载预设Agent配置
        try:
            presets_file = str(self.storage_path.parent / "examples" / "agent_presets.json")
            self.agent_manager.load_presets(presets_file)
        except Exception as e:
            logging.warning(f"⚠️ 加载预设Agent配置失败: {e}")
        
        # 知识库索引文件
        self.index_file = self.storage_path / "knowledge_bases.json"
        
        # 加载知识库索引
        self.knowledge_bases = self._load_knowledge_bases_index()
    
    def _safe_kb_name(self, kb_name: str) -> str:
        """将知识库名称转换为安全的文件夹名称
        
        Args:
            kb_name: 原始知识库名称
            
        Returns:
            安全的文件夹名称
        """
        # 替换不安全的字符
        safe_name = kb_name.replace('/', '_').replace('\\', '_').replace(':', '_')
        safe_name = safe_name.replace('<', '_').replace('>', '_').replace('|', '_')
        safe_name = safe_name.replace('?', '_').replace('*', '_').replace('"', '_')
        return safe_name
    
    def _load_knowledge_bases_index(self) -> Dict[str, KnowledgeBaseInfo]:
        """加载知识库索引
        
        Returns:
            知识库索引字典
        """
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 转换为KnowledgeBaseInfo对象
                knowledge_bases = {}
                for name, info in data.items():
                    knowledge_bases[name] = KnowledgeBaseInfo(**info)
                
                return knowledge_bases
            except Exception as e:
                logging.error(f"加载知识库索引失败: {e}")
        
        return {}
    
    def _save_knowledge_bases_index(self):
        """保存知识库索引"""
        try:
            # 转换为字典格式
            data = {}
            for name, info in self.knowledge_bases.items():
                data[name] = asdict(info)
            
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"保存知识库索引失败: {e}")
    
    def create_knowledge_base(self, name: str, folder_path: str, description: str = "") -> bool:
        """创建知识库
        
        Args:
            name: 知识库名称
            folder_path: 文档文件夹路径
            description: 知识库描述
            
        Returns:
            是否创建成功
        """
        if name in self.knowledge_bases:
            print(f"❌ 知识库 '{name}' 已存在")
            return False
        
        folder_path = Path(folder_path)
        if not folder_path.exists():
            print(f"❌ 文件夹路径不存在: {folder_path}")
            return False
        
        print(f"📚 创建知识库: {name}")
        print(f"📁 文档路径: {folder_path}")
        
        try:
            # 创建知识库目录（使用安全的文件夹名称）
            safe_name = self._safe_kb_name(name)
            kb_path = self.storage_path / safe_name
            kb_path.mkdir(exist_ok=True)
            
            # 处理文档
            print("📄 处理文档...")
            documents = self.document_processor.process_folder(str(folder_path))
            
            if not documents:
                print("⚠️  没有找到可处理的文档")
                return False
            
            # 分块
            print("✂️  文档分块...")
            chunks = self.document_processor.chunk_documents(documents)
            
            # 生成嵌入
            print("🧮 生成嵌入向量...")
            embeddings = self.embedding_client.embed_texts([chunk.content for chunk in chunks])
            
            # 添加嵌入到块中
            for chunk, embedding in zip(chunks, embeddings):
                chunk.embedding = embedding
            
            # 构建向量索引
            print("🔍 构建向量索引...")
            self._build_vector_index(safe_name, chunks)
            
            # 保存块数据
            self._save_chunks(safe_name, chunks)
            
            # 更新知识库信息
            kb_info = KnowledgeBaseInfo(
                name=name,
                description=description,
                folder_path=str(folder_path),
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                document_count=len(documents),
                chunk_count=len(chunks)
            )
            
            self.knowledge_bases[name] = kb_info
            self._save_knowledge_bases_index()
            
            print(f"✅ 知识库 '{name}' 创建成功")
            print(f"   📊 文档数: {len(documents)}, 块数: {len(chunks)}")
            
            return True
        
        except Exception as e:
            logging.error(f"创建知识库失败: {e}")
            print(f"❌ 创建知识库失败: {e}")
            return False
    
    def _build_vector_index(self, kb_name: str, chunks: List[DocumentChunk]):
        """构建向量索引
        
        Args:
            kb_name: 知识库名称
            chunks: 文档块列表
        """
        if not chunks:
            return
        
        # 获取嵌入维度
        embedding_dim = len(chunks[0].embedding)
        
        # 创建FAISS索引
        index = faiss.IndexFlatIP(embedding_dim)  # 内积相似度
        
        # 添加向量
        embeddings = np.array([chunk.embedding for chunk in chunks]).astype('float32')
        
        # 归一化向量（用于余弦相似度）
        faiss.normalize_L2(embeddings)
        
        index.add(embeddings)
        
        # 保存索引
        index_path = self.storage_path / kb_name / "vector_index.faiss"
        faiss.write_index(index, str(index_path))
    
    def _save_chunks(self, kb_name: str, chunks: List[DocumentChunk]):
        """保存文档块
        
        Args:
            kb_name: 知识库名称
            chunks: 文档块列表
        """
        chunks_path = self.storage_path / kb_name / "chunks.pkl"
        
        # 保存时不包含嵌入向量（太大）
        chunks_to_save = []
        for chunk in chunks:
            chunk_copy = DocumentChunk(
                id=chunk.id,
                content=chunk.content,
                metadata=chunk.metadata
            )
            chunks_to_save.append(chunk_copy)
        
        with open(chunks_path, 'wb') as f:
            pickle.dump(chunks_to_save, f)
    
    def _load_chunks(self, kb_name: str) -> List[DocumentChunk]:
        """加载文档块
        
        Args:
            kb_name: 知识库名称
            
        Returns:
            文档块列表
        """
        chunks_path = self.storage_path / kb_name / "chunks.pkl"
        
        if not chunks_path.exists():
            return []
        
        with open(chunks_path, 'rb') as f:
            return pickle.load(f)
    
    def _load_vector_index(self, kb_name: str):
        """加载向量索引
        
        Args:
            kb_name: 知识库名称
            
        Returns:
            FAISS索引
        """
        index_path = self.storage_path / kb_name / "vector_index.faiss"
        
        if not index_path.exists():
            return None
        
        return faiss.read_index(str(index_path))
    
    def query(self, kb_name: str, query: str, top_k: int = None) -> str:
        """查询知识库
        
        Args:
            kb_name: 知识库名称
            query: 查询问题
            top_k: 返回的相关块数量
            
        Returns:
            回答
        """
        if kb_name not in self.knowledge_bases:
            return f"❌ 知识库 '{kb_name}' 不存在"
        
        if top_k is None:
            top_k = self.rag_config["top_k"]
        
        try:
            # 加载索引和块
            index = self._load_vector_index(kb_name)
            chunks = self._load_chunks(kb_name)
            
            if index is None or not chunks:
                return f"❌ 知识库 '{kb_name}' 数据不完整"
            
            # 生成查询嵌入
            query_embedding = self.embedding_client.embed_text(query)
            query_vector = np.array([query_embedding]).astype('float32')
            faiss.normalize_L2(query_vector)
            
            # 搜索相似块
            scores, indices = index.search(query_vector, top_k)
            
            # 获取相关块
            relevant_chunks = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if score >= self.rag_config["similarity_threshold"]:
                    chunk = chunks[idx]
                    relevant_chunks.append((chunk, score))
            
            if not relevant_chunks:
                return "❌ 没有找到相关内容"
            
            # 构建上下文
            context = "\n\n".join([
                f"[文档片段 {i+1}]\n{chunk.content}\n来源: {chunk.metadata.get('source', '未知')}"
                for i, (chunk, _) in enumerate(relevant_chunks)
            ])
            
            # 生成回答
            prompt = f"""
基于以下文档内容回答用户问题。请确保回答准确、详细，并引用相关的文档片段。

用户问题: {query}

相关文档内容:
{context}

请基于上述文档内容回答问题，并在回答末尾列出参考的文档片段编号。

回答:
"""
            
            answer = self.llm_client.generate(prompt)
            
            # 添加引用信息
            references = "\n\n📚 参考文档:\n"
            for i, (chunk, score) in enumerate(relevant_chunks):
                source = chunk.metadata.get('source', '未知')
                page = chunk.metadata.get('page', '')
                page_info = f", 第{page}页" if page else ""
                references += f"[{i+1}] {source}{page_info} (相似度: {score:.3f})\n"
            
            return answer + references
        
        except Exception as e:
            logging.error(f"查询知识库失败: {e}")
            return f"❌ 查询失败: {e}"
    
    def query_stream(self, kb_name: str, query: str, top_k: int = 5):
        """流式查询知识库
        
        Args:
            kb_name: 知识库名称
            query: 查询问题
            top_k: 返回的相关文档数量
            
        Yields:
            生成的回答片段
        """
        if kb_name not in self.knowledge_bases:
            yield f"❌ 知识库 '{kb_name}' 不存在"
            return
        
        try:
            # 调试信息：显示知识库查询详情
            print(f"🔍 [DEBUG] 查询知识库: '{kb_name}'")
            print(f"🔍 [DEBUG] 可用知识库列表: {list(self.knowledge_bases.keys())}")
            print(f"🔍 [DEBUG] 知识库是否存在于索引中: {kb_name in self.knowledge_bases}")
            
            # 加载知识库（使用安全的文件夹名称）
            safe_name = self._safe_kb_name(kb_name)
            print(f"🔍 [DEBUG] 安全文件夹名称: '{safe_name}'")
            
            kb_path = self.storage_path / safe_name
            print(f"🔍 [DEBUG] 知识库路径: {kb_path}")
            print(f"🔍 [DEBUG] 知识库路径是否存在: {kb_path.exists()}")
            
            # 加载向量索引
            index_path = kb_path / "vector_index.faiss"  # 修正文件名
            print(f"🔍 [DEBUG] 向量索引路径: {index_path}")
            print(f"🔍 [DEBUG] 向量索引是否存在: {index_path.exists()}")
            
            if not index_path.exists():
                # 尝试旧的文件名
                old_index_path = kb_path / "index.faiss"
                print(f"🔍 [DEBUG] 尝试旧索引路径: {old_index_path}")
                print(f"🔍 [DEBUG] 旧索引路径是否存在: {old_index_path.exists()}")
                
                if old_index_path.exists():
                    index_path = old_index_path
                else:
                    yield f"❌ 知识库 '{kb_name}' 索引不存在\n调试信息: 安全名称='{safe_name}', 路径={kb_path}"
                    return
            
            index = faiss.read_index(str(index_path))
            print(f"🔍 [DEBUG] 成功加载向量索引，维度: {index.d}, 向量数: {index.ntotal}")
            
            # 加载文档块
            chunks_path = kb_path / "chunks.pkl"
            print(f"🔍 [DEBUG] 文档块路径: {chunks_path}")
            print(f"🔍 [DEBUG] 文档块是否存在: {chunks_path.exists()}")
            
            if not chunks_path.exists():
                yield f"❌ 知识库 '{kb_name}' 文档块不存在\n调试信息: 路径={chunks_path}"
                return
            
            with open(chunks_path, 'rb') as f:
                chunks = pickle.load(f)
            
            # 生成查询向量
            query_embedding = self.embedding_client.embed_text(query)
            query_vector = np.array([query_embedding], dtype=np.float32)
            
            # 搜索相似文档
            scores, indices = index.search(query_vector, top_k)
            
            # 获取相关文档块
            relevant_chunks = []
            for i, idx in enumerate(indices[0]):
                if idx < len(chunks):
                    relevant_chunks.append((chunks[idx], scores[0][i]))
            
            if not relevant_chunks:
                yield "❌ 没有找到相关文档"
                return
            
            # 构建上下文
            context = "\n\n".join([
                f"[文档片段 {i+1}]\n{chunk.content}\n来源: {chunk.metadata.get('source', '未知')}"
                for i, (chunk, _) in enumerate(relevant_chunks)
            ])
            
            # 生成回答
            prompt = f"""
基于以下文档内容回答用户问题。请确保回答准确、详细，并引用相关的文档片段。

用户问题: {query}

相关文档内容:
{context}

请基于上述文档内容回答问题，并在回答末尾列出参考的文档片段编号。

回答:
"""
            
            # 流式生成回答
            answer_parts = []
            for chunk in self.llm_client.generate_stream(prompt):
                answer_parts.append(chunk)
                yield chunk
            
            # 添加引用信息
            references = "\n\n📚 参考文档:\n"
            for i, (chunk, score) in enumerate(relevant_chunks):
                source = chunk.metadata.get('source', '未知')
                page = chunk.metadata.get('page', '')
                page_info = f", 第{page}页" if page else ""
                references += f"[{i+1}] {source}{page_info} (相似度: {score:.3f})\n"
            
            yield references
        
        except Exception as e:
            logging.error(f"流式查询知识库失败: {e}")
            yield f"❌ 查询失败: {e}"
    
    def query_stream_with_context(self, kb_name: str, query: str, chat_history: List[Dict[str, str]], top_k: int = 5, agent_name: str = "默认助手"):
        """基于对话历史的流式查询知识库
        
        Args:
            kb_name: 知识库名称
            query: 查询问题
            chat_history: 对话历史，格式为[{"role": "user/assistant", "content": "..."}]
            top_k: 返回的相关文档数量
            
        Yields:
            生成的回答片段
        """
        if kb_name not in self.knowledge_bases:
            yield f"❌ 知识库 '{kb_name}' 不存在"
            return
        
        try:
            # 调试信息：显示知识库查询详情
            print(f"🔍 [DEBUG] 查询知识库: '{kb_name}'")
            print(f"🔍 [DEBUG] 可用知识库列表: {list(self.knowledge_bases.keys())}")
            print(f"🔍 [DEBUG] 知识库是否存在于索引中: {kb_name in self.knowledge_bases}")
            
            # 加载知识库（使用安全的文件夹名称）
            safe_name = self._safe_kb_name(kb_name)
            print(f"🔍 [DEBUG] 安全文件夹名称: '{safe_name}'")
            
            kb_path = self.storage_path / safe_name
            print(f"🔍 [DEBUG] 知识库路径: {kb_path}")
            print(f"🔍 [DEBUG] 知识库路径是否存在: {kb_path.exists()}")
            
            # 加载向量索引
            index_path = kb_path / "vector_index.faiss"  # 修正文件名
            print(f"🔍 [DEBUG] 向量索引路径: {index_path}")
            print(f"🔍 [DEBUG] 向量索引是否存在: {index_path.exists()}")
            
            if not index_path.exists():
                # 尝试旧的文件名
                old_index_path = kb_path / "index.faiss"
                print(f"🔍 [DEBUG] 尝试旧索引路径: {old_index_path}")
                print(f"🔍 [DEBUG] 旧索引路径是否存在: {old_index_path.exists()}")
                
                if old_index_path.exists():
                    index_path = old_index_path
                else:
                    yield f"❌ 知识库 '{kb_name}' 索引不存在\n调试信息: 安全名称='{safe_name}', 路径={kb_path}"
                    return
            
            index = faiss.read_index(str(index_path))
            print(f"🔍 [DEBUG] 成功加载向量索引，维度: {index.d}, 向量数: {index.ntotal}")
            
            # 加载文档块
            chunks_path = kb_path / "chunks.pkl"
            print(f"🔍 [DEBUG] 文档块路径: {chunks_path}")
            print(f"🔍 [DEBUG] 文档块是否存在: {chunks_path.exists()}")
            
            if not chunks_path.exists():
                yield f"❌ 知识库 '{kb_name}' 文档块不存在\n调试信息: 路径={chunks_path}"
                return
            
            with open(chunks_path, 'rb') as f:
                chunks = pickle.load(f)
            
            # 生成查询向量
            query_embedding = self.embedding_client.embed_text(query)
            query_vector = np.array([query_embedding], dtype=np.float32)
            
            # 搜索相似文档
            scores, indices = index.search(query_vector, top_k)
            
            # 获取相关文档块
            relevant_chunks = []
            for i, idx in enumerate(indices[0]):
                if idx < len(chunks):
                    relevant_chunks.append((chunks[idx], scores[0][i]))
            
            if not relevant_chunks:
                yield "❌ 没有找到相关文档"
                return
            
            # 构建上下文
            context = "\n\n".join([
                f"[文档片段 {i+1}]\n{chunk.content}\n来源: {chunk.metadata.get('source', '未知')}"
                for i, (chunk, _) in enumerate(relevant_chunks)
            ])
            
            # 构建包含对话历史的消息列表
            messages = []
            
            # 使用指定agent的系统提示词
            system_prompt = self.agent_manager.get_system_prompt(agent_name, context)
            if "对话历史" not in system_prompt:
                system_prompt += "\n\n如果用户的问题与之前的对话相关，请结合对话历史来提供连贯的回答。"
            
            messages.append({"role": "system", "content": system_prompt})
            
            # 添加对话历史（只保留最近的几轮对话以避免上下文过长）
            recent_history = chat_history[-6:] if len(chat_history) > 6 else chat_history
            for msg in recent_history:
                messages.append(msg)
            
            # 添加当前问题
            messages.append({"role": "user", "content": query})
            
            # 流式生成回答
            answer_parts = []
            for chunk in self.llm_client.generate_stream_with_context(messages):
                answer_parts.append(chunk)
                yield chunk
            
            # 添加引用信息
            references = "\n\n📚 参考文档:\n"
            for i, (chunk, score) in enumerate(relevant_chunks):
                source = chunk.metadata.get('source', '未知')
                page = chunk.metadata.get('page', '')
                page_info = f", 第{page}页" if page else ""
                references += f"[{i+1}] {source}{page_info} (相似度: {score:.3f})\n"
            
            yield references
        
        except Exception as e:
            logging.error(f"基于上下文的流式查询知识库失败: {e}")
            yield f"❌ 查询失败: {e}"
    
    def list_knowledge_bases(self) -> List[str]:
        """列出所有知识库
        
        Returns:
            知识库名称列表
        """
        return list(self.knowledge_bases.keys())
    
    def get_knowledge_base_info(self, kb_name: str) -> Optional[KnowledgeBaseInfo]:
        """获取知识库信息
        
        Args:
            kb_name: 知识库名称
            
        Returns:
            知识库信息
        """
        return self.knowledge_bases.get(kb_name)
    
    def delete_knowledge_base(self, kb_name: str) -> bool:
        """删除知识库
        
        Args:
            kb_name: 知识库名称
            
        Returns:
            是否删除成功
        """
        if kb_name not in self.knowledge_bases:
            print(f"❌ 知识库 '{kb_name}' 不存在")
            return False
        
        try:
            # 删除知识库文件夹（使用安全的文件夹名称）
            safe_name = self._safe_kb_name(kb_name)
            kb_path = self.storage_path / safe_name
            if kb_path.exists():
                import shutil
                shutil.rmtree(kb_path)
            
            # 从索引中删除
            del self.knowledge_bases[kb_name]
            self._save_knowledge_bases_index()
            
            print(f"✅ 知识库 '{kb_name}' 删除成功")
            return True
        
        except Exception as e:
            logging.error(f"删除知识库失败: {e}")
            print(f"❌ 删除知识库失败: {e}")
            return False
    
    def update_knowledge_base(self, kb_name: str) -> bool:
        """更新知识库（重新处理文档）
        
        Args:
            kb_name: 知识库名称
            
        Returns:
            是否更新成功
        """
        if kb_name not in self.knowledge_bases:
            print(f"❌ 知识库 '{kb_name}' 不存在")
            return False
        
        kb_info = self.knowledge_bases[kb_name]
        
        print(f"🔄 更新知识库: {kb_name}")
        
        # 删除旧数据
        self.delete_knowledge_base(kb_name)
        
        # 重新创建
        return self.create_knowledge_base(
            kb_name, 
            kb_info.folder_path, 
            kb_info.description
        )