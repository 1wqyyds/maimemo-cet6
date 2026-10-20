# 墨墨背单词 OpenAPI 快捷工具箱

本项目已根据官方 OpenAPI 规范，结合你的 API Token 配置完毕，开箱即用。

---

## 🛠️ 文件结构

- `.env`：保存你的 API Token 与请求地址。
- `maimemo_client.py`：完整的 Python SDK 客户端封装。
- `cli.py`：方便好用的命令行交互工具。

---

## 🚀 常用命令行操作

打开终端，进入当前目录 `d:\Personal\Desktop\Codex1\Gemini\墨墨背单词`：

### 1. 查看今日背词进度
```bash
python cli.py progress
```
> 输出已背单词数、今日规划单词总数、学习总时长。

### 2. 查询单词（支持查词与批量查词）
```bash
# 查询单个单词
python cli.py search apple

# 查询多个单词
python cli.py search apple banana orange resilience
```

### 3. 将生词批量添加到学习计划
```bash
# 直接命令行输入添加
python cli.py add-words deliberate contemplate persevere

# 从文本文件批量导入添加（每行一个单词）
python cli.py add-words --file words.txt

# 添加并一并加入提前复习
python cli.py add-words deliberate --advance
```

### 4. 管理云词本
```bash
# 查看所有云词本
python cli.py notepads

# 创建新云词本（文本模式或章节模式）
python cli.py create-notepad --title "考研核心词" --content "# 第一章\napple\nbanana\n# 第二章\norange\npeach" --tags 考研 英语
```

---

## 🐍 在 Python 代码中使用

```python
from maimemo_client import MaiMemoClient

client = MaiMemoClient()

# 1. 查询单词
voc = client.get_vocabulary("apple")
print(voc)

# 2. 获取今日背词进度
progress = client.get_study_progress()
print(progress)

# 3. 批量添加单词
res = client.add_words_by_spellings(["hypothesis", "paradigm"])
print("添加结果:", res)
```
