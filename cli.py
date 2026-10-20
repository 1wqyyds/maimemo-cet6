"""
墨墨背单词 命令行工具 CLI
"""

import sys
import argparse

# 确保在 Windows 控制台或非 UTF-8 环境下输出不会因为编码报错
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from maimemo_client import MaiMemoClient

def main():
    parser = argparse.ArgumentParser(description="墨墨背单词 OpenAPI 快捷工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # 1. 学习进度
    subparsers.add_parser("progress", help="查看今日学习进度与时长")

    # 2. 查词
    word_parser = subparsers.add_parser("search", help="查询单个或多个单词")
    word_parser.add_argument("words", nargs="+", help="英文单词列表，空格分隔")

    # 3. 批量添加单词进背词库
    add_parser = subparsers.add_parser("add-words", help="批量添加单词到学习计划")
    add_parser.add_argument("words", nargs="*", help="要添加的单词拼写")
    add_parser.add_argument("--file", "-f", help="从指定文本文件读取单词列表（每行一个）")
    add_parser.add_argument("--advance", "-a", action="store_true", help="是否同时提前复习")

    # 4. 云词本列表
    subparsers.add_parser("notepads", help="查看云词本列表")

    # 5. 创建云词本
    np_parser = subparsers.add_parser("create-notepad", help="创建云词本")
    np_parser.add_argument("--title", "-t", required=True, help="词本标题")
    np_parser.add_argument("--content", "-c", help="词本内容（文本或带#章节）")
    np_parser.add_argument("--file", "-f", help="从文本文件读取词本内容")
    np_parser.add_argument("--brief", "-b", default="", help="词本简介")
    np_parser.add_argument("--tags", nargs="*", default=[], help="标签，如 考研 雅思")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    client = MaiMemoClient()

    if args.command == "progress":
        print("正在获取今日学习进度...")
        p = client.get_study_progress()
        finished = p.get("finished", 0)
        total = p.get("total", 0)
        duration_sec = p.get("study_time", 0)
        minutes = duration_sec // 60
        seconds = duration_sec % 60
        print("\n【今日墨墨背单词进度】")
        print(f"  - 已完成单词数: {finished}")
        print(f"  - 今日规划总数: {total}")
        print(f"  - 今日学习时长: {minutes} 分 {seconds} 秒")
        if total == 0 and finished == 0:
            print("  提示: 若总数为 0，请先在手机 App 中打开墨墨背单词进行初始化，并确认开启了【自动同步】。")

    elif args.command == "search":
        print(f"正在查询单词: {', '.join(args.words)} ...")
        if len(args.words) == 1:
            voc = client.get_vocabulary(args.words[0])
            if voc:
                print(f"[OK] 找到单词: {voc.get('spelling')}")
                print(f"     ID: {voc.get('id')}")
            else:
                print(f"[X] 未找到单词: {args.words[0]}")
        else:
            vocs = client.query_vocabularies(spellings=args.words)
            print(f"[OK] 成功找到 {len(vocs)} / {len(args.words)} 个单词：")
            for v in vocs:
                print(f"  - {v.get('spelling')}: ID={v.get('id')}")

    elif args.command == "add-words":
        words_to_add = list(args.words)
        if args.file:
            with open(args.file, "r", encoding="utf-8") as f:
                for line in f:
                    w = line.strip()
                    if w and not w.startswith("#"):
                        words_to_add.append(w)
        if not words_to_add:
            print("[!] 请提供要添加的单词或指定 --file 文件！")
            sys.exit(1)

        print(f"正在向墨墨背单词添加 {len(words_to_add)} 个生词...")
        result = client.add_words_by_spellings(words_to_add, advance=args.advance)
        print(f"[OK] 处理完成：请求 {result['requested_count']} 个，词库匹配到 {result['found_count']} 个，成功添加 {result['added_count']} 个！")
        if result['not_found']:
            print(f"[!] 未在墨墨官方词库中匹配到的词: {result['not_found']}")

    elif args.command == "notepads":
        print("正在获取云词本列表...")
        notepads = client.list_notepads()
        if not notepads:
            print("当前没有云词本。")
        else:
            print(f"共找到 {len(notepads)} 个云词本：")
            for np in notepads:
                print(f"  - [{np.get('id')}] {np.get('title')} ({np.get('status')})")

    elif args.command == "create-notepad":
        content = args.content or ""
        if args.file:
            with open(args.file, "r", encoding="utf-8") as f:
                content = f.read()
        if not content:
            print("[!] 请通过 --content 或 --file 提供云词本内容！")
            sys.exit(1)

        print(f"正在创建云词本《{args.title}》...")
        np = client.create_notepad(title=args.title, content=content, brief=args.brief, tags=args.tags)
        print(f"[OK] 云词本创建成功！ID: {np.get('id')}")
        print(f"     标题: {np.get('title')}")

if __name__ == "__main__":
    main()
