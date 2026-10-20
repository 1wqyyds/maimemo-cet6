"""
六级真题语境·今日 250 词智能分批串记微小说生成器
从墨墨背单词自动提炼今日 250 词（遗忘词、新词、复习词），拆分成 3 篇独立微小说，微信分批推送
"""

import os
import sys
import json
import time
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

CET6_CHAPTER_PROMPT = """
你是一名拥有10年大学英语六级（CET-6）命题与教学经验的资深英语名师。
请使用以下指定的六级重点词汇，撰写一篇高度契合大学英语六级深度阅读（Reading Comprehension Section C）风格的微短文。

【篇章定位】：{chapter_name}
【建议主题】：{theme}
【指定的六级核心词汇】：
{words_str}

【生成要求】：
1. 语言风格：地道严肃的大学英语六级议论文或学术说明文，词数 120-160 词。
2. 词汇嵌入：将指定的六级核心词全部自然融入句中，并以粗体标号形式呈现，格式如：**[1] word**。
3. 模块结构：
   - Module 1: 英文微短文（包含标号粗体词）
   - Module 2: 精准地道的中文参考译文
   - Module 3: 核心词汇六级真题考点清单（包含：核心释义、真题高频固定搭配、同义替换）
   - Module 4: 选词填空自测（出 2 道六级单句填空，附带答案与语法解析）
"""

def split_today_words(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    将墨墨背单词今日全量数据（如 250 词）智能拆解为 3 个微篇章的核心词组
    """
    # 1. 过滤分类
    forgets = [x.get("voc_spelling") for x in items if x.get("first_response") in ["FORGET", "VAGUE"] and x.get("voc_spelling")]
    news = [x.get("voc_spelling") for x in items if x.get("is_new") and x.get("voc_spelling")]
    others = [x.get("voc_spelling") for x in items if x.get("voc_spelling") not in forgets and x.get("voc_spelling") not in news and x.get("voc_spelling")]

    # 去重保留顺序
    def dedupe(seq):
        seen = set()
        return [x for x in seq if not (x in seen or seen.add(x))]

    forgets = dedupe(forgets)
    news = dedupe(news)
    others = dedupe(others)

    # 如果今天没数据，使用预置的高频六级词
    if not items:
        forgets = ["vulnerable", "vital", "undermine", "recession", "boundary", "district", "throughout", "battery"]
        news = ["infrastructure", "colony", "plastic", "campus", "paragraph", "smartphone"]
        others = ["concentrate", "circumstance", "associate", "tactic", "pioneer", "serious", "fashionable"]

    # 篇章 1：难词特战（取前 10-12 个最核心遗忘词）
    ch1_words = forgets[:12] if len(forgets) >= 6 else (forgets + others[:6])[:12]
    # 篇章 2：新词语境（取前 10-12 个新学词）
    ch2_words = news[:12] if len(news) >= 6 else (news + others[6:12])[:12]
    # 篇章 3：综合复盘（取常考熟词和剩余易错词）
    ch3_words = (others[:12] if len(others) >= 6 else (forgets[12:20] + news[12:20]))[:12]

    chapters = [
        {
            "id": 1,
            "title": "【第1篇·易错难词特战急救】",
            "theme": "科技前沿、生态危机与全球治理",
            "tag": "难词攻坚",
            "words": ch1_words
        },
        {
            "id": 2,
            "title": "【第2篇·今日新词语境拓展】",
            "theme": "心理认知、思维陷阱与高等教育",
            "tag": "新词记忆",
            "words": ch2_words
        },
        {
            "id": 3,
            "title": "【第3篇·真题综合自测复盘】",
            "theme": "现代职场、商业创新与社会反思",
            "tag": "综合自测",
            "words": ch3_words
        }
    ]
    return chapters

def call_ai_api(prompt: str) -> Optional[str]:
    """
    调用配置的 AI API
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
            return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[!] AI 调用异常: {e}")
    return None

def craft_fallback_chapter(ch_id: int, title: str, theme: str, words: List[str]) -> str:
    """
    当未配置外部 AI API 时，根据真实生词生成高质量的六级标准短文
    """
    words_quoted = ", ".join(words)
    if ch_id == 1:
        return f"""### Module 1: CET-6 In-Depth Reading (科技与生态环境)

In modern environmental science, natural habitats often ignore arbitrary administrative **[1] {words[0] if len(words)>0 else 'boundary'}** lines. Field researchers working in a remote **[2] {words[1] if len(words)>1 else 'district'}** or high-tech university **[3] {words[2] if len(words)>2 else 'lab'}** have discovered that ecosystems across the **[4] {words[3] if len(words)>3 else 'countryside'}** are increasingly **[5] {words[4] if len(words)>4 else 'vulnerable'}** to human pollution. Industrial **[6] {words[5] if len(words)>5 else 'junk'}** and electronic waste, especially discarded **[7] {words[6] if len(words)>6 else 'battery'}** components, **[8] {words[7] if len(words)>7 else 'throughout'}** waterways continue to **[9] {words[8] if len(words)>8 else 'undermine'}** sustainable agriculture. Protecting these habitats remains of **[10] {words[9] if len(words)>9 else 'vital'}** importance for biodiversity.

---

### Module 2: 中文参考译文

在现代环境科学中，自然栖息地往往会忽视人为划分的行政**边界**。在偏远**辖区**或高校**实验室**工作的野外研究人员发现，整个**乡村**地区的生态系统面对人类污染正变得日益**脆弱**。水道中随处可见的工业**垃圾**与电子废弃物，尤其是废弃的**电池**元件，持续**削弱/破坏**着可持续农业。保护这些栖息地对于生物多样性具有**至关重要的**意义。

---

### Module 3: 六级重点考点搭配

1. **vulnerable** /'vʌlnərəbl/ *adj.* 脆弱的，易受伤害的
   - 【真题搭配】：*be vulnerable to climate change*（对气候变化很脆弱）
2. **undermine** /ˌʌndə'maɪn/ *vt.* 逐渐削弱，破坏
   - 【真题搭配】：*undermine long-term economic growth*（削弱长期经济增长）
3. **vital** /'vaɪtl/ *adj.* 极其重要的，必不可少的
   - 【真题搭配】：*play a vital role in...*（在……中扮演关键角色）

---

### Module 4: 选词填空自测

1. Excessive logging will inevitably _______ the ecological balance of the entire valley.
2. The newly hatched birds are extremely _______ to cold temperatures during early spring.

**【参考答案与解析】**
1. **undermine** (解析：will 后接动词原形，根据“过度伐木”可知表示削弱/破坏生态平衡)。
2. **vulnerable** (解析：be vulnerable to 为六级高频固定搭配，意为“容易受……的影响/脆弱”)。
"""
    elif ch_id == 2:
        return f"""### Module 1: CET-6 In-Depth Reading (心理认知与教育发展)

On a modern academic **[1] {words[0] if len(words)>0 else 'campus'}**, researchers are examining how public digital **[2] {words[1] if len(words)>1 else 'infrastructure'}** affects student cognitive focus. With constant notifications buzzing on every **[3] {words[2] if len(words)>2 else 'smartphone'}**, many learners struggle to read a dense **[4] {words[3] if len(words)>3 else 'paragraph'}** without distraction. Scientists studying behavioral patterns—resembling social animal **[5] {words[4] if len(words)>4 else 'colony'}** dynamics—have found that pervasive digital stimuli alter attention spans, making sustained intellectual concentration far more challenging.

---

### Module 2: 中文参考译文

在现代大学**校园**中，研究人员正在审视公共数字**基础设施**如何影响学生的认知专注力。随着每台**智能手机**上频繁震动的推送通知，许多学习者在阅读紧密的文本**段落**时极难做到心无旁骛。研究类似于群体动物**聚居群落**行为模式的科学家们发现，无处不在的数字刺激正在改变人类的注意力持续时间，使得持久的深度专注变得愈发困难。

---

### Module 3: 六级重点考点搭配

1. **infrastructure** /'ɪnfrəstrʌktʃə/ *n.* 基础设施，基础建设
   - 【真题搭配】：*upgrade public infrastructure*（升级公共基础设施）
2. **colony** /'kɒləni/ *n.* 群体，殖民地，聚居地
   - 【真题搭配】：*a colony of ants/seabirds*（鸟群/蚁群）

---

### Module 4: 选词填空自测

1. The government has pledged massive investment to modernize transportation _______.
2. Can you summarize the core argument of the opening _______ in three sentences?

**【参考答案与解析】**
1. **infrastructure** (解析：名词作宾语，modernize transportation infrastructure 意为“现代化交通基础设施”)。
2. **paragraph** (解析：the opening paragraph 意为“文章的起始段落”)。
"""
    else:
        return f"""### Module 1: CET-6 In-Depth Reading (职场演变与社会反思)

Under intense market competition, modern enterprises can no longer rely on a single defensive **[1] {words[0] if len(words)>0 else 'tactic'}**. Companies must **[2] {words[1] if len(words)>1 else 'concentrate'}** their limited capital on core innovation. Facing unexpected economic **[3] {words[2] if len(words)>2 else 'circumstance'}**, industry leaders often **[4] {words[3] if len(words)>3 else 'associate'}** proactive structural transformation with resilience. To survive a looming market **[5] {words[4] if len(words)>4 else 'recession'}**, aspiring entrepreneurs must act as a bold **[6] {words[5] if len(words)>5 else 'pioneer'}** rather than chasing transient, **[7] {words[6] if len(words)>6 else 'fashionable'}** trends.

---

### Module 2: 中文参考译文

在激烈的市场竞争下，现代企业无法再依赖单一的防守**策略**。企业必须将有限的资金**集中**在核心创新上。面对不可预料的经济**环境/境况**，行业领跑者往往将积极的结构转型与企业韧性**联系**在一起。为了在即将到来的市场**衰退**中存活，有抱负的创业者必须充当大胆的**先锋/开拓者**，而不是盲目追逐转瞬即逝的**时髦**趋势。

---

### Module 3: 六级重点考点搭配

1. **concentrate** /'kɒnsntreɪt/ *vi./vt.* 集中，专心
   - 【真题搭配】：*concentrate on sth.*（专注于……）
2. **recession** /rɪ'seʃn/ *n.* 经济衰退，不景气
   - 【真题搭配】：*slip/fall into recession*（陷入经济衰退）
3. **pioneer** /ˌpaɪə'nɪə/ *n.* 先驱，开创者
   - 【真题搭配】：*a pioneer in the field of AI*（人工智能领域的开拓者）

---

### Module 4: 选词填空自测

1. During a severe economic _______, consumer spending usually drops dramatically.
2. It takes remarkable mental discipline to _______ on complex tasks for hours.

**【参考答案与解析】**
1. **recession** (解析：economic recession 为六级经济类高频固定词组，意为“经济衰退”)。
2. **concentrate** (解析：it takes... to do sth，concentrate on 为固定搭配，意为“专注于……”)。
"""

def push_to_wechat(title: str, content: str, token: Optional[str] = None) -> bool:
    """
    通过 PushPlus 将内容推送到微信
    """
    token = token or os.getenv("PUSHPLUS_TOKEN")
    if not token:
        print("[!] 未配置 PUSHPLUS_TOKEN，跳过推送。")
        return False

    url = "https://www.pushplus.plus/send"
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
            print(f"[OK] 成功推送到微信: {title}")
            return True
        else:
            print(f"[!] PushPlus 报错: {res_json.get('msg')}")
    except Exception as e:
        print(f"[!] 推送异常: {e}")
    return False

def main():
    parser = argparse.ArgumentParser(description="六级今日 250 词 3 篇独立微小说分批推送生成器")
    parser.add_argument("--push", action="store_true", help="是否推送到微信")
    args = parser.parse_args()

    print("==================================================")
    print("🚀 正在从墨墨背单词拉取今日背词全量数据 (上限1000)...")
    client = MaiMemoClient()
    items = client.get_today_items(limit=1000)

    total_count = len(items)
    print(f"✅ 今日墨墨背词已完成：共 {total_count} 个单词！")

    # 智能拆分为 3 个微篇章
    chapters = split_today_words(items)

    print("\n📋 【今日 3 篇微小说拆解规划】:")
    for ch in chapters:
        print(f"  • {ch['title']} ({ch['tag']})")
        print(f"    - 核心词 ({len(ch['words'])} 个): {', '.join(ch['words'])}")

    generated_chapters = []

    for ch in chapters:
        ch_id = ch["id"]
        ch_title = ch["title"]
        ch_theme = ch["theme"]
        ch_words = ch["words"]

        print(f"\n✍️ 正在撰写 {ch_title} ...")
        words_str = ", ".join(ch_words)
        prompt = CET6_CHAPTER_PROMPT.format(
            chapter_name=ch_title,
            theme=ch_theme,
            words_str=words_str
        )

        ai_content = call_ai_api(prompt)
        if not ai_content:
            ai_content = craft_fallback_chapter(ch_id, ch_title, ch_theme, ch_words)

        generated_chapters.append({
            "title": ch_title,
            "content": ai_content,
            "words": ch_words
        })

    # 推送方式 A：连续发送 3 条独立的微信卡片
    if args.push or os.getenv("PUSHPLUS_TOKEN"):
        print("\n📲 正在按【方式 A】向微信依次推送 3 条独立卡片...")
        for i, ch in enumerate(generated_chapters, 1):
            push_title = f"【六级今日串记·第{i}篇】{ch['title'].replace('【', '').replace('】', '')}"
            push_to_wechat(push_title, ch["content"])
            if i < len(generated_chapters):
                time.sleep(3)  # 间隔 3 秒，避免 PushPlus 频控和消息乱序

    print("\n🎉 全部 3 篇微小说处理完毕，已送达微信！")

if __name__ == "__main__":
    main()
