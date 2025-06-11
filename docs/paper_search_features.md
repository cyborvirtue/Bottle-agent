# 论文搜索功能增强

本文档介绍了新增的论文搜索功能，包括标签管理和时间范围搜索。

## 功能概述

### 1. 标签管理功能

用户可以设置感兴趣的研究领域标签，系统会自动推送该领域的最新论文。

**主要特性:**
- 添加、删除、更新和列出标签
- 为每个标签设置关键词和arXiv分类
- 自动检查匹配标签的新论文
- 通知历史管理

### 2. 时间范围搜索功能

支持按时间范围搜索论文，可以查找特定时间段内发布的论文。

**主要特性:**
- 按天数回溯搜索（如最近7天、30天）
- 按具体日期范围搜索
- 支持arXiv和Semantic Scholar两个数据源

## 使用方法

### 标签管理

#### 添加标签
```bash
python main.py --tag-action add --tag-name "机器学习" --tag-keywords "machine learning,deep learning,neural network" --tag-categories "cs.LG,cs.AI"
```

#### 列出所有标签
```bash
python main.py --tag-action list
```

#### 更新标签
```bash
python main.py --tag-action update --tag-name "机器学习" --tag-keywords "machine learning,deep learning,transformer" --tag-categories "cs.LG,cs.AI,cs.CL"
```

#### 删除标签
```bash
python main.py --tag-action remove --tag-name "机器学习"
```

### 时间范围搜索

#### 搜索最近N天的论文
```bash
# 搜索最近7天的transformer相关论文
python main.py --search-time "transformer" --days 7

# 搜索最近30天的attention mechanism相关论文
python main.py --search-time "attention mechanism" --days 30
```

#### 搜索特定日期范围的论文
```bash
# 搜索2024年的深度学习论文
python main.py --search "deep learning" --start-date "2024-01-01" --end-date "2024-12-31"

# 搜索2024年上半年的NLP论文
python main.py --search "natural language processing" --start-date "2024-01-01" --end-date "2024-06-30"
```

### 通知管理

#### 检查新论文推送
```bash
python main.py --check-notifications
```

#### 查看通知历史
```bash
python main.py --list-notifications
```

## 配置说明

在 `config.yaml` 文件中，新增了以下配置选项：

```yaml
paper_search:
  notifications:
    check_interval_hours: 24  # 检查新论文的间隔（小时）
    max_notifications: 100    # 最大保存通知数量
    auto_cleanup_days: 30     # 自动清理旧通知的天数
    enable_auto_check: false  # 是否启用自动检查（需要定时任务支持）
```

## 数据存储

- **标签数据**: 存储在 `data/tags.json` 文件中
- **通知历史**: 存储在 `data/notifications.json` 文件中
- **最后检查时间**: 存储在 `data/last_check.json` 文件中

## 使用示例

### 场景1: 关注深度学习领域

1. 添加深度学习标签：
```bash
python main.py --tag-action add --tag-name "深度学习" --tag-keywords "deep learning,neural network,CNN,RNN,transformer" --tag-categories "cs.LG,cs.AI,cs.CV"
```

2. 检查新论文：
```bash
python main.py --check-notifications
```

### 场景2: 查找最新的transformer论文

```bash
# 查找最近一周的transformer论文
python main.py --search-time "transformer" --days 7
```

### 场景3: 研究特定时期的发展

```bash
# 查找2023年的BERT相关论文
python main.py --search "BERT" --start-date "2023-01-01" --end-date "2023-12-31"
```

## 注意事项

1. **API限制**: arXiv和Semantic Scholar都有API调用频率限制，请合理使用
2. **日期格式**: 日期格式为 `YYYY-MM-DD`
3. **关键词**: 多个关键词用逗号分隔，建议使用英文关键词
4. **分类**: arXiv分类代码可以在 [arXiv分类列表](https://arxiv.org/category_taxonomy) 查找
5. **网络连接**: 功能需要稳定的网络连接来访问论文数据库

## 故障排除

### 常见问题

1. **无法找到论文**: 检查关键词拼写和网络连接
2. **日期格式错误**: 确保使用 `YYYY-MM-DD` 格式
3. **标签不匹配**: 检查关键词和分类设置是否正确
4. **API错误**: 可能是网络问题或API限制，稍后重试

### 调试模式

可以在代码中启用调试模式来查看详细的执行信息：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 扩展功能

未来可以考虑添加的功能：

1. **邮件通知**: 自动发送新论文通知邮件
2. **RSS订阅**: 生成RSS源供订阅
3. **论文摘要**: 使用AI生成论文摘要
4. **相关性评分**: 根据用户兴趣对论文进行评分
5. **定时任务**: 自动定期检查新论文