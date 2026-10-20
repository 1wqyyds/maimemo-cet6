"""
墨墨背单词 OpenAPI Python 客户端
"""

import os
import requests
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# 加载本地 .env 文件（保护隐私，不公开）
load_dotenv()

DEFAULT_TOKEN = ""
DEFAULT_BASE_URL = "https://open.maimemo.com/open"

class MaiMemoClient:
    def __init__(self, token: Optional[str] = None, base_url: Optional[str] = None):
        self.token = token or os.getenv("MAIMEMO_TOKEN") or DEFAULT_TOKEN
        if not self.token:
            raise ValueError("未检测到 MAIMEMO_TOKEN，请在 .env 文件中配置！")
        self.base_url = (base_url or os.getenv("MAIMEMO_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        })

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        resp = self.session.request(method, url, **kwargs)
        if resp.status_code >= 400:
            raise RuntimeError(f"请求失败 [{resp.status_code}]: {resp.text}")
        data = resp.json()
        if not data.get("success", False) and "data" not in data:
            errors = data.get("errors", [])
            raise RuntimeError(f"API 业务报错: {errors}")
        return data.get("data", data)

    # ==================== 1. 单词查询 ====================

    def get_vocabulary(self, spelling: str) -> Optional[Dict[str, Any]]:
        """
        根据拼写查询单个单词
        返回格式: {'voc': {'id': '...', 'spelling': '...'}}
        """
        res = self._request("GET", "/api/v1/memo/vocabulary", params={"spelling": spelling})
        return res.get("voc")

    def query_vocabularies(self, spellings: Optional[List[str]] = None, ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        批量查询单词（支持按拼写或按 ID 查询，最多 1000 个）
        """
        payload: Dict[str, Any] = {}
        if spellings:
            payload["spellings"] = spellings
        elif ids:
            payload["ids"] = ids
        else:
            raise ValueError("必须提供 spellings 或 ids 之一")

        res = self._request("POST", "/api/v1/memo/vocabulary/query", json=payload)
        return res.get("voc") or res.get("vocs") or []

    # ==================== 2. 学习进度与背词 (公测接口) ====================

    def get_study_progress(self) -> Dict[str, Any]:
        """
        获取今日学习进度与时长
        返回示例: {'finished': 20, 'total': 100, 'study_time': 1200}
        注：需在 App 中开启自动同步，且当日初始化后才能获得准确数据
        """
        res = self._request("POST", "/api/v1/memo/study/get_study_progress", json={})
        return res.get("progress", {})

    def get_today_items(self, limit: int = 50, is_finished: Optional[bool] = None, is_new: Optional[bool] = None) -> List[Dict[str, Any]]:
        """
        获取今日学习单词列表
        """
        payload: Dict[str, Any] = {"limit": limit}
        if is_finished is not None:
            payload["is_finished"] = is_finished
        if is_new is not None:
            payload["is_new"] = is_new
        res = self._request("POST", "/api/v1/memo/study/get_today_items", json=payload)
        return res.get("today_items", [])

    def add_words_by_ids(self, word_ids: List[str], advance: bool = False) -> int:
        """
        通过单词 ID 列表批量将单词加入学习计划
        :param word_ids: 单词 ID 列表（通过查询单词接口获取）
        :param advance: 是否一并提前复习
        :return: 成功添加的单词数量
        """
        words = [{"id": wid} for wid in word_ids]
        payload = {
            "words": words,
            "advance": advance
        }
        res = self._request("POST", "/api/v1/memo/study/add_words", json=payload)
        return res.get("added_count", 0)

    def add_words_by_spellings(self, spellings: List[str], advance: bool = False) -> Dict[str, Any]:
        """
        便捷方法：直接传入英文拼写列表，自动查 ID 并批量加入学习计划
        """
        valid_words = self.query_vocabularies(spellings=spellings)
        found_ids = [w["id"] for w in valid_words if "id" in w]
        found_spellings = [w["spelling"] for w in valid_words if "spelling" in w]
        not_found = list(set(spellings) - set(found_spellings))

        added_count = 0
        if found_ids:
            added_count = self.add_words_by_ids(found_ids, advance=advance)

        return {
            "requested_count": len(spellings),
            "found_count": len(found_ids),
            "added_count": added_count,
            "not_found": not_found
        }

    # ==================== 3. 云词本管理 ====================

    def list_notepads(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """
        查询我的云词本列表
        """
        res = self._request("GET", "/api/v1/memo/notepads", params={"limit": limit, "offset": offset})
        return res.get("notepads", [])

    def create_notepad(self, title: str, content: str, brief: str = "", tags: Optional[List[str]] = None, status: str = "PUBLISHED") -> Dict[str, Any]:
        """
        创建云词本
        :param title: 词本标题
        :param content: 词本内容
               - 章节模式：以 # 开头，如 "# 第一章\napple\nbanana"
               - 文本模式：直接贴文章或单词列表，开头加 // 则自动还原词根
        :param brief: 简介
        :param tags: 标签列表，如 ["日常", "雅思"]
        :param status: 状态，默认 PUBLISHED
        """
        payload = {
            "notepad": {
                "title": title,
                "content": content,
                "brief": brief or title,
                "tags": tags or [],
                "status": status
            }
        }
        res = self._request("POST", "/api/v1/memo/notepads", json=payload)
        return res.get("notepad", {})
