#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
嵌入客户端模块
支持OpenAI、HuggingFace等多种嵌入模型
"""

from openai import OpenAI
import numpy as np
from typing import List, Dict, Any
import logging
import time
import os

# HuggingFace支持
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("⚠️  sentence-transformers未安装，将无法使用本地嵌入模型")


class EmbeddingClient:
    """嵌入客户端"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.embedding_config = config["embedding"]
        self.provider = self.embedding_config["provider"]
        self.model_name = self.embedding_config["model"]
        
        # 初始化客户端
        if self.provider == "openai":
            self._init_openai()
        elif self.provider == "huggingface":
            self._init_huggingface()
        else:
            raise ValueError(f"不支持的嵌入提供商: {self.provider}")
    
    def _init_openai(self):
        """初始化OpenAI客户端"""
        api_key = self.embedding_config.get("api_key")
        if not api_key:
            raise ValueError("OpenAI API密钥未配置")
        
        # 初始化OpenAI客户端
        client_kwargs = {
            "api_key": api_key
        }
        
        # 设置自定义base_url（如果有）
        if self.embedding_config.get("base_url"):
            client_kwargs["base_url"] = self.embedding_config["base_url"]
        
        self.openai_client = OpenAI(**client_kwargs)
    
    def _init_huggingface(self):
        """初始化HuggingFace客户端"""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ValueError("sentence-transformers库未安装")
        
        try:
            print(f"🤗 加载HuggingFace模型: {self.model_name}")
            self.hf_model = SentenceTransformer(self.model_name)
            print("✅ 模型加载成功")
        except Exception as e:
            raise ValueError(f"加载HuggingFace模型失败: {e}")
    
    def embed_text(self, text: str) -> np.ndarray:
        """生成单个文本的嵌入
        
        Args:
            text: 输入文本
            
        Returns:
            嵌入向量
        """
        if self.provider == "openai":
            return self._embed_openai([text])[0]
        elif self.provider == "huggingface":
            return self._embed_huggingface([text])[0]
        else:
            raise ValueError(f"不支持的嵌入提供商: {self.provider}")
    
    def embed_texts(self, texts: List[str]) -> List[np.ndarray]:
        """生成多个文本的嵌入
        
        Args:
            texts: 文本列表
            
        Returns:
            嵌入向量列表
        """
        if not texts:
            return []
        
        if self.provider == "openai":
            return self._embed_openai(texts)
        elif self.provider == "huggingface":
            return self._embed_huggingface(texts)
        else:
            raise ValueError(f"不支持的嵌入提供商: {self.provider}")
    
    def _embed_openai(self, texts: List[str]) -> List[np.ndarray]:
        """使用OpenAI生成嵌入
        
        Args:
            texts: 文本列表
            
        Returns:
            嵌入向量列表
        """
        embeddings = []
        batch_size = 100  # OpenAI API批处理大小限制
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            try:
                # 调用OpenAI API
                response = self.openai_client.embeddings.create(
                    model=self.model_name,
                    input=batch,
                    encoding_format="float"
                )
                
                # 提取嵌入向量
                batch_embeddings = [
                    np.array(item.embedding) 
                    for item in response.data
                ]
                
                embeddings.extend(batch_embeddings)
                
                # 避免API限制
                if i + batch_size < len(texts):
                    time.sleep(0.1)
            
            except Exception as e:
                logging.error(f"OpenAI嵌入生成失败: {e}")
                raise
        
        return embeddings
    
    def _embed_huggingface(self, texts: List[str]) -> List[np.ndarray]:
        """使用HuggingFace生成嵌入
        
        Args:
            texts: 文本列表
            
        Returns:
            嵌入向量列表
        """
        try:
            # 生成嵌入
            embeddings = self.hf_model.encode(
                texts,
                convert_to_numpy=True,
                show_progress_bar=len(texts) > 10
            )
            
            # 转换为列表
            return [embedding for embedding in embeddings]
        
        except Exception as e:
            logging.error(f"HuggingFace嵌入生成失败: {e}")
            raise
    
    def get_embedding_dimension(self) -> int:
        """获取嵌入向量维度
        
        Returns:
            嵌入向量维度
        """
        if self.provider == "openai":
            # OpenAI模型的维度
            model_dimensions = {
                "text-embedding-ada-002": 1536,
                "text-embedding-3-small": 1536,
                "text-embedding-3-large": 3072
            }
            return model_dimensions.get(self.model_name, 1536)
        
        elif self.provider == "huggingface":
            # 通过生成一个测试嵌入来获取维度
            test_embedding = self.embed_text("test")
            return len(test_embedding)
        
        else:
            raise ValueError(f"不支持的嵌入提供商: {self.provider}")
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """计算两个嵌入向量的相似度
        
        Args:
            embedding1: 嵌入向量1
            embedding2: 嵌入向量2
            
        Returns:
            相似度分数（余弦相似度）
        """
        # 归一化向量
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        # 计算余弦相似度
        similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
        return float(similarity)
    
    def find_most_similar(self, query_embedding: np.ndarray, 
                         candidate_embeddings: List[np.ndarray], 
                         top_k: int = 5) -> List[tuple]:
        """找到最相似的嵌入向量
        
        Args:
            query_embedding: 查询嵌入向量
            candidate_embeddings: 候选嵌入向量列表
            top_k: 返回的最相似向量数量
            
        Returns:
            (索引, 相似度分数)的列表，按相似度降序排列
        """
        similarities = []
        
        for i, candidate in enumerate(candidate_embeddings):
            similarity = self.compute_similarity(query_embedding, candidate)
            similarities.append((i, similarity))
        
        # 按相似度降序排序
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]