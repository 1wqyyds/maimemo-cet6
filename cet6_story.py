"""
六级真题语境·今日单词串记微小说生成器
结合墨墨背单词 OpenAPI + AI 大模型 + PushPlus 微信推送
"""

import os
import sys
import json
import argparse
import webbrowser
import requests
from typing import List, Dict, Any, Optional

# 控制台编码安全
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from maimemo_client import MaiMemoClient

# 内置六级高频核心词样例（当今天墨墨 App 尚未背词或未同步时用于演示体验）
SAMPLE_CET6_WORDS = [
    "deteriorate",
    "susceptible",
    "unprecedented",
    "plausible",
    "contemplate",
    "perseverance",
    "inevitable",
    "subtle",
    "speculate",
    "indispensable"
]

CET6_PROMPT_TEMPLATE = """
你是一名拥有10年大学英语六级（CET-6）命题与教学经验的资深英语名师。
请使用以下指定的六级重点词汇，撰写一篇高度契合大学英语六级深度阅读（Reading Comprehension Section C）风格的短文，帮助考生在真实语境中深度掌握这些词汇。

【指定的六级核心词汇】：
{words_str}

【生成要求】：
1. 【短文体裁】：大学英语六级高频真题题材（如科技与人工智能伦理、心理学与认知习惯、气候危机与可持续发展、现代职场与教育反思）。
2. 【语言风格】：议论文或学术说明文，句式严谨地道，适当使用非谓语动词、分词短语及从句，字数在 150 - 200 词左右。
3. 【高亮与标记】：短文中所有指定的六级核心词必须全部自然使用，且一律使用粗体并标上序号，格式如：**[1] deteriorate**。
4. 【内容模块】：
   - Module 1: 英文短文（含带序号的粗体词汇）
   - Module 2: 精准地道的中文参考译文
   - Module 3: 核心词汇六级真题考点清单（包含：单词拼写、词性与核心释义、六级常考固定搭配/Collocations、六级高频同义替换）
   - Module 4: 选词填空实战自测（针对其中 2 个重点词出 2 道六级单句填空，文末附带答案与解析）

请直接输出规范、排版优美的 Markdown 文本。
"""

def get_today_cet6_words(client: MaiMemoClient, limit: int = 15) -> List[Dict[str, Any]]:
    """
    从墨墨 API 获取今天背的单词，优先提取遗忘/模糊词和新词
    """
    try:
        items = client.get_today_items(limit=100)
    except Exception as e:
        print(f"[!] 从墨墨获取今日单词失败: {e}")
        return []

    if not items:
        return []

    # 优先级排序：FORGET > VAGUE > is_new > 其他
    def sort_key(item):
        resp = item.get("first_response", "")
        is_new = item.get("is_new", False)
        if resp == "FORGET":
            return 1
        elif resp == "VAGUE":
            return 2
        elif is_new:
            return 3
        else:
            return 4

    sorted_items = sorted(items, key=sort_key)
    return sorted_items[:limit]

def call_ai_api(prompt: str) -> Optional[str]:
    """
    调用用户配置的 AI API（兼容 OpenAI 规范，支持 DeepSeek、Gemini、SiliconFlow、Kimi 等）
    """
    api_key = os.getenv("AI_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY")
    base_url = os.getenv("AI_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
    model = os.getenv("AI_MODEL", "deepseek-chat")

    if not api_key:
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a professional CET-6 English expert."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }

    try:
        url = f"{base_url}/chat/completions"
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        else:
            print(f"[!] AI 接口返回异常 [{resp.status_code}]: {resp.text}")
    except Exception as e:
        print(f"[!] 调用 AI 接口出错: {e}")
    return None

def generate_html_view(markdown_content: str, words: List[str], output_path: str = "today_cet6_story.html"):
    """
    将内容生成带有发音功能和现代化卡片排版的 HTML 文件
    """
    import re
    # 简单的 Markdown 转 HTML 渲染
    body_html = markdown_content
    # 转标题
    body_html = re.sub(r"^### (.*)$", r"<h3>\1</h3>", body_html, flags=re.MULTILINE)
    body_html = re.sub(r"^## (.*)$", r"<h2>\1</h2>", body_html, flags=re.MULTILINE)
    body_html = re.sub(r"^# (.*)$", r"<h1>\1</h1>", body_html, flags=re.MULTILINE)
    # 转粗体
    body_html = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", body_html)
    # 转换行
    body_html = body_html.replace("\n\n", "</p><p>").replace("\n", "<br>")

    # 为生词添加点击朗读特性
    words_tags = "".join([f'<span class="word-tag" onclick="speak(\'{w}\')">{w} 🔊</span>' for w in words])

    html_template = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>六级真题语境·今日单词串记微短文</title>
    <style>
        :root {{
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text: #1e293b;
            --primary: #2563eb;
            --highlight: #fef08a;
            --border: #e2e8f0;
        }}
        @media (prefers-color-scheme: dark) {{
            :root {{
                --bg: #0f172a;
                --card-bg: #1e293b;
                --text: #f1f5f9;
                --primary: #60a5fa;
                --highlight: #854d0e;
                --border: #334155;
            }}
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text);
            line-height: 1.8;
            margin: 0;
            padding: 24px 16px;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: var(--card-bg);
            padding: 32px;
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.06);
            border: 1px solid var(--border);
        }}
        h1, h2, h3 {{
            color: var(--primary);
            border-bottom: 2px solid var(--border);
            padding-bottom: 8px;
        }}
        strong {{
            background: var(--highlight);
            color: #000;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 600;
            cursor: pointer;
        }}
        .word-bar {{
            margin-bottom: 24px;
            padding: 16px;
            background: rgba(37, 99, 235, 0.08);
            border-radius: 12px;
        }}
        .word-tag {{
            display: inline-block;
            background: var(--primary);
            color: #ffffff;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 13px;
            margin: 4px;
            cursor: pointer;
            transition: transform 0.1s;
        }}
        .word-tag:hover {{
            transform: scale(1.05);
        }}
        .audio-tip {{
            font-size: 12px;
            color: #64748b;
            margin-top: 8px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📖 六级真题语境·今日单词串记微小说</h1>
        <div class="word-bar">
            <div><strong>今日重点词汇（点击可听真人发音）：</strong></div>
            <div style="margin-top: 8px;">{words_tags}</div>
            <div class="audio-tip">💡 提示：点击上方任意单词标签，即可直接播放英音朗读。</div>
        </div>
        <div class="content">
            <p>{body_html}</p>
        </div>
    </div>
    <script>
        function speak(word) {{
            if ('speechSynthesis' in window) {{
                window.speechSynthesis.cancel();
                const utterance = new SpeechSynthesisUtterance(word);
                utterance.lang = 'en-US';
                utterance.rate = 0.9;
                window.speechSynthesis.speak(utterance);
            }} else {{
                alert('您的浏览器不支持语音朗读');
            }}
        }}
    </script>
</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_template)
    return output_path

def push_to_wechat(title: str, content: str, token: Optional[str] = None) -> bool:
    """
    通过 PushPlus 将内容推送到微信
    """
    token = token or os.getenv("PUSHPLUS_TOKEN")
    if not token:
        print("[!] 未配置 PUSHPLUS_TOKEN，跳过微信推送。")
        return False

    url = "http://www.pushplus.plus/send"
    payload = {
        "token": token,
        "title": title,
        "content": content,
        "template": "markdown"
    }
    try:
        resp = requests.post(url, json=payload, timeout=15)
        res_json = resp.json()
        if res_json.get("code") == 200:
            print("[OK] 已成功推送到微信 (PushPlus)！")
            return True
        else:
            print(f"[!] PushPlus 推送失败: {res_json.get('msg')}")
    except Exception as e:
        print(f"[!] 推送异常: {e}")
    return False

def main():
    parser = argparse.ArgumentParser(description="六级真题语境·今日单词串记微小说生成器")
    parser.add_argument("words", nargs="*", help="手动指定单词列表（不传则自动从墨墨 API 获取今日单词）")
    parser.add_argument("--file", "-f", help="从文件读取单词列表")
    parser.add_argument("--limit", "-l", type=int, default=12, help="单篇短文串记的最大单词数（默认 12 个）")
    parser.add_argument("--push", action="store_true", help="是否同时推送到微信 (需环境变量或 .env 中有 PUSHPLUS_TOKEN)")
    parser.add_argument("--demo", action="store_true", help="使用内置的六级真题高频核心词演示")

    args = parser.parse_args()

    # 1. 确定本次要串记的单词
    words_to_use = []

    if args.words:
        words_to_use = args.words
    elif args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            words_to_use = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    elif args.demo:
        words_to_use = SAMPLE_CET6_WORDS
    else:
        # 从墨墨 API 自动抓取
        print("正在从墨墨背单词 OpenAPI 获取今日背词清单...")
        client = MaiMemoClient()
        today_items = get_today_cet6_words(client, limit=args.limit)
        if today_items:
            print(f"[OK] 成功从墨墨获取到今天背过的 {len(today_items)} 个词汇！")
            for item in today_items:
                status = item.get("first_response", "学习")
                print(f"  - {item.get('voc_spelling')}: 状态={status}")
            words_to_use = [item.get("voc_spelling") for item in today_items if item.get("voc_spelling")]
        else:
            print("💡 提示：检测到今天尚未在墨墨 App 中同步背词记录。")
            print("   正在自动启用【六级真题高频核心词汇】进行效果演示体验！")
            print("   （也可以通过 `python cet6_story.py word1 word2 ...` 手动传入今日单词）\n")
            words_to_use = SAMPLE_CET6_WORDS

    if not words_to_use:
        print("[!] 未获取到有效单词，退出。")
        sys.exit(1)

    print(f"\n🎯 本次用于六级串记的重点单词 ({len(words_to_use)} 个):")
    print("   " + ", ".join(words_to_use))

    # 2. 构建 Prompt
    words_str = ", ".join(words_to_use)
    prompt = CET6_PROMPT_TEMPLATE.format(words_str=words_str)

    # 3. 尝试调用 AI 接口
    print("\n🤖 正在请求 AI 编写六级真题风格的串记微小说...")
    ai_story = call_ai_api(prompt)

    if not ai_story:
        # 如果未配置 AI API Key，提示用户配置，并生成一个精美模板
        print("\n" + "="*60)
        print("💡 温馨提示：当前尚未配置 AI_API_KEY（如 DeepSeek 或 Gemini）。")
        print("   你可以选择以下两种方式之一：")
        print("   方式 1：在 .env 文件中添加 DEEPSEEK_API_KEY=你的Key 即可全自动生成；")
        print("   方式 2：直接复制下方为你生成的专属 Prompt 发给任意 AI（或发在对话框中给我）：")
        print("="*60 + "\n")
        print("📋 【复制以下 Prompt】:")
        print(prompt)

        # 生成一个基础演示短文
        ai_story = f"""### Module 1: CET-6 In-Depth Reading Passage (科技与现代环境)

In recent decades, the global ecosystem has begun to **[1] deteriorate** at an **[2] unprecedented** rate, driven largely by intense industrial activity. Developing regions are particularly **[3] susceptible** to these environmental shifts, facing severe agricultural disruptions. Although some critics initially offered a **[4] plausible** defense regarding the trade-offs of rapid economic growth, policymakers can no longer afford to delay action. They must seriously **[5] contemplate** long-term sustainability models. 

Experts widely **[6] speculate** that without **[7] indispensable** global collaboration and sustained scientific **[8] perseverance**, the crisis will become virtually **[9] inevitable**. Even **[10] subtle** variations in ocean temperatures can trigger cascading failures across planetary food chains.

---

### Module 2: 中文参考译文

近几十年来，在密集工业活动的推动下，全球生态系统开始以前所未有的速度**恶化**。发展中地区对这些环境变化尤其**易受影响（脆弱）**，面临着严重的农业受损。尽管一些批评人士最初就经济快速增长的权衡取舍提出了看似**合情合理**的辩解，但决策者已无法承受拖延行动的后果。他们必须严肃**深思（考量）**长期的可持续发展模式。

专家们普遍**推测**，如果没有不可或缺的全球协作与持之以恒的科学**毅力**，这场危机将几乎变得**不可避免**。即使是海洋温度的**细微**变化，也可能在整个地球食物链中引发连锁性的崩溃反应。

---

### Module 3: 六级常考考点清单

1. **deteriorate** /dɪˈtɪəriəreɪt/ *vi.* 恶化，退化
   - 【六级真题搭配】：*deteriorate rapidly/sharply*（急剧恶化）；*environmental deterioration*（环境恶化）
   - 【同义替换】：*degrade, worsen, decline*

2. **susceptible** /səˈseptəbl/ *adj.* 易受影响的，脆弱的
   - 【六级真题搭配】：*be susceptible to (disease/influence)*（对……易感的/易受影响的）
   - 【同义替换】：*vulnerable, prone*

3. **unprecedented** /ʌnˈpresɪdentɪd/ *adj.* 前所未有的，空前的
   - 【六级真题搭配】：*at an unprecedented pace/rate*（以前所未有的速度）；*unprecedented challenge*
   - 【同义替换】：*unequaled, groundbreaking*

4. **plausible** /ˈplɔːzəbl/ *adj.* 似乎合理的，说得通的
   - 【六级真题搭配】：*a plausible explanation/argument*（合情合理的解释/论点）
   - 【反义词】：*implausible*（难以置信的）

5. **contemplate** /ˈkɒntəmpleɪt/ *vt.* 盘算，深思
   - 【六级真题搭配】：*contemplate doing sth.*（盘算/考虑做某事）
   - 【同义替换】：*ponder, meditate on, reflect on*

---

### Module 4: 六级选词填空实战自测

**Questions:**
1. The patient's condition began to _______ rapidly after the operation, requiring immediate intensive care.
2. Older adults and infants are especially _______ to extreme heatwaves during summer.

**【参考答案与解析】**
1. **deteriorate** (解析：情态动词 began to 后接动词原形，根据 rapidly 判断表示“身体状况急剧恶化”)。
2. **susceptible** (解析：be susceptible to 为六级高频固定搭配，意为“容易受……的影响/对……脆弱”)。
"""

    # 4. 生成 HTML 网页并尝试打开
    html_file = generate_html_view(ai_story, words_to_use)
    print(f"\n[OK] 已生成可视化复习网页: {html_file}")
    try:
        webbrowser.open(os.path.abspath(html_file))
        print("🌐 已在默认浏览器自动打开短文自测页面！")
    except Exception:
        pass

    # 5. 如果开启了推送或设置了 --push
    if args.push or os.getenv("PUSHPLUS_TOKEN"):
        print("📲 正在推送到微信 (PushPlus)...")
        push_to_wechat("【六级今日串记】语境短文与考点自测", ai_story)

if __name__ == "__main__":
    main()
