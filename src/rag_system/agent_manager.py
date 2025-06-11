#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent管理器
负责管理智能体的角色设定、提示词和能力配置
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class AgentConfig:
    """Agent配置数据类"""
    name: str
    description: str
    avatar: str  # 头像emoji或图标
    system_prompt: str
    tools: List[str]  # 可用工具列表
    mcp_servers: List[str]  # MCP服务器列表
    temperature: float = 0.7
    max_tokens: int = 2000
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()

class AgentManager:
    """Agent管理器"""
    
    def __init__(self, storage_path: str = "data/agents"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.config_file = self.storage_path / "agents.json"
        self.agents: Dict[str, AgentConfig] = {}
        self._load_agents()
        self._ensure_default_agent()
    
    def _load_agents(self):
        """加载agent配置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for name, config_dict in data.items():
                        self.agents[name] = AgentConfig(**config_dict)
                logging.info(f"✅ 加载了 {len(self.agents)} 个Agent配置")
            else:
                logging.info("📝 Agent配置文件不存在，将创建默认配置")
        except Exception as e:
            logging.error(f"❌ 加载Agent配置失败: {e}")
    
    def _save_agents(self):
        """保存agent配置"""
        try:
            data = {name: asdict(config) for name, config in self.agents.items()}
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logging.info("✅ Agent配置已保存")
        except Exception as e:
            logging.error(f"❌ 保存Agent配置失败: {e}")
    
    def _ensure_default_agent(self):
        """确保存在默认agent"""
        if "默认助手" not in self.agents:
            default_agent = AgentConfig(
                name="默认助手",
                description="通用智能助手，基于知识库回答问题",
                avatar="🤖",
                system_prompt="你是一个基于知识库的智能助手。请基于提供的文档内容来回答用户问题，确保回答准确、详细，并在适当时引用相关的文档片段。",
                tools=[],
                mcp_servers=[]
            )
            self.agents["默认助手"] = default_agent
            self._save_agents()
    
    def create_agent(self, config: AgentConfig) -> bool:
        """创建新的agent
        
        Args:
            config: Agent配置
            
        Returns:
            是否创建成功
        """
        try:
            if config.name in self.agents:
                logging.warning(f"⚠️ Agent '{config.name}' 已存在")
                return False
            
            self.agents[config.name] = config
            self._save_agents()
            logging.info(f"✅ 创建Agent '{config.name}' 成功")
            return True
        except Exception as e:
            logging.error(f"❌ 创建Agent失败: {e}")
            return False
    
    def update_agent(self, name: str, config: AgentConfig) -> bool:
        """更新agent配置
        
        Args:
            name: Agent名称
            config: 新的配置
            
        Returns:
            是否更新成功
        """
        try:
            if name not in self.agents:
                logging.warning(f"⚠️ Agent '{name}' 不存在")
                return False
            
            # 保留创建时间
            config.created_at = self.agents[name].created_at
            config.updated_at = datetime.now().isoformat()
            
            self.agents[name] = config
            self._save_agents()
            logging.info(f"✅ 更新Agent '{name}' 成功")
            return True
        except Exception as e:
            logging.error(f"❌ 更新Agent失败: {e}")
            return False
    
    def delete_agent(self, name: str) -> bool:
        """删除agent
        
        Args:
            name: Agent名称
            
        Returns:
            是否删除成功
        """
        try:
            if name not in self.agents:
                logging.warning(f"⚠️ Agent '{name}' 不存在")
                return False
            
            if name == "默认助手":
                logging.warning("⚠️ 不能删除默认助手")
                return False
            
            del self.agents[name]
            self._save_agents()
            logging.info(f"✅ 删除Agent '{name}' 成功")
            return True
        except Exception as e:
            logging.error(f"❌ 删除Agent失败: {e}")
            return False
    
    def get_agent(self, name: str) -> Optional[AgentConfig]:
        """获取agent配置
        
        Args:
            name: Agent名称
            
        Returns:
            Agent配置，如果不存在返回None
        """
        return self.agents.get(name)
    
    def list_agents(self) -> List[str]:
        """列出所有agent名称
        
        Returns:
            Agent名称列表
        """
        return list(self.agents.keys())
    
    def get_agent_info(self, name: str) -> Optional[Dict[str, Any]]:
        """获取agent详细信息
        
        Args:
            name: Agent名称
            
        Returns:
            Agent详细信息字典
        """
        agent = self.get_agent(name)
        if not agent:
            return None
        
        return {
            "name": agent.name,
            "description": agent.description,
            "avatar": agent.avatar,
            "system_prompt": agent.system_prompt,
            "tools_count": len(agent.tools),
            "mcp_servers_count": len(agent.mcp_servers),
            "temperature": agent.temperature,
            "max_tokens": agent.max_tokens,
            "created_at": agent.created_at,
            "updated_at": agent.updated_at
        }
    
    def get_system_prompt(self, name: str, context: str = "") -> str:
        """获取agent的系统提示词
        
        Args:
            name: Agent名称
            context: 上下文信息（如知识库内容）
            
        Returns:
            完整的系统提示词
        """
        agent = self.get_agent(name)
        if not agent:
            agent = self.get_agent("默认助手")
        
        system_prompt = agent.system_prompt
        
        if context:
            system_prompt += f"\n\n相关文档内容:\n{context}"
        
        return system_prompt
    
    def export_agent(self, name: str) -> Optional[Dict[str, Any]]:
        """导出agent配置
        
        Args:
            name: Agent名称
            
        Returns:
            Agent配置字典
        """
        agent = self.get_agent(name)
        if not agent:
            return None
        
        return asdict(agent)
    
    def import_agent(self, config_dict: Dict[str, Any]) -> bool:
        """导入agent配置
        
        Args:
            config_dict: Agent配置字典
            
        Returns:
            是否导入成功
        """
        try:
            config = AgentConfig(**config_dict)
            return self.create_agent(config)
        except Exception as e:
            logging.error(f"❌ 导入Agent配置失败: {e}")
            return False
    
    def load_presets(self, presets_file: str = "examples/agent_presets.json") -> int:
        """加载预设agent配置
        
        Args:
            presets_file: 预设配置文件路径
            
        Returns:
            成功加载的agent数量
        """
        try:
            presets_path = Path(presets_file)
            if not presets_path.exists():
                logging.warning(f"⚠️ 预设配置文件不存在: {presets_file}")
                return 0
            
            with open(presets_path, 'r', encoding='utf-8') as f:
                presets = json.load(f)
            
            loaded_count = 0
            for name, config_dict in presets.items():
                if name not in self.agents:  # 只加载不存在的agent
                    if self.import_agent(config_dict):
                        loaded_count += 1
                        logging.info(f"✅ 加载预设Agent: {name}")
                    else:
                        logging.warning(f"⚠️ 加载预设Agent失败: {name}")
                else:
                    logging.info(f"📝 Agent '{name}' 已存在，跳过加载")
            
            logging.info(f"✅ 成功加载 {loaded_count} 个预设Agent")
            return loaded_count
        
        except Exception as e:
            logging.error(f"❌ 加载预设配置失败: {e}")
            return 0