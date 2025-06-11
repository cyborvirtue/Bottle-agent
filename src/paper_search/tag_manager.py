#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标签管理模块
支持用户标签管理和论文推送功能
"""

import json
import os
from typing import List, Dict, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class UserTag:
    """用户标签数据结构"""
    name: str
    keywords: List[str]
    categories: List[str]  # arXiv分类
    created_date: str
    last_check: str = None
    is_active: bool = True
    
    def __post_init__(self):
        if self.last_check is None:
            self.last_check = datetime.now().isoformat()


@dataclass
class PaperNotification:
    """论文推送通知数据结构"""
    paper_id: str
    title: str
    authors: List[str]
    abstract: str
    published_date: str
    pdf_url: str
    matched_tags: List[str]
    notification_date: str
    is_read: bool = False


class TagManager:
    """标签管理器"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.tags_file = self.data_dir / "user_tags.json"
        self.notifications_file = self.data_dir / "notifications.json"
        
        # 确保数据目录存在
        self.data_dir.mkdir(exist_ok=True)
        
        # 加载现有数据
        self.tags = self._load_tags()
        self.notifications = self._load_notifications()
    
    def _load_tags(self) -> List[UserTag]:
        """加载用户标签"""
        if not self.tags_file.exists():
            return []
        
        try:
            with open(self.tags_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [UserTag(**tag_data) for tag_data in data]
        except Exception as e:
            print(f"⚠️  加载标签失败: {e}")
            return []
    
    def _save_tags(self) -> None:
        """保存用户标签"""
        try:
            with open(self.tags_file, 'w', encoding='utf-8') as f:
                json.dump([asdict(tag) for tag in self.tags], f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 保存标签失败: {e}")
    
    def _load_notifications(self) -> List[PaperNotification]:
        """加载通知记录"""
        if not self.notifications_file.exists():
            return []
        
        try:
            with open(self.notifications_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [PaperNotification(**notif_data) for notif_data in data]
        except Exception as e:
            print(f"⚠️  加载通知失败: {e}")
            return []
    
    def _save_notifications(self) -> None:
        """保存通知记录"""
        try:
            with open(self.notifications_file, 'w', encoding='utf-8') as f:
                json.dump([asdict(notif) for notif in self.notifications], f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 保存通知失败: {e}")
    
    def add_tag(self, name: str, keywords: List[str], categories: List[str] = None) -> bool:
        """添加新标签
        
        Args:
            name: 标签名称
            keywords: 关键词列表
            categories: arXiv分类列表
            
        Returns:
            是否添加成功
        """
        if categories is None:
            categories = []
        
        # 检查标签是否已存在
        if any(tag.name == name for tag in self.tags):
            print(f"⚠️  标签 '{name}' 已存在")
            return False
        
        new_tag = UserTag(
            name=name,
            keywords=keywords,
            categories=categories,
            created_date=datetime.now().isoformat()
        )
        
        self.tags.append(new_tag)
        self._save_tags()
        print(f"✅ 标签 '{name}' 添加成功")
        return True
    
    def remove_tag(self, name: str) -> bool:
        """删除标签
        
        Args:
            name: 标签名称
            
        Returns:
            是否删除成功
        """
        for i, tag in enumerate(self.tags):
            if tag.name == name:
                del self.tags[i]
                self._save_tags()
                print(f"✅ 标签 '{name}' 删除成功")
                return True
        
        print(f"⚠️  标签 '{name}' 不存在")
        return False
    
    def update_tag(self, name: str, keywords: List[str] = None, categories: List[str] = None, is_active: bool = None) -> bool:
        """更新标签
        
        Args:
            name: 标签名称
            keywords: 新的关键词列表
            categories: 新的分类列表
            is_active: 是否激活
            
        Returns:
            是否更新成功
        """
        for tag in self.tags:
            if tag.name == name:
                if keywords is not None:
                    tag.keywords = keywords
                if categories is not None:
                    tag.categories = categories
                if is_active is not None:
                    tag.is_active = is_active
                
                self._save_tags()
                print(f"✅ 标签 '{name}' 更新成功")
                return True
        
        print(f"⚠️  标签 '{name}' 不存在")
        return False
    
    def get_tags(self, active_only: bool = True) -> List[UserTag]:
        """获取标签列表
        
        Args:
            active_only: 是否只返回激活的标签
            
        Returns:
            标签列表
        """
        if active_only:
            return [tag for tag in self.tags if tag.is_active]
        return self.tags
    
    def get_tag_keywords(self, active_only: bool = True) -> Set[str]:
        """获取所有标签的关键词集合
        
        Args:
            active_only: 是否只包含激活的标签
            
        Returns:
            关键词集合
        """
        keywords = set()
        for tag in self.get_tags(active_only):
            keywords.update(tag.keywords)
        return keywords
    
    def get_tag_categories(self, active_only: bool = True) -> Set[str]:
        """获取所有标签的分类集合
        
        Args:
            active_only: 是否只包含激活的标签
            
        Returns:
            分类集合
        """
        categories = set()
        for tag in self.get_tags(active_only):
            categories.update(tag.categories)
        return categories
    
    def get_all_tags(self) -> Dict[str, Dict[str, Any]]:
        """获取所有标签的字典格式数据
        
        Returns:
            标签字典，键为标签名称，值为标签信息
        """
        result = {}
        for tag in self.tags:
            result[tag.name] = {
                'keywords': tag.keywords,
                'categories': tag.categories,
                'created_at': tag.created_date,
                'last_check': tag.last_check,
                'is_active': tag.is_active
            }
        return result
    
    def match_paper_tags(self, paper_title: str, paper_abstract: str, paper_categories: List[str]) -> List[str]:
        """匹配论文与用户标签
        
        Args:
            paper_title: 论文标题
            paper_abstract: 论文摘要
            paper_categories: 论文分类
            
        Returns:
            匹配的标签名称列表
        """
        matched_tags = []
        paper_text = f"{paper_title} {paper_abstract}".lower()
        
        for tag in self.get_tags(active_only=True):
            # 检查关键词匹配
            keyword_match = any(keyword.lower() in paper_text for keyword in tag.keywords)
            
            # 检查分类匹配
            category_match = any(cat in paper_categories for cat in tag.categories)
            
            if keyword_match or category_match:
                matched_tags.append(tag.name)
        
        return matched_tags
    
    def add_notification(self, paper_id: str, title: str, authors: List[str], abstract: str, 
                        published_date: str, pdf_url: str, matched_tags: List[str]) -> None:
        """添加论文推送通知
        
        Args:
            paper_id: 论文ID
            title: 论文标题
            authors: 作者列表
            abstract: 摘要
            published_date: 发表日期
            pdf_url: PDF链接
            matched_tags: 匹配的标签
        """
        notification = PaperNotification(
            paper_id=paper_id,
            title=title,
            authors=authors,
            abstract=abstract,
            published_date=published_date,
            pdf_url=pdf_url,
            matched_tags=matched_tags,
            notification_date=datetime.now().isoformat()
        )
        
        self.notifications.append(notification)
        self._save_notifications()
    
    def get_notifications(self, unread_only: bool = False, limit: int = None) -> List[PaperNotification]:
        """获取通知列表
        
        Args:
            unread_only: 是否只返回未读通知
            limit: 限制返回数量
            
        Returns:
            通知列表
        """
        notifications = self.notifications
        
        if unread_only:
            notifications = [n for n in notifications if not n.is_read]
        
        # 按通知日期倒序排列
        notifications.sort(key=lambda x: x.notification_date, reverse=True)
        
        if limit:
            notifications = notifications[:limit]
        
        return notifications
    
    def mark_notification_read(self, paper_id: str) -> bool:
        """标记通知为已读
        
        Args:
            paper_id: 论文ID
            
        Returns:
            是否标记成功
        """
        for notification in self.notifications:
            if notification.paper_id == paper_id:
                notification.is_read = True
                self._save_notifications()
                return True
        return False
    
    def clear_old_notifications(self, days: int = 30) -> int:
        """清理旧通知
        
        Args:
            days: 保留天数
            
        Returns:
            清理的通知数量
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff_date.isoformat()
        
        old_count = len(self.notifications)
        self.notifications = [n for n in self.notifications if n.notification_date >= cutoff_str]
        new_count = len(self.notifications)
        
        if old_count != new_count:
            self._save_notifications()
        
        return old_count - new_count
    
    def display_tags(self) -> None:
        """显示所有标签"""
        tags = self.get_tags(active_only=False)
        
        if not tags:
            print("📭 暂无标签")
            return
        
        print(f"\n🏷️  用户标签 ({len(tags)} 个):\n")
        
        for i, tag in enumerate(tags, 1):
            status = "✅" if tag.is_active else "❌"
            print(f"{status} [{i}] {tag.name}")
            print(f"   🔑 关键词: {', '.join(tag.keywords)}")
            if tag.categories:
                print(f"   📂 分类: {', '.join(tag.categories)}")
            print(f"   📅 创建: {tag.created_date[:10]}")
            print()
    
    def display_notifications(self, limit: int = 10) -> None:
        """显示通知
        
        Args:
            limit: 显示数量限制
        """
        notifications = self.get_notifications(limit=limit)
        
        if not notifications:
            print("📭 暂无通知")
            return
        
        print(f"\n🔔 论文推送通知 (最近 {len(notifications)} 条):\n")
        
        for i, notif in enumerate(notifications, 1):
            status = "📖" if notif.is_read else "🆕"
            print(f"{status} [{i}] {notif.title}")
            print(f"   👥 作者: {', '.join(notif.authors[:2])}{'...' if len(notif.authors) > 2 else ''}")
            print(f"   📅 发表: {notif.published_date}")
            print(f"   🏷️  匹配标签: {', '.join(notif.matched_tags)}")
            print(f"   📝 摘要: {notif.abstract[:100]}...")
            if notif.pdf_url:
                print(f"   🔗 PDF: {notif.pdf_url}")
            print()