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

from .document_processor import DocumentProcessor
from .embedding_client import EmbeddingClient
from ..llm.llm_client import LLMClient


@dataclass
class DocumentChunk:
    """文档块数据结构"""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[np.ndarray] = None


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
        
        # 知识库索引文件
        self.index_file = self.storage_path / "knowledge_bases.json"
        
        # 加载知识库索引
        self.knowledge_bases = self._load_knowledge_bases_index()
    
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
            # 创建知识库目录
            kb_path = self.storage_path / name
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
            self._build_vector_index(name, chunks)
            
            # 保存块数据
            self._save_chunks(name, chunks)
            
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
            # 删除知识库文件夹
            kb_path = self.storage_path / kb_name
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