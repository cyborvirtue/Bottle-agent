#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web界面模块
基于Streamlit的Web界面
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, List
from pathlib import Path
import time

# 尝试导入streamlit
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False
    print("⚠️  Streamlit未安装，Web界面不可用")


class WebInterface:
    """Web界面"""
    
    def __init__(self, search_engine, kb_manager, config):
        if not STREAMLIT_AVAILABLE:
            raise ImportError("Streamlit未安装，无法启动Web界面")
        
        self.search_engine = search_engine
        self.kb_manager = kb_manager
        self.config = config
    
    def run(self):
        """运行Web界面"""
        # 设置页面配置
        st.set_page_config(
            page_title="Bottle-Agent",
            page_icon="🍾",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # 主标题
        st.title("🍾 Bottle-Agent")
        st.markdown("*轻量学术搜索与RAG agent*")
        
        # 侧边栏
        self._render_sidebar()
        
        # 主内容区域
        tab1, tab2, tab3, tab4 = st.tabs(["📚 论文搜索", "🏷️ 标签管理", "🧠 RAG问答", "⚙️ 知识库管理"])
        
        with tab1:
            self._render_paper_search()
        
        with tab2:
            self._render_tag_management()
        
        with tab3:
            self._render_rag_query()
        
        with tab4:
            self._render_kb_management()
    
    def _render_sidebar(self):
        """渲染侧边栏"""
        st.sidebar.header("📊 系统状态")
        
        # 知识库统计
        kb_list = self.kb_manager.list_knowledge_bases()
        st.sidebar.metric("知识库数量", len(kb_list))
        
        if kb_list:
            st.sidebar.subheader("📚 知识库列表")
            for kb_name in kb_list:
                kb_info = self.kb_manager.get_knowledge_base_info(kb_name)
                if kb_info:
                    with st.sidebar.expander(f"📖 {kb_name}"):
                        st.write(f"📝 描述: {kb_info.description or '无'}")
                        st.write(f"📊 文档: {kb_info.document_count}")
                        st.write(f"🧩 块数: {kb_info.chunk_count}")
        
        # 标签统计
        if hasattr(self.search_engine, 'tag_manager'):
            try:
                tags = self.search_engine.tag_manager.get_all_tags()
                st.sidebar.metric("标签数量", len(tags))
                
                if tags:
                    st.sidebar.subheader("🏷️ 标签列表")
                    for tag_name, tag_info in list(tags.items())[:5]:  # 只显示前5个
                        with st.sidebar.expander(f"🏷️ {tag_name}"):
                            st.write(f"📝 关键词: {len(tag_info.get('keywords', []))}")
                            st.write(f"📂 分类: {len(tag_info.get('categories', []))}")
                    
                    if len(tags) > 5:
                        st.sidebar.write(f"... 还有 {len(tags) - 5} 个标签")
            except:
                pass
        
        # 配置信息
        st.sidebar.subheader("⚙️ 配置")
        st.sidebar.write(f"🤖 LLM: {self.config['llm']['model']}")
        st.sidebar.write(f"🧮 嵌入: {self.config['embedding']['model']}")
    
    def _render_paper_search(self):
        """渲染论文搜索界面"""
        st.header("📚 论文智能搜索")
        
        # 搜索表单
        with st.form("search_form"):
            # 第一行：搜索查询
            query = st.text_input(
                "搜索查询",
                placeholder="例如：diffusion models in medical imaging",
                help="输入自然语言查询，系统会自动优化搜索关键词"
            )
            
            # 第二行：搜索选项
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                source = st.selectbox(
                    "搜索源",
                    ["arxiv", "semantic_scholar"],
                    help="选择论文搜索源"
                )
            
            with col2:
                max_results = st.number_input(
                    "最大结果数",
                    min_value=1,
                    max_value=50,
                    value=10,
                    help="限制返回的论文数量"
                )
            
            with col3:
                search_type = st.selectbox(
                    "搜索类型",
                    ["普通搜索", "时间范围搜索", "最近N天搜索"],
                    help="选择搜索类型"
                )
            
            # 时间范围选项（条件显示）
            start_date = None
            end_date = None
            days_back = None
            
            if search_type == "时间范围搜索":
                col_date1, col_date2 = st.columns(2)
                with col_date1:
                    start_date = st.date_input(
                        "开始日期",
                        help="搜索的开始日期"
                    )
                with col_date2:
                    end_date = st.date_input(
                        "结束日期",
                        help="搜索的结束日期"
                    )
            
            elif search_type == "最近N天搜索":
                days_back = st.number_input(
                    "回溯天数",
                    min_value=1,
                    max_value=365,
                    value=7,
                    help="搜索最近N天的论文"
                )
            
            submitted = st.form_submit_button("🔍 搜索")
        
        # 执行搜索
        if submitted and query:
            with st.spinner("🔍 搜索中..."):
                try:
                    # 根据搜索类型执行不同的搜索
                    if search_type == "最近N天搜索":
                        results = self.search_engine.search_by_time_range(query, days_back=days_back)
                        search_info = f"最近{days_back}天"
                    elif search_type == "时间范围搜索":
                        start_str = start_date.strftime("%Y-%m-%d") if start_date else None
                        end_str = end_date.strftime("%Y-%m-%d") if end_date else None
                        results = self.search_engine.search(query, start_date=start_str, end_date=end_str)
                        search_info = f"{start_str or '开始'} 到 {end_str or '现在'}"
                    else:
                        results = self.search_engine.search(query)
                        search_info = "全部时间"
                    
                    if results:
                        st.success(f"✅ 找到 {len(results)} 篇论文 ({search_info})")
                        
                        # 显示结果
                        for i, paper in enumerate(results, 1):
                            with st.expander(f"📄 [{i}] {paper.title}", expanded=i <= 3):
                                col1, col2 = st.columns([2, 1])
                                
                                with col1:
                                    st.write(f"**👥 作者:** {', '.join(paper.authors[:5])}")
                                    st.write(f"**📅 发表时间:** {paper.published_date}")
                                    
                                    if paper.abstract:
                                        st.write("**📝 摘要:**")
                                        st.write(paper.abstract)
                                    
                                    if paper.categories:
                                        st.write(f"**🏷️ 分类:** {', '.join(paper.categories[:3])}")
                                
                                with col2:
                                    if paper.pdf_url:
                                        st.link_button("📄 查看PDF", paper.pdf_url)
                                    
                                    if paper.arxiv_id:
                                        st.write(f"**🆔 arXiv ID:** {paper.arxiv_id}")
                                    
                                    if paper.doi:
                                        st.write(f"**🔗 DOI:** {paper.doi}")
                    else:
                        st.warning(f"📭 没有找到相关论文 ({search_info})")
                
                except Exception as e:
                    st.error(f"❌ 搜索失败: {e}")
    
    def _render_tag_management(self):
        """渲染标签管理界面"""
        st.header("🏷️ 标签管理")
        
        # 检查是否有标签管理器
        if not hasattr(self.search_engine, 'tag_manager'):
            st.error("❌ 标签管理功能不可用，请检查后端配置")
            return
        
        tag_manager = self.search_engine.tag_manager
        
        # 创建两列布局
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("➕ 添加新标签")
            
            with st.form("add_tag_form"):
                tag_name = st.text_input(
                    "标签名称",
                    placeholder="例如：深度学习",
                    help="为标签起一个有意义的名称"
                )
                
                tag_keywords = st.text_area(
                    "关键词",
                    placeholder="例如：deep learning, neural network, CNN, RNN",
                    help="用逗号分隔多个关键词"
                )
                
                tag_categories = st.text_input(
                    "arXiv分类（可选）",
                    placeholder="例如：cs.LG, cs.AI, cs.CV",
                    help="用逗号分隔多个arXiv分类代码"
                )
                
                add_submitted = st.form_submit_button("➕ 添加标签")
            
            if add_submitted and tag_name and tag_keywords:
                try:
                    keywords = [k.strip() for k in tag_keywords.split(',') if k.strip()]
                    categories = [c.strip() for c in tag_categories.split(',') if c.strip()] if tag_categories else []
                    
                    tag_manager.add_tag(tag_name, keywords, categories)
                    st.success(f"✅ 标签 '{tag_name}' 添加成功！")
                    st.rerun()
                
                except Exception as e:
                    st.error(f"❌ 添加标签失败: {e}")
        
        with col2:
            st.subheader("🔔 通知管理")
            
            # 检查新论文按钮
            if st.button("🔔 检查新论文推送", use_container_width=True):
                with st.spinner("🔍 检查中..."):
                    try:
                        count = self.search_engine.check_and_notify_new_papers()
                        if count > 0:
                            st.success(f"✅ 发现 {count} 篇匹配的新论文")
                        else:
                            st.info("📭 暂无新的匹配论文")
                    except Exception as e:
                        st.error(f"❌ 检查失败: {e}")
            
            # 显示通知历史
            if st.button("📋 查看通知历史", use_container_width=True):
                try:
                    notifications = tag_manager.get_notifications(limit=10)
                    if notifications:
                        st.subheader("📋 最近通知")
                        for i, notif in enumerate(notifications[:5], 1):
                            with st.expander(f"📄 [{i}] {notif.title[:50]}..."):
                                st.write(f"**🏷️ 匹配标签:** {', '.join(notif.matched_tags)}")
                                st.write(f"**📅 通知时间:** {notif.notification_date[:19]}")
                                st.write(f"**📅 发表时间:** {notif.published_date}")
                                st.write(f"**👥 作者:** {', '.join(notif.authors[:3])}")
                                if notif.pdf_url:
                                    st.link_button("📄 查看PDF", notif.pdf_url)
                    else:
                        st.info("📭 暂无通知历史")
                except Exception as e:
                    st.error(f"❌ 获取通知失败: {e}")
        
        # 显示现有标签
        st.subheader("📋 现有标签")
        
        try:
            tags = tag_manager.get_all_tags()
            
            if tags:
                # 创建标签数据表格
                tag_data = []
                for tag_name, tag_info in tags.items():
                    tag_data.append({
                        "标签名称": tag_name,
                        "关键词数量": len(tag_info.get('keywords', [])),
                        "分类数量": len(tag_info.get('categories', [])),
                        "创建时间": tag_info.get('created_at', '')[:19],
                        "关键词": ', '.join(tag_info.get('keywords', [])[:3]) + ('...' if len(tag_info.get('keywords', [])) > 3 else '')
                    })
                
                df = pd.DataFrame(tag_data)
                st.dataframe(df, use_container_width=True)
                
                # 标签操作
                st.subheader("🔧 标签操作")
                
                col_op1, col_op2 = st.columns(2)
                
                with col_op1:
                    st.write("**✏️ 编辑标签**")
                    edit_tag = st.selectbox(
                        "选择要编辑的标签",
                        ["选择标签..."] + list(tags.keys()),
                        key="edit_tag_select"
                    )
                    
                    if edit_tag != "选择标签...":
                        tag_info = tags[edit_tag]
                        
                        with st.form(f"edit_tag_form_{edit_tag}"):
                            new_keywords = st.text_area(
                                "新关键词",
                                value=', '.join(tag_info.get('keywords', [])),
                                help="用逗号分隔多个关键词"
                            )
                            
                            new_categories = st.text_input(
                                "新分类",
                                value=', '.join(tag_info.get('categories', [])),
                                help="用逗号分隔多个arXiv分类代码"
                            )
                            
                            edit_submitted = st.form_submit_button("✏️ 更新标签")
                        
                        if edit_submitted:
                            try:
                                keywords = [k.strip() for k in new_keywords.split(',') if k.strip()]
                                categories = [c.strip() for c in new_categories.split(',') if c.strip()]
                                
                                tag_manager.update_tag(edit_tag, keywords=keywords, categories=categories)
                                st.success(f"✅ 标签 '{edit_tag}' 更新成功！")
                                st.rerun()
                            
                            except Exception as e:
                                st.error(f"❌ 更新标签失败: {e}")
                
                with col_op2:
                    st.write("**🗑️ 删除标签**")
                    delete_tag = st.selectbox(
                        "选择要删除的标签",
                        ["选择标签..."] + list(tags.keys()),
                        key="delete_tag_select"
                    )
                    
                    if delete_tag != "选择标签...":
                        st.warning(f"⚠️ 确定要删除标签 '{delete_tag}' 吗？")
                        
                        if st.button(f"🗑️ 确认删除 '{delete_tag}'", type="secondary"):
                            try:
                                tag_manager.remove_tag(delete_tag)
                                st.success(f"✅ 标签 '{delete_tag}' 删除成功！")
                                st.rerun()
                            
                            except Exception as e:
                                st.error(f"❌ 删除标签失败: {e}")
            
            else:
                st.info("📭 暂无标签，请添加第一个标签")
        
        except Exception as e:
            st.error(f"❌ 获取标签列表失败: {e}")
    
    def _render_rag_query(self):
        """渲染RAG问答界面"""
        st.header("🧠 RAG智能问答")
        
        # 知识库选择
        kb_list = self.kb_manager.list_knowledge_bases()
        
        if not kb_list:
            st.warning("📭 没有可用的知识库，请先创建知识库")
            return
        
        # 侧边栏配置
        with st.sidebar:
            st.subheader("⚙️ 对话配置")
            selected_kb = st.selectbox(
                "选择知识库",
                kb_list,
                help="选择要查询的知识库"
            )
            
            top_k = st.slider(
                "相关文档数",
                min_value=1,
                max_value=10,
                value=5,
                help="检索的相关文档片段数量"
            )
            
            # 对话统计信息
            if "chat_history" in st.session_state and st.session_state.chat_history:
                user_messages = len([msg for msg in st.session_state.chat_history if msg["role"] == "user"])
                st.metric("对话轮数", user_messages)
            
            # 清空对话历史按钮
            if st.button("🗑️ 清空对话历史"):
                if "chat_history" in st.session_state:
                    st.session_state.chat_history = []
                st.rerun()
            
            # 导出对话历史
            if "chat_history" in st.session_state and st.session_state.chat_history:
                if st.button("📥 导出对话历史"):
                    import json
                    from datetime import datetime
                    
                    export_data = {
                        "timestamp": datetime.now().isoformat(),
                        "knowledge_base": selected_kb,
                        "chat_history": st.session_state.chat_history
                    }
                    
                    st.download_button(
                        label="下载对话记录",
                        data=json.dumps(export_data, ensure_ascii=False, indent=2),
                        file_name=f"rag_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
        
        # Agent配置区域
        st.subheader("🤖 智能体设定")
        
        # Agent选择和配置
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        
        with col1:
            # 获取可用的agent列表
            agent_list = self.kb_manager.agent_manager.list_agents()
            selected_agent = st.selectbox(
                "选择智能体角色",
                agent_list,
                help="选择不同的智能体角色来获得专业化的回答"
            )
            
            # 显示当前agent信息
            if selected_agent:
                agent_info = self.kb_manager.agent_manager.get_agent_info(selected_agent)
                if agent_info:
                    st.markdown(f"{agent_info['avatar']} **{agent_info['name']}** - {agent_info['description']}")
        
        with col2:
            if st.button("⚙️ 配置Agent"):
                st.session_state.show_agent_config = True
        
        with col3:
            if st.button("➕ 新建Agent"):
                st.session_state.show_new_agent = True
        
        with col4:
            if st.button("📦 加载预设"):
                try:
                    count = self.kb_manager.agent_manager.load_presets()
                    if count > 0:
                        st.success(f"✅ 成功加载 {count} 个预设Agent")
                        st.rerun()
                    else:
                        st.info("📝 没有新的预设Agent需要加载")
                except Exception as e:
                    st.error(f"❌ 加载预设失败: {e}")
        
        # Agent配置弹窗
        if st.session_state.get('show_agent_config', False):
            self._render_agent_config_modal(selected_agent)
        
        # 新建Agent弹窗
        if st.session_state.get('show_new_agent', False):
            self._render_new_agent_modal()
        
        st.divider()
        
        # 初始化对话历史和选中的agent
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        if "selected_agent" not in st.session_state:
            st.session_state.selected_agent = "默认助手"
        
        # 显示对话历史
        chat_container = st.container()
        with chat_container:
            for i, message in enumerate(st.session_state.chat_history):
                if message["role"] == "user":
                    with st.chat_message("user"):
                        st.markdown(message["content"])
                else:
                    with st.chat_message("assistant"):
                        st.markdown(message["content"])
        
        # 用户输入
        if prompt := st.chat_input("请输入您的问题...", key="rag_chat_input"):
            if not selected_kb:
                st.error("请先选择知识库")
                return
            
            # 添加用户消息到历史
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            
            # 显示用户消息
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # 生成并显示助手回答
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""
                
                try:
                     # 流式生成回答（基于对话历史和选中的agent）
                     for chunk in self.kb_manager.query_stream_with_context(selected_kb, prompt, st.session_state.chat_history, top_k, selected_agent):
                         full_response += chunk
                         message_placeholder.markdown(full_response + "▌")
                     
                     # 移除光标
                     message_placeholder.markdown(full_response)
                     
                     # 添加助手回答到历史
                     st.session_state.chat_history.append({"role": "assistant", "content": full_response})
                
                except Exception as e:
                    error_msg = f"❌ 查询失败: {e}"
                    message_placeholder.markdown(error_msg)
                    st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
        
        # 显示知识库信息
        if kb_list:
            st.subheader("📚 知识库信息")
            
            selected_info_kb = st.selectbox(
                "查看知识库详情",
                ["选择知识库..."] + kb_list,
                key="info_kb_select"
            )
            
            if selected_info_kb != "选择知识库...":
                kb_info = self.kb_manager.get_knowledge_base_info(selected_info_kb)
                if kb_info:
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("文档数量", kb_info.document_count)
                    
                    with col2:
                        st.metric("文档块数量", kb_info.chunk_count)
                    
                    with col3:
                        st.metric("创建时间", kb_info.created_at[:10])
                    
                    with col4:
                        st.metric("更新时间", kb_info.updated_at[:10])
                    
                    st.write(f"**📝 描述:** {kb_info.description or '无描述'}")
                    st.write(f"**📁 文件夹路径:** {kb_info.folder_path}")
    
    def _render_kb_management(self):
        """渲染知识库管理界面"""
        st.header("⚙️ 知识库管理")
        
        # 创建知识库
        st.subheader("📚 创建新知识库")
        
        with st.form("create_kb_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                kb_name = st.text_input(
                    "知识库名称",
                    placeholder="例如：llm_papers",
                    help="知识库的唯一标识符"
                )
                
                kb_description = st.text_area(
                    "描述",
                    placeholder="例如：大语言模型相关论文",
                    help="知识库的描述信息"
                )
            
            with col2:
                folder_path = st.text_input(
                    "文件夹路径",
                    placeholder="例如：/path/to/papers",
                    help="包含文档的文件夹路径"
                )
                
                st.write("**支持的文件格式:**")
                st.write("📄 PDF, 📝 TXT, 📋 Markdown, 📄 DOCX")
            
            create_submitted = st.form_submit_button("📚 创建知识库")
        
        if create_submitted and kb_name and folder_path:
            # 验证路径
            path = Path(folder_path).expanduser().resolve()
            
            if not path.exists():
                st.error(f"❌ 文件夹路径不存在: {path}")
            else:
                with st.spinner("📚 创建知识库中..."):
                    try:
                        success = self.kb_manager.create_knowledge_base(
                            kb_name, str(path), kb_description
                        )
                        
                        if success:
                            st.success(f"✅ 知识库 '{kb_name}' 创建成功！")
                            st.rerun()  # 刷新页面
                        else:
                            st.error(f"❌ 知识库 '{kb_name}' 创建失败")
                    
                    except Exception as e:
                        st.error(f"❌ 创建失败: {e}")
        
        # 管理现有知识库
        kb_list = self.kb_manager.list_knowledge_bases()
        
        if kb_list:
            st.subheader("📋 现有知识库")
            
            # 知识库列表
            kb_data = []
            for kb_name in kb_list:
                kb_info = self.kb_manager.get_knowledge_base_info(kb_name)
                if kb_info:
                    kb_data.append({
                        "名称": kb_name,
                        "描述": kb_info.description or "无",
                        "文档数": kb_info.document_count,
                        "块数": kb_info.chunk_count,
                        "创建时间": kb_info.created_at[:10]
                    })
            
            if kb_data:
                df = pd.DataFrame(kb_data)
                st.dataframe(df, use_container_width=True)
            
            # 知识库操作
            st.subheader("🔧 知识库操作")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**🔄 更新知识库**")
                update_kb = st.selectbox(
                    "选择要更新的知识库",
                    ["选择知识库..."] + kb_list,
                    key="update_kb_select"
                )
                
                if st.button("🔄 更新", key="update_btn"):
                    if update_kb != "选择知识库...":
                        with st.spinner(f"🔄 更新知识库 '{update_kb}' 中..."):
                            try:
                                success = self.kb_manager.update_knowledge_base(update_kb)
                                if success:
                                    st.success(f"✅ 知识库 '{update_kb}' 更新成功！")
                                    st.rerun()
                                else:
                                    st.error(f"❌ 知识库 '{update_kb}' 更新失败")
                            except Exception as e:
                                st.error(f"❌ 更新失败: {e}")
                    else:
                        st.warning("⚠️ 请选择要更新的知识库")
            
            with col2:
                st.write("**🗑️ 删除知识库**")
                delete_kb = st.selectbox(
                    "选择要删除的知识库",
                    ["选择知识库..."] + kb_list,
                    key="delete_kb_select"
                )
                
                if st.button("🗑️ 删除", key="delete_btn", type="secondary"):
                    if delete_kb != "选择知识库...":
                        # 确认删除
                        if st.session_state.get(f"confirm_delete_{delete_kb}", False):
                            try:
                                success = self.kb_manager.delete_knowledge_base(delete_kb)
                                if success:
                                    st.success(f"✅ 知识库 '{delete_kb}' 删除成功！")
                                    st.session_state[f"confirm_delete_{delete_kb}"] = False
                                    st.rerun()
                                else:
                                    st.error(f"❌ 知识库 '{delete_kb}' 删除失败")
                            except Exception as e:
                                st.error(f"❌ 删除失败: {e}")
                        else:
                            st.warning(f"⚠️ 确定要删除知识库 '{delete_kb}' 吗？")
                            if st.button(f"确认删除 {delete_kb}", key=f"confirm_{delete_kb}"):
                                st.session_state[f"confirm_delete_{delete_kb}"] = True
                                st.rerun()
                    else:
                        st.warning("⚠️ 请选择要删除的知识库")
        else:
            st.info("📭 暂无知识库，请创建第一个知识库")
    
    def _render_agent_config_modal(self, agent_name: str):
        """渲染Agent配置弹窗"""
        with st.expander("🤖 Agent配置", expanded=True):
            agent = self.kb_manager.agent_manager.get_agent(agent_name)
            if not agent:
                st.error(f"Agent '{agent_name}' 不存在")
                return
            
            with st.form(f"agent_config_{agent_name}"):
                st.subheader(f"配置 {agent.avatar} {agent.name}")
                
                # 基本信息
                new_description = st.text_input("描述", value=agent.description)
                new_avatar = st.text_input("头像 (emoji)", value=agent.avatar)
                
                # 系统提示词
                new_system_prompt = st.text_area(
                    "系统提示词",
                    value=agent.system_prompt,
                    height=200,
                    help="定义智能体的角色和行为"
                )
                
                # 参数设置
                col1, col2 = st.columns(2)
                with col1:
                    new_temperature = st.slider(
                        "创造性 (Temperature)",
                        min_value=0.0,
                        max_value=2.0,
                        value=agent.temperature,
                        step=0.1
                    )
                
                with col2:
                    new_max_tokens = st.number_input(
                        "最大输出长度",
                        min_value=100,
                        max_value=8000,
                        value=agent.max_tokens,
                        step=100
                    )
                
                # 工具和MCP配置（暂时显示为文本）
                st.subheader("能力配置")
                new_tools = st.text_area(
                    "可用工具 (每行一个)",
                    value="\n".join(agent.tools),
                    help="智能体可以使用的工具列表"
                )
                
                new_mcp_servers = st.text_area(
                    "MCP服务器 (每行一个)",
                    value="\n".join(agent.mcp_servers),
                    help="智能体可以连接的MCP服务器"
                )
                
                # 按钮
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.form_submit_button("💾 保存配置"):
                        from ..rag_system.agent_manager import AgentConfig
                        
                        updated_config = AgentConfig(
                            name=agent.name,
                            description=new_description,
                            avatar=new_avatar,
                            system_prompt=new_system_prompt,
                            tools=[t.strip() for t in new_tools.split("\n") if t.strip()],
                            mcp_servers=[s.strip() for s in new_mcp_servers.split("\n") if s.strip()],
                            temperature=new_temperature,
                            max_tokens=int(new_max_tokens)
                        )
                        
                        if self.kb_manager.agent_manager.update_agent(agent.name, updated_config):
                            st.success("✅ Agent配置已更新")
                            st.session_state.show_agent_config = False
                            st.rerun()
                        else:
                            st.error("❌ 更新失败")
                
                with col2:
                    if st.form_submit_button("📤 导出配置"):
                        config_dict = self.kb_manager.agent_manager.export_agent(agent.name)
                        if config_dict:
                            import json
                            st.download_button(
                                label="下载配置文件",
                                data=json.dumps(config_dict, ensure_ascii=False, indent=2),
                                file_name=f"agent_{agent.name}.json",
                                mime="application/json"
                            )
                
                with col3:
                    if st.form_submit_button("❌ 关闭"):
                        st.session_state.show_agent_config = False
                        st.rerun()
    
    def _render_new_agent_modal(self):
        """渲染新建Agent弹窗"""
        with st.expander("➕ 新建智能体", expanded=True):
            with st.form("new_agent_form"):
                st.subheader("创建新的智能体")
                
                # 基本信息
                agent_name = st.text_input("名称", placeholder="例如：学术助手")
                agent_description = st.text_input("描述", placeholder="例如：专门回答学术问题的助手")
                agent_avatar = st.text_input("头像 (emoji)", value="🤖", placeholder="🤖")
                
                # 系统提示词
                system_prompt = st.text_area(
                    "系统提示词",
                    placeholder="你是一个专业的学术助手，擅长回答学术相关问题...",
                    height=200,
                    help="定义智能体的角色和行为"
                )
                
                # 参数设置
                col1, col2 = st.columns(2)
                with col1:
                    temperature = st.slider(
                        "创造性 (Temperature)",
                        min_value=0.0,
                        max_value=2.0,
                        value=0.7,
                        step=0.1
                    )
                
                with col2:
                    max_tokens = st.number_input(
                        "最大输出长度",
                        min_value=100,
                        max_value=8000,
                        value=2000,
                        step=100
                    )
                
                # 工具和MCP配置
                st.subheader("能力配置")
                tools_text = st.text_area(
                    "可用工具 (每行一个)",
                    placeholder="search\ncalculator\nfile_reader",
                    help="智能体可以使用的工具列表"
                )
                
                mcp_servers_text = st.text_area(
                    "MCP服务器 (每行一个)",
                    placeholder="filesystem\nbrowser\napi_client",
                    help="智能体可以连接的MCP服务器"
                )
                
                # 按钮
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.form_submit_button("✅ 创建Agent"):
                        if not agent_name or not system_prompt:
                            st.error("请填写名称和系统提示词")
                        else:
                            from ..rag_system.agent_manager import AgentConfig
                            
                            new_config = AgentConfig(
                                name=agent_name,
                                description=agent_description or "自定义智能体",
                                avatar=agent_avatar or "🤖",
                                system_prompt=system_prompt,
                                tools=[t.strip() for t in tools_text.split("\n") if t.strip()],
                                mcp_servers=[s.strip() for s in mcp_servers_text.split("\n") if s.strip()],
                                temperature=temperature,
                                max_tokens=int(max_tokens)
                            )
                            
                            if self.kb_manager.agent_manager.create_agent(new_config):
                                st.success(f"✅ 智能体 '{agent_name}' 创建成功")
                                st.session_state.show_new_agent = False
                                st.rerun()
                            else:
                                st.error("❌ 创建失败，可能名称已存在")
                
                with col2:
                    # 导入配置
                    uploaded_file = st.file_uploader(
                        "导入配置文件",
                        type=["json"],
                        help="上传之前导出的Agent配置文件"
                    )
                    
                    if uploaded_file and st.form_submit_button("📥 导入"):
                        try:
                            import json
                            config_dict = json.load(uploaded_file)
                            if self.kb_manager.agent_manager.import_agent(config_dict):
                                st.success("✅ Agent配置导入成功")
                                st.session_state.show_new_agent = False
                                st.rerun()
                            else:
                                st.error("❌ 导入失败")
                        except Exception as e:
                            st.error(f"❌ 导入失败: {e}")
                
                with col3:
                    if st.form_submit_button("❌ 取消"):
                        st.session_state.show_new_agent = False
                        st.rerun()


def run_streamlit_app(search_engine, kb_manager, config):
    """运行Streamlit应用"""
    if not STREAMLIT_AVAILABLE:
        print("❌ Streamlit未安装，无法启动Web界面")
        return
    
    # 创建Web界面实例
    web_interface = WebInterface(search_engine, kb_manager, config)
    
    # 运行界面
    web_interface.run()