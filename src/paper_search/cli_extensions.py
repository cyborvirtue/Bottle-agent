#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
论文搜索CLI扩展
添加标签管理和时间搜索功能
"""

import argparse
from typing import List, Dict, Any
from datetime import datetime, timedelta

from .search_engine import PaperSearchEngine
from .tag_manager import TagManager


class PaperSearchCLI:
    """论文搜索命令行接口扩展"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.search_engine = PaperSearchEngine(config)
        self.tag_manager = self.search_engine.tag_manager
    
    def add_tag_command(self, args) -> None:
        """添加标签命令"""
        keywords = [k.strip() for k in args.keywords.split(',') if k.strip()]
        categories = [c.strip() for c in args.categories.split(',') if c.strip()] if args.categories else []
        
        success = self.tag_manager.add_tag(args.name, keywords, categories)
        if success:
            print(f"✅ 标签 '{args.name}' 添加成功")
            print(f"   🔑 关键词: {', '.join(keywords)}")
            if categories:
                print(f"   📂 分类: {', '.join(categories)}")
        else:
            print(f"❌ 标签 '{args.name}' 添加失败")
    
    def remove_tag_command(self, args) -> None:
        """删除标签命令"""
        success = self.tag_manager.remove_tag(args.name)
        if not success:
            print(f"❌ 标签 '{args.name}' 不存在")
    
    def list_tags_command(self, args) -> None:
        """列出标签命令"""
        self.tag_manager.display_tags()
    
    def update_tag_command(self, args) -> None:
        """更新标签命令"""
        keywords = None
        categories = None
        
        if args.keywords:
            keywords = [k.strip() for k in args.keywords.split(',') if k.strip()]
        
        if args.categories:
            categories = [c.strip() for c in args.categories.split(',') if c.strip()]
        
        success = self.tag_manager.update_tag(
            args.name, 
            keywords=keywords, 
            categories=categories, 
            is_active=args.active
        )
        
        if not success:
            print(f"❌ 标签 '{args.name}' 不存在")
    
    def search_time_range_command(self, args) -> None:
        """时间范围搜索命令"""
        print(f"🔍 搜索最近 {args.days} 天的论文: {args.query}")
        
        papers = self.search_engine.search_by_time_range(
            args.query, 
            days_back=args.days, 
            source=args.source, 
            max_results=args.max_results
        )
        
        self.search_engine.display_results(papers)
    
    def search_date_range_command(self, args) -> None:
        """日期范围搜索命令"""
        print(f"🔍 搜索 {args.start_date} 到 {args.end_date} 的论文: {args.query}")
        
        papers = self.search_engine.search(
            args.query,
            source=args.source,
            max_results=args.max_results,
            start_date=args.start_date,
            end_date=args.end_date
        )
        
        self.search_engine.display_results(papers)
    
    def check_notifications_command(self, args) -> None:
        """检查推送通知命令"""
        print("🔔 检查新论文推送...")
        
        count = self.search_engine.check_and_notify_new_papers()
        
        if count > 0:
            print(f"✅ 发现 {count} 篇匹配的新论文")
            self.tag_manager.display_notifications(limit=count)
        else:
            print("📭 暂无新的匹配论文")
    
    def list_notifications_command(self, args) -> None:
        """列出通知命令"""
        self.tag_manager.display_notifications(limit=args.limit)
    
    def mark_read_command(self, args) -> None:
        """标记已读命令"""
        success = self.tag_manager.mark_notification_read(args.paper_id)
        if success:
            print(f"✅ 论文 {args.paper_id} 已标记为已读")
        else:
            print(f"❌ 未找到论文 {args.paper_id}")
    
    def clear_old_notifications_command(self, args) -> None:
        """清理旧通知命令"""
        count = self.tag_manager.clear_old_notifications(args.days)
        print(f"✅ 清理了 {count} 条超过 {args.days} 天的旧通知")
    
    def setup_parser(self) -> argparse.ArgumentParser:
        """设置命令行解析器"""
        parser = argparse.ArgumentParser(description="论文搜索与标签管理工具")
        subparsers = parser.add_subparsers(dest='command', help='可用命令')
        
        # 标签管理命令
        tag_parser = subparsers.add_parser('tag', help='标签管理')
        tag_subparsers = tag_parser.add_subparsers(dest='tag_action', help='标签操作')
        
        # 添加标签
        add_tag_parser = tag_subparsers.add_parser('add', help='添加标签')
        add_tag_parser.add_argument('name', help='标签名称')
        add_tag_parser.add_argument('keywords', help='关键词（逗号分隔）')
        add_tag_parser.add_argument('--categories', help='arXiv分类（逗号分隔）')
        
        # 删除标签
        remove_tag_parser = tag_subparsers.add_parser('remove', help='删除标签')
        remove_tag_parser.add_argument('name', help='标签名称')
        
        # 列出标签
        tag_subparsers.add_parser('list', help='列出所有标签')
        
        # 更新标签
        update_tag_parser = tag_subparsers.add_parser('update', help='更新标签')
        update_tag_parser.add_argument('name', help='标签名称')
        update_tag_parser.add_argument('--keywords', help='新的关键词（逗号分隔）')
        update_tag_parser.add_argument('--categories', help='新的分类（逗号分隔）')
        update_tag_parser.add_argument('--active', type=bool, help='是否激活')
        
        # 时间搜索命令
        time_search_parser = subparsers.add_parser('search-time', help='按时间范围搜索')
        time_search_parser.add_argument('query', help='搜索查询')
        time_search_parser.add_argument('--days', type=int, default=7, help='向前搜索天数')
        time_search_parser.add_argument('--source', default='arxiv', choices=['arxiv', 'semantic_scholar'], help='搜索源')
        time_search_parser.add_argument('--max-results', type=int, help='最大结果数')
        
        # 日期范围搜索命令
        date_search_parser = subparsers.add_parser('search-date', help='按日期范围搜索')
        date_search_parser.add_argument('query', help='搜索查询')
        date_search_parser.add_argument('start_date', help='开始日期 (YYYY-MM-DD)')
        date_search_parser.add_argument('end_date', help='结束日期 (YYYY-MM-DD)')
        date_search_parser.add_argument('--source', default='arxiv', choices=['arxiv', 'semantic_scholar'], help='搜索源')
        date_search_parser.add_argument('--max-results', type=int, help='最大结果数')
        
        # 通知管理命令
        notify_parser = subparsers.add_parser('notify', help='通知管理')
        notify_subparsers = notify_parser.add_subparsers(dest='notify_action', help='通知操作')
        
        # 检查新论文
        notify_subparsers.add_parser('check', help='检查新论文推送')
        
        # 列出通知
        list_notify_parser = notify_subparsers.add_parser('list', help='列出通知')
        list_notify_parser.add_argument('--limit', type=int, default=10, help='显示数量限制')
        
        # 标记已读
        read_parser = notify_subparsers.add_parser('read', help='标记通知为已读')
        read_parser.add_argument('paper_id', help='论文ID')
        
        # 清理旧通知
        clear_parser = notify_subparsers.add_parser('clear', help='清理旧通知')
        clear_parser.add_argument('--days', type=int, default=30, help='保留天数')
        
        return parser
    
    def run(self, args: List[str] = None) -> None:
        """运行CLI"""
        parser = self.setup_parser()
        parsed_args = parser.parse_args(args)
        
        if not parsed_args.command:
            parser.print_help()
            return
        
        # 标签管理命令
        if parsed_args.command == 'tag':
            if parsed_args.tag_action == 'add':
                self.add_tag_command(parsed_args)
            elif parsed_args.tag_action == 'remove':
                self.remove_tag_command(parsed_args)
            elif parsed_args.tag_action == 'list':
                self.list_tags_command(parsed_args)
            elif parsed_args.tag_action == 'update':
                self.update_tag_command(parsed_args)
            else:
                tag_parser.print_help()
        
        # 时间搜索命令
        elif parsed_args.command == 'search-time':
            self.search_time_range_command(parsed_args)
        
        elif parsed_args.command == 'search-date':
            self.search_date_range_command(parsed_args)
        
        # 通知管理命令
        elif parsed_args.command == 'notify':
            if parsed_args.notify_action == 'check':
                self.check_notifications_command(parsed_args)
            elif parsed_args.notify_action == 'list':
                self.list_notifications_command(parsed_args)
            elif parsed_args.notify_action == 'read':
                self.mark_read_command(parsed_args)
            elif parsed_args.notify_action == 'clear':
                self.clear_old_notifications_command(parsed_args)
            else:
                notify_parser.print_help()
        
        else:
            parser.print_help()


def create_cli_extensions(config: Dict[str, Any]) -> PaperSearchCLI:
    """创建CLI扩展实例"""
    return PaperSearchCLI(config)