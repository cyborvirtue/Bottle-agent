# 🍾 Bottle-Agent

一个轻量级的学术论文搜索与RAG问答系统，支持智能论文检索和本地知识库构建。

## ✨ 功能特性

### 📚 论文智能搜索
- 支持arXiv和Semantic Scholar API
- LLM驱动的查询优化
- 自然语言搜索支持
- 多源论文聚合展示

### 🧠 本地RAG知识库
- 支持PDF、TXT、Markdown、DOCX文档
- 基于FAISS的向量检索
- 智能文档分块和嵌入
- 上下文感知的问答系统

### 🖥️ 多种交互方式
- 命令行界面（CLI）
- Web界面（Streamlit）
- 灵活的配置管理

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd bottle_agent

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置设置

编辑 `config.yaml` 文件，设置必要的API密钥：

```yaml
llm:
  api_key: "your-openai-api-key"  # 或设置环境变量OPENAI_API_KEY

embedding:
  api_key: "your-openai-api-key"  # 同上

paper_search:
  semantic_scholar:
    api_key: "your-semantic-scholar-api-key"  # 可选
```

### 3. 运行方式

#### 命令行模式

```bash
# 启动交互式CLI
python main.py --mode cli

# 直接搜索论文
python main.py --search "transformer architecture"

# RAG问答
python main.py --rag-query "什么是注意力机制？" --kb-name "ai_papers"

# 创建知识库
python main.py --create-kb "ai_papers" --folder "/path/to/papers" --description "AI相关论文"
```

#### Web界面模式

```bash
# 启动Web界面
python main.py --mode web

# 然后在浏览器中访问 http://localhost:8501
```

## 📖 详细使用说明

### 论文搜索

支持自然语言查询，系统会自动优化搜索关键词：

```bash
# CLI示例
search> diffusion models in medical imaging

# 或在Web界面中输入查询
```

### 知识库管理

#### 创建知识库

```bash
# CLI命令
create_kb ai_papers /path/to/papers "AI相关论文集合"

# 支持的文件格式：PDF, TXT, Markdown, DOCX
```

#### 查询知识库

```bash
# CLI命令
query ai_papers "解释一下transformer的自注意力机制"
```

#### 管理知识库

```bash
# 列出所有知识库
list_kb

# 查看知识库信息
info_kb ai_papers

# 更新知识库
update_kb ai_papers

# 删除知识库
delete_kb ai_papers
```

## 🏗️ 项目结构

```
bottle_agent/
├── main.py                 # 主入口文件
├── config.yaml            # 配置文件
├── requirements.txt       # 依赖列表
├── README.md             # 项目说明
├── src/                  # 源代码目录
│   ├── __init__.py
│   ├── config/           # 配置管理
│   │   └── settings.py
│   ├── llm/              # LLM客户端
│   │   └── llm_client.py
│   ├── paper_search/     # 论文搜索
│   │   └── search_engine.py
│   ├── rag_system/       # RAG系统
│   │   ├── knowledge_base.py
│   │   ├── document_processor.py
│   │   └── embedding_client.py
│   └── ui/               # 用户界面
│       ├── cli_interface.py
│       └── web_interface.py
├── data/                 # 数据存储目录
│   ├── knowledge_bases/  # 知识库存储
│   └── cache/           # 缓存文件
└── logs/                # 日志文件
```

## ⚙️ 配置说明

### LLM配置

```yaml
llm:
  provider: "openai"        # LLM提供商
  model: "gpt-3.5-turbo"   # 模型名称
  api_key: ""              # API密钥
  max_tokens: 2048         # 最大token数
  temperature: 0.7         # 温度参数
```

### 嵌入模型配置

```yaml
embedding:
  provider: "openai"                              # openai 或 huggingface
  model: "text-embedding-ada-002"                # 模型名称
  # model: "sentence-transformers/all-MiniLM-L6-v2"  # HuggingFace示例
```

### RAG系统配置

```yaml
rag:
  document_processing:
    chunk_size: 1000        # 文档块大小
    chunk_overlap: 200      # 块重叠大小
  retrieval:
    top_k: 5               # 检索文档数量
    max_context_length: 4000  # 最大上下文长度
```

## 🔧 高级功能

### 自定义嵌入模型

支持使用HuggingFace的sentence-transformers模型：

```yaml
embedding:
  provider: "huggingface"
  model: "sentence-transformers/all-MiniLM-L6-v2"
```

### 批量文档处理

系统支持批量处理文件夹中的所有支持格式文档，自动去重和增量更新。

### 缓存机制

内置缓存机制，提高重复查询的响应速度。

## 🐛 故障排除

### 常见问题

1. **API密钥错误**
   - 确保在`config.yaml`中正确设置API密钥
   - 或设置环境变量`OPENAI_API_KEY`

2. **依赖安装失败**
   - 确保Python版本 >= 3.8
   - 使用虚拟环境避免依赖冲突

3. **文档处理失败**
   - 检查文件格式是否支持
   - 确保文件没有损坏
   - 检查文件路径是否正确

4. **Web界面无法启动**
   - 确保安装了Streamlit：`pip install streamlit`
   - 检查端口8501是否被占用

### 日志查看

日志文件位于`logs/`目录下，可以查看详细的错误信息。

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

### 开发环境设置

```bash
# 安装开发依赖
pip install pytest black flake8

# 代码格式化
black src/

# 代码检查
flake8 src/

# 运行测试
pytest
```

## 📄 许可证

MIT License

## 🙏 致谢

- [arXiv API](https://arxiv.org/help/api) - 论文数据源
- [Semantic Scholar API](https://www.semanticscholar.org/product/api) - 论文数据源
- [FAISS](https://github.com/facebookresearch/faiss) - 向量检索
- [Streamlit](https://streamlit.io/) - Web界面框架
- [OpenAI](https://openai.com/) - LLM和嵌入服务