# 🚀 Bottle-Agent 快速开始指南

## 📋 前置要求

- Python 3.8+
- OpenAI API密钥（用于LLM和嵌入）

## ⚡ 快速安装

### 1. 克隆项目

```bash
cd /Users/kalami/大三下/创新工程实践
# 项目已在 bottle_agent/ 目录中
```

### 2. 创建虚拟环境

```bash
cd bottle_agent
python -m venv venv
source venv/bin/activate  # macOS/Linux
```

### 3. 安装依赖

```bash
# 安装核心依赖
pip install -r requirements.txt

# 或者分步安装（如果遇到问题）
pip install pyyaml requests numpy scipy scikit-learn
pip install PyPDF2 python-docx markdown
pip install faiss-cpu
pip install openai
pip install transformers torch sentence-transformers
pip install streamlit  # Web界面（可选）
pip install rich click  # 命令行增强（可选）
```

### 4. 配置API密钥

编辑 `config.yaml` 文件：

**使用OpenAI：**
```yaml
llm:
  provider: "openai"
  api_key: "your-openai-api-key-here"  # 替换为您的OpenAI API密钥

embedding:
  api_key: "your-openai-api-key-here"  # 同上
```

**使用火山引擎：**
```yaml
llm:
  provider: "volcengine"
  volcengine:
    api_key: "your-ark-api-key-here"  # 替换为您的火山引擎API密钥
    model: "deepseek-r1-250120"  # 火山引擎模型ID

embedding:
  api_key: "your-openai-api-key-here"  # 嵌入模型仍使用OpenAI
```

或者设置环境变量：

```bash
# OpenAI
export OPENAI_API_KEY="your-openai-api-key-here"

# 火山引擎
export ARK_API_KEY="your-ark-api-key-here"
```

## 🎯 快速测试

### 1. 测试论文搜索

```bash
# 命令行模式
python main.py --search "transformer architecture"

# 或使用快速启动脚本
python run.py --search "diffusion models"
```

### 2. 启动交互式CLI

```bash
python main.py --mode cli
```

在CLI中尝试：
```
> search transformer attention mechanism
> help
> exit
```

### 3. 启动Web界面

```bash
python main.py --mode web
```

然后在浏览器中访问：http://localhost:8501

## 📚 创建第一个知识库

### 1. 准备文档

创建一个包含PDF、TXT或Markdown文件的文件夹：

```bash
mkdir ~/test_papers
# 将一些PDF论文放入此文件夹
```

### 2. 创建知识库

```bash
# 命令行方式
python main.py --create-kb "test_kb" --folder "~/test_papers" --description "测试知识库"

# 或在CLI中
python main.py --mode cli
> create_kb test_kb ~/test_papers "我的第一个知识库"
```

### 3. 查询知识库

```bash
# 命令行方式
python main.py --rag-query "什么是transformer？" --kb-name "test_kb"

# 或在CLI中
> query test_kb "解释一下注意力机制"
```

## 🔧 常见问题解决

### 问题1：导入错误

```bash
# 确保在项目根目录
cd bottle_agent

# 使用run.py启动
python run.py --help
```

### 问题2：API密钥错误

```bash
# 检查配置文件
cat config.yaml | grep api_key

# 或设置环境变量
export OPENAI_API_KEY="sk-..."
```

### 问题3：依赖安装失败

```bash
# 升级pip
pip install --upgrade pip

# 分别安装核心依赖
pip install pyyaml requests numpy
pip install faiss-cpu
pip install openai
```

### 问题4：FAISS安装问题（Apple Silicon Mac）

```bash
# 对于M1/M2 Mac
conda install -c conda-forge faiss-cpu
# 或
pip install faiss-cpu --no-cache-dir
```

## 📖 使用示例

### 论文搜索示例

```bash
# 搜索AI相关论文
python run.py --search "large language models GPT"

# 搜索特定领域
python run.py --search "computer vision object detection"

# 搜索最新研究
python run.py --search "diffusion models 2024"
```

### 知识库管理示例

```bash
# 列出所有知识库
python run.py --list-kb

# 查看知识库信息
python run.py --kb-info "test_kb"

# 更新知识库
python run.py --update-kb "test_kb"

# 删除知识库
python run.py --delete-kb "test_kb"
```

### RAG问答示例

```bash
# 技术问题
python run.py --rag-query "什么是自注意力机制？" --kb-name "ai_papers"

# 比较分析
python run.py --rag-query "比较CNN和Transformer的优缺点" --kb-name "dl_papers"

# 应用场景
python run.py --rag-query "扩散模型在图像生成中的应用" --kb-name "cv_papers"
```

## 🎨 Web界面功能

启动Web界面后，您可以：

1. **论文搜索**：在搜索框中输入自然语言查询
2. **RAG问答**：选择知识库并提问
3. **知识库管理**：创建、更新、删除知识库
4. **实时状态**：查看系统状态和知识库统计

## 📈 进阶配置

### 使用本地嵌入模型

编辑 `config.yaml`：

```yaml
embedding:
  provider: "huggingface"
  model: "sentence-transformers/all-MiniLM-L6-v2"
```

### 调整文档处理参数

```yaml
rag:
  document_processing:
    chunk_size: 1500  # 增加块大小
    chunk_overlap: 300  # 增加重叠
  retrieval:
    top_k: 8  # 检索更多相关文档
```

### 启用缓存

```yaml
performance:
  cache_enabled: true
  cache_ttl: 7200  # 2小时缓存
```

## 🎯 下一步

1. 阅读完整的 [README.md](README.md)
2. 探索 [配置选项](config.yaml)
3. 查看 [项目结构](README.md#项目结构)
4. 贡献代码或报告问题

## 💡 提示

- 首次使用建议先用小量文档测试
- 定期更新知识库以包含新文档
- 使用描述性的知识库名称便于管理
- Web界面提供更直观的操作体验
- 命令行模式适合批量操作和脚本化

祝您使用愉快！🎉