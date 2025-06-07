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
        tab1, tab2, tab3 = st.tabs(["📚 论文搜索", "🧠 RAG问答", "⚙️ 知识库管理"])
        
        with tab1:
            self._render_paper_search()
        
        with tab2:
            self._render_rag_query()
        
        with tab3:
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
        
        # 配置信息
        st.sidebar.subheader("⚙️ 配置")
        st.sidebar.write(f"🤖 LLM: {self.config['llm']['model']}")
        st.sidebar.write(f"🧮 嵌入: {self.config['embedding']['model']}")
    
    def _render_paper_search(self):
        """渲染论文搜索界面"""
        st.header("📚 论文智能搜索")
        
        # 搜索表单
        with st.form("search_form"):
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                query = st.text_input(
                    "搜索查询",
                    placeholder="例如：diffusion models in medical imaging",
                    help="输入自然语言查询，系统会自动优化搜索关键词"
                )
            
            with col2:
                source = st.selectbox(
                    "搜索源",
                    ["arxiv", "semantic_scholar"],
                    help="选择论文搜索源"
                )
            
            with col3:
                max_results = st.number_input(
                    "最大结果数",
                    min_value=1,
                    max_value=50,
                    value=10,
                    help="限制返回的论文数量"
                )
            
            submitted = st.form_submit_button("🔍 搜索")
        
        # 执行搜索
        if submitted and query:
            with st.spinner("🔍 搜索中..."):
                try:
                    results = self.search_engine.search(query, source, max_results)
                    
                    if results:
                        st.success(f"✅ 找到 {len(results)} 篇论文")
                        
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
                        st.warning("📭 没有找到相关论文")
                
                except Exception as e:
                    st.error(f"❌ 搜索失败: {e}")
    
    def _render_rag_query(self):
        """渲染RAG问答界面"""
        st.header("🧠 RAG智能问答")
        
        # 知识库选择
        kb_list = self.kb_manager.list_knowledge_bases()
        
        if not kb_list:
            st.warning("📭 没有可用的知识库，请先创建知识库")
            return
        
        # 问答表单
        with st.form("rag_form"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                question = st.text_area(
                    "问题",
                    placeholder="例如：什么是transformer架构？它有哪些优势？",
                    height=100,
                    help="输入您想要了解的问题"
                )
            
            with col2:
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
            
            submitted = st.form_submit_button("🤔 提问")
        
        # 执行查询
        if submitted and question and selected_kb:
            with st.spinner("🤔 思考中..."):
                try:
                    answer = self.kb_manager.query(selected_kb, question, top_k)
                    
                    # 显示回答
                    st.subheader("📝 回答")
                    st.markdown(answer)
                
                except Exception as e:
                    st.error(f"❌ 查询失败: {e}")
        
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


def run_streamlit_app(search_engine, kb_manager, config):
    """运行Streamlit应用"""
    if not STREAMLIT_AVAILABLE:
        print("❌ Streamlit未安装，无法启动Web界面")
        return
    
    # 创建Web界面实例
    web_interface = WebInterface(search_engine, kb_manager, config)
    
    # 运行界面
    web_interface.run()