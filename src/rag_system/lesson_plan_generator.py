#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
教案设计生成器模块
支持PPT解析、要点提取和教案生成
"""

import os
import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

import fitz  # PyMuPDF for PDF processing
from ..llm.llm_client import LLMClient
from .embedding_client import EmbeddingClient
from .knowledge_base import KnowledgeBaseManager


@dataclass
class PPTSlide:
    """PPT幻灯片数据结构"""
    page_number: int
    title: str
    content: str
    images: List[str]  # 图片描述
    bullet_points: List[str]


@dataclass
class PPTScript:
    """PPT页面讲稿数据结构"""
    page_number: int
    page_title: str
    script_content: str  # 完整的讲稿内容
    key_points: List[str]  # 本页重点
    estimated_time: str  # 预计讲解时间
    teaching_tips: List[str]  # 教学提示


@dataclass
class TeachingScript:
    """教学文稿数据结构 - 专注于PPT页面对应的教学内容"""
    title: str  # 课程标题
    subject: str  # 学科
    grade_level: str  # 年级
    total_duration: str  # 总时长
    ppt_scripts: List[PPTScript]  # PPT页面讲稿列表
    course_overview: str = ""  # 课程概述
    learning_objectives: List[str] = None  # 学习目标
    materials_needed: List[str] = None  # 所需材料
    created_at: str = ""  # 创建时间
    
    # 兼容性字段（用于向后兼容旧的教案格式）
    objectives: Optional[List[str]] = None
    materials: Optional[List[str]] = None
    sections: Optional[List] = None
    assessment: Optional[str] = None
    homework: Optional[str] = None
    reflection: Optional[str] = None
    
    def __post_init__(self):
        if self.learning_objectives is None:
            self.learning_objectives = []
        if self.materials_needed is None:
            self.materials_needed = []


class TeachingScriptGenerator:
    """教学文稿生成器 - 专注于PPT页面对应的教学文稿生成"""
    
    def __init__(self, config: Dict[str, Any], kb_manager: KnowledgeBaseManager):
        self.config = config
        self.kb_manager = kb_manager
        self.llm_client = LLMClient(config)
        self.embedding_client = EmbeddingClient(config)
        
        # 存储路径
        self.storage_path = Path(config["knowledge_base"]["storage_path"]) / "lesson_plans"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 临时知识库名称
        self.temp_kb_name = "_temp_lesson_plan_kb"
        
        logging.info("教案设计生成器初始化完成")
    
    def parse_ppt_pdf(self, pdf_path: str) -> List[PPTSlide]:
        """解析PPT PDF文件
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            PPT幻灯片列表
        """
        slides = []
        
        try:
            doc = fitz.open(pdf_path)
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # 提取文本
                text = page.get_text()
                
                # 提取文本块
                blocks = page.get_text("dict")["blocks"]
                
                # 分析文本结构
                title = ""
                content_lines = []
                bullet_points = []
                
                for block in blocks:
                    if "lines" in block:
                        for line in block["lines"]:
                            line_text = ""
                            for span in line["spans"]:
                                line_text += span["text"]
                            
                            line_text = line_text.strip()
                            if line_text:
                                # 判断是否为标题（通常字体较大或在页面顶部）
                                if not title and len(line_text) < 100:
                                    title = line_text
                                elif line_text.startswith(('•', '·', '-', '1.', '2.', '3.')):
                                    bullet_points.append(line_text)
                                else:
                                    content_lines.append(line_text)
                
                # 创建幻灯片对象
                slide = PPTSlide(
                    page_number=page_num + 1,
                    title=title or f"第{page_num + 1}页",
                    content="\n".join(content_lines),
                    images=[],  # 暂不处理图片
                    bullet_points=bullet_points
                )
                
                slides.append(slide)
            
            doc.close()
            logging.info(f"成功解析PPT PDF，共{len(slides)}页")
            
        except Exception as e:
            logging.error(f"解析PPT PDF失败: {e}")
            raise
        
        return slides
    
    def parse_markdown_outline(self, md_path: str) -> str:
        """解析Markdown教学大纲
        
        Args:
            md_path: Markdown文件路径
            
        Returns:
            大纲内容
        """
        try:
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logging.info(f"成功解析Markdown大纲，长度: {len(content)}字符")
            return content
            
        except Exception as e:
            logging.error(f"解析Markdown大纲失败: {e}")
            raise
    
    def extract_key_points(self, slides: List[PPTSlide], outline: str = "") -> Dict[int, str]:
        """提取PPT要点总结
        
        Args:
            slides: PPT幻灯片列表
            outline: 教学大纲（可选）
            
        Returns:
            按页数编码的要点字典
        """
        key_points = {}
        
        # 构建提示词
        prompt_template = """
你是一位专业的教学设计专家。请分析以下PPT内容，为每一页提取关键要点。

要求：
1. 为每页PPT提取3-5个核心要点
2. 要点应该简洁明了，突出重点
3. 考虑教学逻辑和知识点的连贯性
4. 如果有教学大纲，请结合大纲内容

{outline_section}

PPT内容分析：

{slides_content}

请按以下格式输出每页的要点：

第X页要点：
- 要点1
- 要点2
- 要点3
...
"""
        
        # 准备大纲部分
        outline_section = ""
        if outline:
            outline_section = f"教学大纲：\n{outline}\n"
        
        # 准备幻灯片内容
        slides_content = ""
        for slide in slides:
            slides_content += f"\n第{slide.page_number}页：{slide.title}\n"
            slides_content += f"内容：{slide.content}\n"
            if slide.bullet_points:
                slides_content += f"要点：{'; '.join(slide.bullet_points)}\n"
            slides_content += "-" * 40 + "\n"
        
        # 构建完整提示词
        prompt = prompt_template.format(
            outline_section=outline_section,
            slides_content=slides_content
        )
        
        try:
            # 调用LLM生成要点
            response = self.llm_client.generate(prompt)
            
            # 解析响应，提取每页要点
            lines = response.split('\n')
            current_page = None
            current_points = []
            
            for line in lines:
                line = line.strip()
                if line.startswith('第') and '页要点' in line:
                    # 保存上一页的要点
                    if current_page is not None and current_points:
                        key_points[current_page] = '\n'.join(current_points)
                    
                    # 提取页码
                    try:
                        page_num = int(line.split('第')[1].split('页')[0])
                        current_page = page_num
                        current_points = []
                    except:
                        continue
                        
                elif line.startswith('-') or line.startswith('•'):
                    if current_page is not None:
                        current_points.append(line)
            
            # 保存最后一页的要点
            if current_page is not None and current_points:
                key_points[current_page] = '\n'.join(current_points)
            
            logging.info(f"成功提取{len(key_points)}页的要点")
            
        except Exception as e:
            logging.error(f"提取要点失败: {e}")
            # 如果LLM调用失败，使用简单的规则提取
            for slide in slides:
                points = []
                if slide.title:
                    points.append(f"- 主题：{slide.title}")
                if slide.bullet_points:
                    points.extend(slide.bullet_points)
                elif slide.content:
                    # 简单分割内容作为要点
                    content_lines = slide.content.split('\n')[:3]
                    for line in content_lines:
                        if line.strip():
                            points.append(f"- {line.strip()}")
                
                key_points[slide.page_number] = '\n'.join(points)
        
        return key_points
    
    def generate_teaching_script(self, key_points: Dict[int, str], agent_name: str = "默认助手",
                                subject: str = "", grade_level: str = "", 
                                additional_context: str = "", progress_callback=None) -> TeachingScript:
        """根据PPT要点生成教学文稿 - 采用分页生成策略确保每页都有讲稿
        
        Args:
            key_points: 按页数编码的要点字典
            agent_name: 智能体名称
            subject: 学科
            grade_level: 年级
            additional_context: 额外上下文
            
        Returns:
            教学文稿
        """
        # 获取智能体配置
        agent = self.kb_manager.agent_manager.get_agent(agent_name)
        if not agent:
            agent_name = "默认助手"
            agent = self.kb_manager.agent_manager.get_agent(agent_name)
        
        try:
            # 采用分页生成策略，为每一页单独生成讲稿
            ppt_scripts = self._generate_scripts_by_pages(key_points, agent, subject, grade_level, additional_context, progress_callback)
            
            # 生成课程概览信息
            course_info = self._generate_course_overview(key_points, agent, subject, grade_level, additional_context)
            
            lesson_plan = TeachingScript(
                title=course_info.get('title', f"{subject or '课程'}教学讲稿"),
                subject=subject or "通用课程",
                grade_level=grade_level or "适龄学生",
                total_duration=self._calculate_total_duration(ppt_scripts),
                ppt_scripts=ppt_scripts,
                course_overview=course_info.get('overview', '基于PPT内容的系统化教学讲稿'),
                learning_objectives=course_info.get('objectives', self._extract_objectives_from_scripts(ppt_scripts)),
                materials_needed=course_info.get('materials', ["PPT课件", "教学设备"]),
                created_at=datetime.now().isoformat()
            )
            
            logging.info(f"成功生成教案：{lesson_plan.title}")
            return lesson_plan
            
        except Exception as e:
            logging.error(f"生成教案失败: {e}")
            # 返回基础教案模板
            return self._create_basic_teaching_script(key_points, subject, grade_level)
    
    def _generate_scripts_by_pages(self, key_points: Dict[int, str], agent, 
                                 subject: str = None, grade_level: str = None, 
                                 additional_context: str = None, progress_callback=None) -> List[PPTScript]:
        """
        分页生成策略：每5页一组生成讲稿，确保不跳页且避免内容过长
        """
        ppt_scripts = []
        total_pages = len(key_points)
        page_numbers = sorted(key_points.keys())
        
        # 按5页一组进行分批生成
        batch_size = 5
        total_batches = (len(page_numbers) + batch_size - 1) // batch_size
        
        print(f"[教案生成] 开始按批次生成讲稿")
        print(f"[教案生成] 总页数: {len(page_numbers)}页，分为{total_batches}个批次")
        print(f"[教案生成] 每批次处理{batch_size}页")
        
        for batch_idx, i in enumerate(range(0, len(page_numbers), batch_size)):
            batch_pages = page_numbers[i:i + batch_size]
            batch_key_points = {page_num: key_points[page_num] for page_num in batch_pages}
            
            current_batch = batch_idx + 1
            message = f"正在生成第{batch_pages[0]}-{batch_pages[-1]}页讲稿"
            
            print(f"[教案生成] 正在处理第{current_batch}/{total_batches}批次 (第{batch_pages[0]}-{batch_pages[-1]}页)")
            
            # 调用进度回调
            if progress_callback:
                progress_callback(current_batch, total_batches, message)
            
            try:
                print(f"{message}...")
                # 为当前批次生成讲稿
                batch_scripts = self._generate_batch_scripts(
                    batch_key_points, agent, subject, grade_level, additional_context, total_pages
                )
                ppt_scripts.extend(batch_scripts)
                print(f"[教案生成] 第{current_batch}批次生成成功，获得{len(batch_scripts)}个讲稿")
                
            except Exception as e:
                print(f"生成第{batch_pages[0]}-{batch_pages[-1]}页讲稿时出错: {e}")
                print(f"[教案生成] 第{current_batch}批次生成失败: {e}")
                # 为失败的批次创建基础讲稿
                for page_num in batch_pages:
                    ppt_scripts.append(self._create_basic_script(page_num, key_points[page_num]))
        
        # 按页码排序确保顺序正确
        ppt_scripts.sort(key=lambda x: x.page_number)
        return ppt_scripts
    
    def _generate_batch_scripts(self, batch_key_points: Dict[int, str], agent, 
                              subject: str, grade_level: str, additional_context: str, 
                              total_pages: int) -> List[PPTScript]:
        """
        为一批页面（最多5页）生成讲稿
        """
        page_numbers = sorted(batch_key_points.keys())
        start_page = page_numbers[0]
        end_page = page_numbers[-1]
        
        prompt_template = """
{agent_prompt}

现在请你为PPT的第{start_page}-{end_page}页（共{total_pages}页）生成完整的教学讲稿。

学科：{subject}
年级：{grade_level}

本批次页面内容要点：
{batch_content}

{additional_context_section}

请为每一页PPT生成详细的教学讲稿，严格按照以下格式：

=== 第X页讲稿 ===
页面标题：[根据内容提取的页面标题]
讲解时间：[预计时间，如3-5分钟]

完整讲稿：
[这里写老师在这一页要说的所有话，包括：
- 开场引入语（如果是第1页）或承接上页的过渡语
- 知识点详细讲解
- 举例说明
- 与学生的互动对话
- 重点强调
- 过渡到下一页的衔接语（如果不是最后一页）]

重点提示：
- [本页的教学重点1]
- [本页的教学重点2]

教学技巧：
- [针对本页内容的教学建议1]
- [针对本页内容的教学建议2]

请确保：
1. 必须为第{start_page}到第{end_page}页的每一页都生成讲稿
2. 不能跳过任何页面
3. 语言自然流畅，符合口语表达习惯
4. 包含完整的师生互动对话
5. 有明确的知识点讲解和举例
6. 体现你的专业特色和教学风格
7. 内容充实，每页能够支撑3-8分钟的讲解
8. 与前后页面内容有良好的衔接
"""
        
        # 准备批次内容
        batch_content = ""
        for page_num in page_numbers:
            batch_content += f"\n第{page_num}页要点：\n{batch_key_points[page_num]}\n"
        
        # 准备额外上下文
        additional_context_section = ""
        if additional_context:
            additional_context_section = f"\n额外要求和背景：\n{additional_context}\n"
        
        # 构建完整提示词
        prompt = prompt_template.format(
            agent_prompt=agent.system_prompt if agent else "你是一位经验丰富的教师。",
            start_page=start_page,
            end_page=end_page,
            total_pages=total_pages,
            subject=subject or "通用课程",
            grade_level=grade_level or "适龄学生",
            batch_content=batch_content,
            additional_context_section=additional_context_section
        )
        
        try:
            # 调用LLM生成批次讲稿
            response = self.llm_client.generate(prompt, temperature=agent.temperature if agent else 0.7)
            
            # 解析批次讲稿
            return self._parse_batch_response(response, batch_key_points)
            
        except Exception as e:
            print(f"生成第{start_page}-{end_page}页讲稿时出错: {e}")
            # 返回基础讲稿
            return [self._create_basic_script(page_num, content) for page_num, content in batch_key_points.items()]
    
    def _generate_single_page_script(self, page_num: int, page_content: str, agent, 
                                   subject: str, grade_level: str, additional_context: str, 
                                   total_pages: int) -> Optional[PPTScript]:
        """
        为单页生成详细讲稿
        """
        prompt_template = """
{agent_prompt}

现在请你为PPT的第{page_num}页（共{total_pages}页）生成完整的教学讲稿。

学科：{subject}
年级：{grade_level}

第{page_num}页内容要点：
{page_content}

{additional_context_section}

请按以下格式生成这一页的教学讲稿：

页面标题：[根据内容提取的页面标题]
讲解时间：[预计时间，如3-5分钟]

完整讲稿：
[这里写老师在这一页要说的所有话，包括：
- 开场引入语（如果是第1页）或承接上页的过渡语
- 知识点详细讲解
- 举例说明
- 与学生的互动对话
- 重点强调
- 过渡到下一页的衔接语（如果不是最后一页）]

重点提示：
- [本页的教学重点1]
- [本页的教学重点2]

教学技巧：
- [针对本页内容的教学建议1]
- [针对本页内容的教学建议2]

请确保讲稿：
- 语言自然流畅，符合口语表达习惯
- 包含完整的师生互动对话
- 有明确的知识点讲解和举例
- 体现你的专业特色和教学风格
- 内容充实，能够支撑3-8分钟的讲解
- 与前后页面内容有良好的衔接
"""
        
        # 准备额外上下文
        additional_context_section = ""
        if additional_context:
            additional_context_section = f"\n额外要求和背景：\n{additional_context}\n"
        
        # 构建完整提示词
        prompt = prompt_template.format(
            agent_prompt=agent.system_prompt if agent else "你是一位经验丰富的教师。",
            page_num=page_num,
            total_pages=total_pages,
            subject=subject or "通用课程",
            grade_level=grade_level or "适龄学生",
            page_content=page_content,
            additional_context_section=additional_context_section
        )
        
        try:
            # 调用LLM生成单页讲稿
            response = self.llm_client.generate(prompt, temperature=agent.temperature if agent else 0.7)
            
            # 解析单页讲稿
            return self._parse_single_page_response(response, page_num, page_content)
            
        except Exception as e:
            print(f"生成第{page_num}页讲稿时出错: {e}")
            return None
    
    def _parse_batch_response(self, response: str, batch_key_points: Dict[int, str]) -> List[PPTScript]:
        """
        解析批量生成的讲稿响应
        """
        scripts = []
        page_numbers = sorted(batch_key_points.keys())
        
        # 按页面分割响应
        sections = re.split(r'=== 第(\d+)页讲稿 ===', response)
        
        # 处理分割后的内容
        for i in range(1, len(sections), 2):
            if i + 1 < len(sections):
                page_num = int(sections[i])
                content = sections[i + 1].strip()
                
                if page_num in page_numbers:
                    script = self._parse_page_content(content, page_num)
                    if script:
                        scripts.append(script)
        
        # 确保所有页面都有讲稿
        existing_pages = {script.page_number for script in scripts}
        for page_num in page_numbers:
            if page_num not in existing_pages:
                # 创建基础讲稿
                basic_script = self._create_basic_script(page_num, batch_key_points[page_num])
                scripts.append(basic_script)
        
        # 按页码排序
        scripts.sort(key=lambda x: x.page_number)
        return scripts
    
    def _parse_page_content(self, content: str, page_num: int) -> Optional[PPTScript]:
        """
        解析单页内容
        """
        try:
            lines = content.split('\n')
            page_title = ""
            estimated_time = ""
            script_content = ""
            key_points = []
            teaching_tips = []
            
            current_section = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith('页面标题：'):
                    page_title = line.replace('页面标题：', '').strip()
                elif line.startswith('讲解时间：'):
                    estimated_time = line.replace('讲解时间：', '').strip()
                elif line == '完整讲稿：':
                    current_section = 'script'
                elif line == '重点提示：':
                    current_section = 'key_points'
                elif line == '教学技巧：':
                    current_section = 'teaching_tips'
                elif line.startswith('- '):
                    if current_section == 'key_points':
                        key_points.append(line[2:].strip())
                    elif current_section == 'teaching_tips':
                        teaching_tips.append(line[2:].strip())
                else:
                    if current_section == 'script':
                        if script_content:
                            script_content += '\n' + line
                        else:
                            script_content = line
            
            return PPTScript(
                page_number=page_num,
                page_title=page_title or f"第{page_num}页",
                script_content=script_content or "请参考页面内容进行讲解。",
                key_points=key_points,
                estimated_time=estimated_time or "3-5分钟",
                teaching_tips=teaching_tips
            )
            
        except Exception as e:
            print(f"解析第{page_num}页内容时出错: {e}")
            return None
    
    def _parse_single_page_response(self, response: str, page_num: int, page_content: str) -> Optional[PPTScript]:
        """
        解析单页讲稿响应
        """
        lines = response.strip().split('\n')
        
        title = f"第{page_num}页"
        estimated_time = "5分钟"
        script_content = ""
        key_points = []
        teaching_tips = []
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith("页面标题："):
                title = line.replace("页面标题：", "").strip()
            elif line.startswith("讲解时间："):
                estimated_time = line.replace("讲解时间：", "").strip()
            elif line == "完整讲稿：":
                current_section = "script"
            elif line == "重点提示：":
                current_section = "points"
            elif line == "教学技巧：":
                current_section = "tips"
            elif line.startswith("- "):
                content = line[2:].strip()
                if current_section == "points":
                    key_points.append(content)
                elif current_section == "tips":
                    teaching_tips.append(content)
            elif current_section == "script":
                if script_content:
                    script_content += "\n" + line
                else:
                    script_content = line
        
        # 如果没有解析到完整讲稿，使用页面内容创建基础讲稿
        if not script_content:
            script_content = f"现在我们来学习第{page_num}页的内容。{page_content}"
        
        return PPTScript(
             page_number=page_num,
             page_title=title,
             script_content=script_content,
             key_points=key_points,
             estimated_time=estimated_time,
             teaching_tips=teaching_tips
         )
    
    def _create_basic_script(self, page_num: int, page_content: str) -> PPTScript:
        """
        创建基础讲稿作为备选
        """
        return PPTScript(
             page_number=page_num,
             page_title=f"第{page_num}页",
             script_content=f"现在我们来学习第{page_num}页的内容。{page_content}。请大家仔细观察这一页的要点，我们一起来分析和讨论。",
             key_points=["理解本页核心概念", "掌握相关知识点"],
             estimated_time="5分钟",
             teaching_tips=["引导学生思考", "结合实际例子说明"]
         )
    
    def _extract_title(self, text: str) -> Optional[str]:
        """从生成的文本中提取标题"""
        lines = text.split('\n')
        for line in lines[:10]:  # 只检查前10行
            line = line.strip()
            if '标题' in line or '课题' in line:
                # 提取冒号后的内容
                if '：' in line:
                    return line.split('：', 1)[1].strip()
                elif ':' in line:
                    return line.split(':', 1)[1].strip()
        return None
    
    def _extract_objectives(self, text: str) -> List[str]:
        """提取教学目标"""
        objectives = []
        lines = text.split('\n')
        in_objectives = False
        
        for line in lines:
            line = line.strip()
            if '教学目标' in line:
                in_objectives = True
                continue
            elif in_objectives:
                if line.startswith(('1.', '2.', '3.', '4.', '5.', '-', '•')):
                    objectives.append(line)
                elif line and not line.startswith(('1.', '2.', '3.', '4.', '5.', '-', '•')) and len(objectives) > 0:
                    break
        
        return objectives[:5]  # 最多5个目标
    
    def _extract_materials(self, text: str) -> List[str]:
        """提取教学材料"""
        materials = []
        lines = text.split('\n')
        in_materials = False
        
        for line in lines:
            line = line.strip()
            if '教学材料' in line or '教学准备' in line:
                in_materials = True
                continue
            elif in_materials:
                if line.startswith(('1.', '2.', '3.', '4.', '5.', '-', '•')):
                    materials.append(line)
                elif line and not line.startswith(('1.', '2.', '3.', '4.', '5.', '-', '•')) and len(materials) > 0:
                    break
        
        return materials
    
    # 注意：_extract_sections方法已移除，新的TeachingScript结构专注于PPT页面讲稿
    
    def _extract_assessment(self, text: str) -> str:
        """提取评估方式"""
        return "课堂观察、提问互动、练习反馈相结合的多元评估"
    
    def _extract_ppt_scripts(self, text: str, key_points: List[PPTSlide]) -> List[PPTScript]:
        """从生成的文本中提取PPT讲稿"""
        scripts = []
        lines = text.split('\n')
        current_script = None
        current_section = None
        script_content = []
        key_points_list = []
        teaching_tips = []
        
        for line in lines:
            line = line.strip()
            
            # 检测新的页面讲稿开始
            if line.startswith('=== 第') and '页讲稿' in line:
                # 保存前一个讲稿
                if current_script:
                    current_script['script_content'] = '\n'.join(script_content).strip()
                    current_script['key_points'] = key_points_list
                    current_script['teaching_tips'] = teaching_tips
                    scripts.append(PPTScript(**current_script))
                
                # 开始新的讲稿
                page_num = self._extract_page_number(line)
                current_script = {
                    'page_number': page_num,
                    'page_title': '',
                    'script_content': '',
                    'key_points': [],
                    'estimated_time': '5分钟',
                    'teaching_tips': []
                }
                current_section = 'header'
                script_content = []
                key_points_list = []
                teaching_tips = []
                continue
            
            if not current_script:
                continue
                
            # 解析页面标题
            if line.startswith('页面标题：'):
                current_script['page_title'] = line.replace('页面标题：', '').strip()
                continue
            
            # 解析讲解时间
            if line.startswith('讲解时间：'):
                current_script['estimated_time'] = line.replace('讲解时间：', '').strip()
                continue
            
            # 检测不同部分
            if line == '完整讲稿：':
                current_section = 'script'
                continue
            elif line == '重点提示：':
                current_section = 'key_points'
                continue
            elif line == '教学技巧：':
                current_section = 'tips'
                continue
            
            # 根据当前部分添加内容
            if current_section == 'script' and line:
                script_content.append(line)
            elif current_section == 'key_points' and line.startswith('-'):
                key_points_list.append(line[1:].strip())
            elif current_section == 'tips' and line.startswith('-'):
                teaching_tips.append(line[1:].strip())
        
        # 保存最后一个讲稿
        if current_script:
            current_script['script_content'] = '\n'.join(script_content).strip()
            current_script['key_points'] = key_points_list
            current_script['teaching_tips'] = teaching_tips
            scripts.append(PPTScript(**current_script))
        
        # 如果没有解析到讲稿，根据要点字典创建基础讲稿
        if not scripts and key_points:
            for page_num, points_text in key_points.items():
                points_list = [line.strip('- ') for line in points_text.split('\n') if line.strip().startswith('-')]
                scripts.append(PPTScript(
                    page_number=page_num,
                    page_title=f"第{page_num}页",
                    script_content=f"现在我们来看第{page_num}页的内容。\n\n{points_text}",
                    key_points=points_list[:3],
                    estimated_time="3-5分钟",
                    teaching_tips=["注意与学生互动", "适当举例说明"]
                ))
        
        return scripts
    
    def _extract_page_number(self, line: str) -> int:
        """从标题行中提取页码"""
        import re
        match = re.search(r'第(\d+)页', line)
        return int(match.group(1)) if match else 1
    
    def _generate_course_overview(self, key_points: Dict[int, str], agent, 
                                subject: str, grade_level: str, additional_context: str) -> Dict[str, Any]:
        """生成课程概览信息"""
        try:
            # 构建概览生成提示词
            prompt = f"""
{agent.system_prompt if agent else "你是一位经验丰富的教师。"}

请根据以下PPT内容要点，生成课程的基本信息：

学科：{subject or "通用课程"}
年级：{grade_level or "适龄学生"}

PPT内容要点：
{chr(10).join([f"第{k}页：{v}" for k, v in key_points.items()])}

{f"额外要求：{additional_context}" if additional_context else ""}

请按以下格式输出：

课程标题：[简洁的课程标题]

课程概述：
[2-3句话描述本课程的主要内容和特点]

学习目标：
- [目标1]
- [目标2]
- [目标3]

教学材料：
- [材料1]
- [材料2]
- [材料3]
"""
            
            response = self.llm_client.generate(prompt, temperature=agent.temperature if agent else 0.7)
            return self._parse_course_overview(response)
            
        except Exception as e:
            logging.warning(f"生成课程概览失败，使用默认值: {e}")
            return {
                'title': f"{subject or '课程'}教学讲稿",
                'overview': '基于PPT内容的系统化教学讲稿',
                'objectives': self._extract_objectives_from_scripts([]),
                'materials': ["PPT课件", "教学设备"]
            }
    
    def _parse_course_overview(self, response: str) -> Dict[str, Any]:
        """解析课程概览响应"""
        lines = response.strip().split('\n')
        
        title = ""
        overview = ""
        objectives = []
        materials = []
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith("课程标题："):
                title = line.replace("课程标题：", "").strip()
            elif line == "课程概述：":
                current_section = "overview"
            elif line == "学习目标：":
                current_section = "objectives"
            elif line == "教学材料：":
                current_section = "materials"
            elif line.startswith("- "):
                content = line[2:].strip()
                if current_section == "objectives":
                    objectives.append(content)
                elif current_section == "materials":
                    materials.append(content)
            elif current_section == "overview" and line:
                if overview:
                    overview += " " + line
                else:
                    overview = line
        
        return {
            'title': title or "教学讲稿",
            'overview': overview or "基于PPT内容的系统化教学讲稿",
            'objectives': objectives or ["理解课程核心概念", "掌握相关知识点", "培养分析问题的能力"],
            'materials': materials or ["PPT课件", "教学设备"]
        }
    
    def _calculate_total_duration(self, scripts: List[PPTScript]) -> str:
        """计算总时长"""
        total_minutes = 0
        for script in scripts:
            # 从estimated_time中提取数字
            time_str = script.estimated_time
            import re
            numbers = re.findall(r'\d+', time_str)
            if numbers:
                total_minutes += int(numbers[0])
            else:
                total_minutes += 5  # 默认5分钟
        
        return f"{total_minutes}分钟"
    
    def _extract_objectives_from_scripts(self, scripts: List[PPTScript]) -> List[str]:
        """从讲稿中提取教学目标"""
        objectives = []
        for script in scripts[:3]:  # 从前3页提取目标
            if script.key_points:
                for point in script.key_points[:2]:  # 每页最多2个目标
                    if point not in objectives:
                        objectives.append(f"掌握{point}")
        
        if not objectives:
            objectives = ["理解课程核心概念", "掌握相关知识点", "培养分析问题的能力"]
        
        return objectives[:5]

    def _extract_homework(self, text: str) -> str:
        """提取作业安排"""
        return "完成课后练习题，预习下节课内容"
    
    def _extract_reflection(self, text: str) -> str:
        """提取教学反思"""
        return "关注学生参与度，调整教学节奏，优化教学方法"
    
    def _create_basic_teaching_script(self, key_points: Dict[int, str], 
                                     subject: str, grade_level: str) -> TeachingScript:
        """创建基础教案模板"""
        # 为每个要点创建基础讲稿
        ppt_scripts = []
        for page_num, points in key_points.items():
            ppt_scripts.append(PPTScript(
                page_number=page_num,
                page_title=f"第{page_num}页",
                script_content=f"现在我们来看第{page_num}页的内容。\n\n{points}",
                key_points=points.split('\n')[:3],
                estimated_time="3-5分钟",
                teaching_tips=["注意与学生互动", "适当举例说明"]
            ))
        
        return TeachingScript(
            title=f"{subject}教学讲稿",
            subject=subject or "通用课程",
            grade_level=grade_level or "适龄学生",
            total_duration=f"{len(ppt_scripts) * 5}分钟",
            ppt_scripts=ppt_scripts,
            course_overview="基于PPT内容的系统化教学讲稿",
            learning_objectives=[
                "掌握本课重点知识",
                "理解核心概念",
                "培养学习兴趣"
            ],
            materials_needed=[
                "PPT课件",
                "教学设备",
                "练习材料"
            ],
            created_at=datetime.now().isoformat()
        )
    
    def save_teaching_script(self, teaching_script: TeachingScript, filename: str = None) -> str:
        """保存教学文稿到文件
        
        Args:
            teaching_script: 教学文稿对象
            filename: 文件名（可选）
            
        Returns:
            保存的文件路径
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"lesson_plan_{timestamp}.json"
        
        file_path = self.storage_path / filename
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(teaching_script), f, ensure_ascii=False, indent=2)
            
            logging.info(f"教案已保存到: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logging.error(f"保存教案失败: {e}")
            raise
    
    def load_teaching_script(self, file_path: str) -> TeachingScript:
        """从文件加载教学文稿
        
        Args:
            file_path: 文件路径
            
        Returns:
            教学文稿对象
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 重构PPTScript对象
            ppt_scripts = []
            for script_data in data.get('ppt_scripts', []):
                ppt_scripts.append(PPTScript(**script_data))
            data['ppt_scripts'] = ppt_scripts
            
            # 兼容性处理：将旧的LessonPlan字段映射到TeachingScript
            if 'total_duration' not in data and 'duration' in data:
                data['total_duration'] = data['duration']
                # 移除旧字段避免冲突
                data.pop('duration', None)
            if 'learning_objectives' not in data and 'objectives' in data:
                data['learning_objectives'] = data['objectives']
            if 'materials_needed' not in data and 'materials' in data:
                data['materials_needed'] = data['materials']
            if 'course_overview' not in data:
                data['course_overview'] = "基于PPT内容的系统化教学讲稿"
            
            # 清理可能导致冲突的旧字段
            old_fields = ['duration']  # 可以根据需要添加更多旧字段
            for field in old_fields:
                data.pop(field, None)
            
            return TeachingScript(**data)
            
        except Exception as e:
            logging.error(f"加载教案失败: {e}")
            raise
    
    def list_teaching_scripts(self) -> List[Dict[str, Any]]:
        """列出所有保存的教学文稿
        
        Returns:
            教学文稿信息列表
        """
        teaching_scripts = []
        
        try:
            for file_path in self.storage_path.glob("*.json"):
                try:
                    teaching_script = self.load_teaching_script(str(file_path))
                    teaching_scripts.append({
                        "filename": file_path.name,
                        "title": teaching_script.title,
                        "subject": teaching_script.subject,
                        "grade_level": teaching_script.grade_level,
                        "created_at": teaching_script.created_at,
                        "file_path": str(file_path)
                    })
                except Exception as e:
                    logging.warning(f"跳过损坏的教案文件 {file_path}: {e}")
                    continue
            
            # 按创建时间排序
            teaching_scripts.sort(key=lambda x: x['created_at'], reverse=True)
            
        except Exception as e:
            logging.error(f"列出教案失败: {e}")
        
        return teaching_scripts
    
    def generate_teaching_script_workflow(self, ppt_path: str = None, outline_path: str = None,
                                        agent_name: str = "默认助手", subject: str = "",
                                        grade_level: str = "", additional_context: str = "",
                                        progress_callback=None) -> Tuple[TeachingScript, str]:
        """完整的教学文稿生成工作流
        
        Args:
            ppt_path: PPT PDF文件路径
            outline_path: Markdown大纲文件路径
            agent_name: 智能体名称
            subject: 学科
            grade_level: 年级
            additional_context: 额外上下文
            
        Returns:
            (教学文稿对象, 保存路径)
        """
        try:
            print(f"[教案生成] 开始教学文稿生成工作流")
            print(f"[教案生成] 智能体: {agent_name}")
            print(f"[教案生成] 学科: {subject}，年级: {grade_level}")
            
            # 1. 解析输入文件
            slides = []
            outline = ""
            
            if ppt_path:
                print(f"[教案生成] 正在解析PPT文件: {ppt_path}")
                logging.info(f"解析PPT文件: {ppt_path}")
                slides = self.parse_ppt_pdf(ppt_path)
                print(f"[教案生成] PPT解析完成，共{len(slides)}页")
            
            if outline_path:
                print(f"[教案生成] 正在解析大纲文件: {outline_path}")
                logging.info(f"解析大纲文件: {outline_path}")
                outline = self.parse_markdown_outline(outline_path)
                print(f"[教案生成] 大纲解析完成，长度: {len(outline)}字符")
            
            if not slides and not outline:
                raise ValueError("至少需要提供PPT文件或大纲文件")
            
            # 2. 提取要点
            print(f"[教案生成] 开始提取教学要点")
            logging.info("提取教学要点...")
            if slides:
                key_points = self.extract_key_points(slides, outline)
                print(f"[教案生成] 教学要点提取完成，共{len(key_points)}页要点")
            else:
                # 如果只有大纲，创建虚拟要点
                key_points = {1: f"教学大纲要点：\n{outline[:500]}..."}
                print(f"[教案生成] 基于大纲创建虚拟要点")

            # 3. 生成教学文稿
            print(f"[教案生成] 开始生成教学文稿")
            logging.info(f"使用智能体 '{agent_name}' 生成教学文稿...")
            teaching_script = self.generate_teaching_script(
                key_points=key_points,
                agent_name=agent_name,
                subject=subject,
                grade_level=grade_level,
                additional_context=additional_context,
                progress_callback=progress_callback
            )

            # 4. 保存教学文稿
            print(f"[教案生成] 开始保存教学文稿")
            logging.info("保存教学文稿...")
            file_path = self.save_teaching_script(teaching_script)

            print(f"[教案生成] 教学文稿生成完成！")
            print(f"[教案生成] 保存路径: {file_path}")
            print(f"[教案生成] 生成的讲稿数量: {len(teaching_script.ppt_scripts) if hasattr(teaching_script, 'ppt_scripts') else 0}")
            
            logging.info(f"教学文稿生成工作流完成，保存到: {file_path}")
            return teaching_script, file_path
            
        except Exception as e:
            logging.error(f"教学文稿生成工作流失败: {e}")
            raise