#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG系统数据结构模块
定义共享的数据结构，避免循环导入
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class DocumentChunk:
    """文档块数据结构"""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Any = None  # numpy array or None (保持与原代码一致的字段名)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'content': self.content,
            'metadata': self.metadata,
            'embedding': self.embedding.tolist() if self.embedding is not None else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocumentChunk':
        """从字典创建实例"""
        import numpy as np
        embedding = np.array(data['embedding']) if data.get('embedding') is not None else None
        return cls(
            id=data['id'],
            content=data['content'],
            metadata=data['metadata'],
            embedding=embedding
        )


@dataclass
class Document:
    """文档数据结构"""
    id: str
    title: str
    content: str
    file_path: str
    file_type: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'file_path': self.file_path,
            'file_type': self.file_type,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Document':
        """从字典创建实例"""
        return cls(
            id=data['id'],
            title=data['title'],
            content=data['content'],
            file_path=data['file_path'],
            file_type=data['file_type'],
            metadata=data['metadata']
        )