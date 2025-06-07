#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM客户端模块
支持OpenAI、Anthropic等多种LLM提供商
"""

import openai
from typing import Dict, Any, List, Optional
import time
import logging


class LLMClient:
    """LLM客户端"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.llm_config = config["llm"]
        self.provider = self.llm_config["provider"]
        
        # 初始化客户端
        if self.provider == "openai":
            self._init_openai()
        else:
            raise ValueError(f"不支持的LLM提供商: {self.provider}")
    
    def _init_openai(self):
        """初始化OpenAI客户端"""
        api_key = self.llm_config.get("api_key")
        if not api_key:
            raise ValueError("OpenAI API密钥未配置")
        
        # 设置API密钥
        openai.api_key = api_key
        
        # 设置自定义base_url（如果有）
        if self.llm_config.get("base_url"):
            openai.api_base = self.llm_config["base_url"]
    
    def generate(self, prompt: str, **kwargs) -> str:
        """生成文本
        
        Args:
            prompt: 输入提示
            **kwargs: 额外参数
            
        Returns:
            生成的文本
        """
        if self.provider == "openai":
            return self._generate_openai(prompt, **kwargs)
        else:
            raise ValueError(f"不支持的LLM提供商: {self.provider}")
    
    def _generate_openai(self, prompt: str, **kwargs) -> str:
        """使用OpenAI生成文本
        
        Args:
            prompt: 输入提示
            **kwargs: 额外参数
            
        Returns:
            生成的文本
        """
        # 合并配置参数
        params = {
            "model": self.llm_config["model"],
            "temperature": self.llm_config.get("temperature", 0.7),
            "max_tokens": self.llm_config.get("max_tokens", 2000),
        }
        params.update(kwargs)
        
        # 构建消息
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        try:
            # 调用OpenAI API
            response = openai.ChatCompletion.create(
                messages=messages,
                **params
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            logging.error(f"OpenAI API调用失败: {e}")
            raise
    
    def generate_with_context(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """基于上下文生成文本
        
        Args:
            messages: 消息列表，格式为[{"role": "user/assistant", "content": "..."}]
            **kwargs: 额外参数
            
        Returns:
            生成的文本
        """
        if self.provider == "openai":
            return self._generate_openai_with_context(messages, **kwargs)
        else:
            raise ValueError(f"不支持的LLM提供商: {self.provider}")
    
    def _generate_openai_with_context(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """使用OpenAI基于上下文生成文本
        
        Args:
            messages: 消息列表
            **kwargs: 额外参数
            
        Returns:
            生成的文本
        """
        # 合并配置参数
        params = {
            "model": self.llm_config["model"],
            "temperature": self.llm_config.get("temperature", 0.7),
            "max_tokens": self.llm_config.get("max_tokens", 2000),
        }
        params.update(kwargs)
        
        try:
            # 调用OpenAI API
            response = openai.ChatCompletion.create(
                messages=messages,
                **params
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            logging.error(f"OpenAI API调用失败: {e}")
            raise
    
    def extract_keywords(self, text: str) -> List[str]:
        """从文本中提取关键词
        
        Args:
            text: 输入文本
            
        Returns:
            关键词列表
        """
        prompt = f"""
请从以下文本中提取最重要的关键词，用于学术论文搜索。

文本: {text}

要求:
1. 提取5-10个最重要的关键词
2. 关键词应该是学术术语或专业词汇
3. 用逗号分隔关键词
4. 只返回关键词，不要其他解释

关键词:
"""
        
        try:
            response = self.generate(prompt)
            # 解析关键词
            keywords = [kw.strip() for kw in response.split(',')]
            return [kw for kw in keywords if kw]  # 过滤空字符串
        except Exception as e:
            logging.error(f"关键词提取失败: {e}")
            return []
    
    def summarize_papers(self, papers: List[Dict[str, Any]]) -> str:
        """总结论文列表
        
        Args:
            papers: 论文列表
            
        Returns:
            总结文本
        """
        if not papers:
            return "没有找到相关论文。"
        
        # 构建论文信息
        papers_text = ""
        for i, paper in enumerate(papers[:5], 1):  # 只总结前5篇
            papers_text += f"""
{i}. 标题: {paper.get('title', '')}
   作者: {', '.join(paper.get('authors', [])[:3])}
   摘要: {paper.get('abstract', '')[:300]}...
   发表时间: {paper.get('published_date', '')}

"""
        
        prompt = f"""
请对以下学术论文进行总结分析:

{papers_text}

请提供:
1. 主要研究领域和方向
2. 关键技术和方法
3. 研究趋势和发展方向
4. 推荐阅读的论文（按重要性排序）

总结:
"""
        
        try:
            return self.generate(prompt)
        except Exception as e:
            logging.error(f"论文总结失败: {e}")
            return "论文总结生成失败。"