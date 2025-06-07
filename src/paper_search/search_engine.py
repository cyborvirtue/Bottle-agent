#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
论文搜索引擎模块
支持arXiv和Semantic Scholar API
"""

import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
from dataclasses import dataclass

from ..llm.llm_client import LLMClient


@dataclass
class Paper:
    """论文数据结构"""
    title: str
    authors: List[str]
    abstract: str
    published_date: str
    pdf_url: str
    arxiv_id: Optional[str] = None
    doi: Optional[str] = None
    categories: List[str] = None
    
    def __post_init__(self):
        if self.categories is None:
            self.categories = []


class PaperSearchEngine:
    """论文搜索引擎"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.llm_client = LLMClient(config)
        self.arxiv_config = config["paper_search"]["arxiv"]
        self.semantic_scholar_config = config["paper_search"]["semantic_scholar"]
    
    def search(self, query: str, source: str = "arxiv", max_results: int = None) -> List[Paper]:
        """搜索论文
        
        Args:
            query: 搜索查询
            source: 搜索源 (arxiv, semantic_scholar)
            max_results: 最大结果数
            
        Returns:
            论文列表
        """
        # 使用LLM优化查询
        optimized_query = self._optimize_query(query)
        
        if source == "arxiv":
            return self._search_arxiv(optimized_query, max_results)
        elif source == "semantic_scholar":
            return self._search_semantic_scholar(optimized_query, max_results)
        else:
            raise ValueError(f"不支持的搜索源: {source}")
    
    def _optimize_query(self, query: str) -> str:
        """使用LLM优化搜索查询
        
        Args:
            query: 原始查询
            
        Returns:
            优化后的查询
        """
        prompt = f"""
你是一个学术搜索专家。请将用户的自然语言查询转换为适合学术论文搜索的关键词。

用户查询: {query}

请提取最重要的学术关键词，用空格分隔。只返回关键词，不要其他解释。

示例:
用户查询: "最近有哪些关于Diffusion模型在医学图像中的应用？"
关键词: diffusion model medical image application

用户查询: "图神经网络在药物发现中的应用"
关键词: graph neural network drug discovery

现在请处理用户查询:
"""
        
        try:
            response = self.llm_client.generate(prompt)
            # 清理响应，只保留关键词
            optimized = re.sub(r'[^a-zA-Z0-9\s\u4e00-\u9fff]', ' ', response.strip())
            optimized = ' '.join(optimized.split())  # 规范化空格
            return optimized if optimized else query
        except Exception as e:
            print(f"⚠️  查询优化失败，使用原始查询: {e}")
            return query
    
    def _search_arxiv(self, query: str, max_results: int = None) -> List[Paper]:
        """搜索arXiv
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
            
        Returns:
            论文列表
        """
        if max_results is None:
            max_results = self.arxiv_config["max_results"]
        
        # 构建arXiv API查询
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max_results,
            "sortBy": self.arxiv_config["sort_by"],
            "sortOrder": self.arxiv_config["sort_order"]
        }
        
        try:
            response = requests.get(self.arxiv_config["base_url"], params=params, timeout=30)
            response.raise_for_status()
            
            return self._parse_arxiv_response(response.text)
        except Exception as e:
            print(f"❌ arXiv搜索失败: {e}")
            return []
    
    def _parse_arxiv_response(self, xml_content: str) -> List[Paper]:
        """解析arXiv API响应
        
        Args:
            xml_content: XML响应内容
            
        Returns:
            论文列表
        """
        papers = []
        
        try:
            root = ET.fromstring(xml_content)
            
            # 定义命名空间
            namespaces = {
                'atom': 'http://www.w3.org/2005/Atom',
                'arxiv': 'http://arxiv.org/schemas/atom'
            }
            
            entries = root.findall('atom:entry', namespaces)
            
            for entry in entries:
                # 提取基本信息
                title = entry.find('atom:title', namespaces).text.strip().replace('\n', ' ')
                abstract = entry.find('atom:summary', namespaces).text.strip().replace('\n', ' ')
                
                # 提取作者
                authors = []
                for author in entry.findall('atom:author', namespaces):
                    name = author.find('atom:name', namespaces).text
                    authors.append(name)
                
                # 提取发布日期
                published = entry.find('atom:published', namespaces).text
                published_date = published.split('T')[0]  # 只保留日期部分
                
                # 提取PDF链接和arXiv ID
                pdf_url = None
                arxiv_id = None
                
                for link in entry.findall('atom:link', namespaces):
                    if link.get('type') == 'application/pdf':
                        pdf_url = link.get('href')
                
                # 从ID中提取arXiv ID
                entry_id = entry.find('atom:id', namespaces).text
                arxiv_id = entry_id.split('/')[-1]
                
                # 提取分类
                categories = []
                for category in entry.findall('atom:category', namespaces):
                    categories.append(category.get('term'))
                
                paper = Paper(
                    title=title,
                    authors=authors,
                    abstract=abstract,
                    published_date=published_date,
                    pdf_url=pdf_url,
                    arxiv_id=arxiv_id,
                    categories=categories
                )
                
                papers.append(paper)
        
        except Exception as e:
            print(f"❌ 解析arXiv响应失败: {e}")
        
        return papers
    
    def _search_semantic_scholar(self, query: str, max_results: int = None) -> List[Paper]:
        """搜索Semantic Scholar
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
            
        Returns:
            论文列表
        """
        if max_results is None:
            max_results = self.semantic_scholar_config["max_results"]
        
        headers = {}
        if self.semantic_scholar_config.get("api_key"):
            headers["x-api-key"] = self.semantic_scholar_config["api_key"]
        
        params = {
            "query": query,
            "limit": max_results,
            "fields": "title,authors,abstract,year,openAccessPdf,externalIds"
        }
        
        try:
            url = f"{self.semantic_scholar_config['base_url']}/paper/search"
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            
            return self._parse_semantic_scholar_response(response.json())
        except Exception as e:
            print(f"❌ Semantic Scholar搜索失败: {e}")
            return []
    
    def _parse_semantic_scholar_response(self, json_data: Dict[str, Any]) -> List[Paper]:
        """解析Semantic Scholar API响应
        
        Args:
            json_data: JSON响应数据
            
        Returns:
            论文列表
        """
        papers = []
        
        try:
            for item in json_data.get('data', []):
                # 提取基本信息
                title = item.get('title', '').strip()
                abstract = item.get('abstract', '').strip() if item.get('abstract') else ''
                
                # 提取作者
                authors = []
                for author in item.get('authors', []):
                    authors.append(author.get('name', ''))
                
                # 提取年份
                year = item.get('year')
                published_date = str(year) if year else ''
                
                # 提取PDF链接
                pdf_url = None
                open_access_pdf = item.get('openAccessPdf')
                if open_access_pdf:
                    pdf_url = open_access_pdf.get('url')
                
                # 提取DOI和arXiv ID
                doi = None
                arxiv_id = None
                external_ids = item.get('externalIds', {})
                if external_ids:
                    doi = external_ids.get('DOI')
                    arxiv_id = external_ids.get('ArXiv')
                
                paper = Paper(
                    title=title,
                    authors=authors,
                    abstract=abstract,
                    published_date=published_date,
                    pdf_url=pdf_url,
                    arxiv_id=arxiv_id,
                    doi=doi
                )
                
                papers.append(paper)
        
        except Exception as e:
            print(f"❌ 解析Semantic Scholar响应失败: {e}")
        
        return papers
    
    def display_results(self, papers: List[Paper]) -> None:
        """显示搜索结果
        
        Args:
            papers: 论文列表
        """
        if not papers:
            print("📭 没有找到相关论文")
            return
        
        print(f"\n📚 找到 {len(papers)} 篇论文:\n")
        
        for i, paper in enumerate(papers, 1):
            print(f"🔸 [{i}] {paper.title}")
            print(f"   👥 作者: {', '.join(paper.authors[:3])}{'...' if len(paper.authors) > 3 else ''}")
            print(f"   📅 发表: {paper.published_date}")
            
            if paper.abstract:
                # 截断摘要
                abstract_preview = paper.abstract[:200] + "..." if len(paper.abstract) > 200 else paper.abstract
                print(f"   📝 摘要: {abstract_preview}")
            
            if paper.pdf_url:
                print(f"   🔗 PDF: {paper.pdf_url}")
            
            if paper.arxiv_id:
                print(f"   🆔 arXiv: {paper.arxiv_id}")
            
            if paper.categories:
                print(f"   🏷️  分类: {', '.join(paper.categories[:3])}")
            
            print()