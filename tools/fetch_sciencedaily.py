"""ScienceDaily 科学语料爬虫（多频道全量版）。

覆盖 15 个科学频道，抓取深度长文，清洗后追加到 local_corpus.json。
新文章标记 "category": "science"，已有无标记文章补标 "category": "history"。

运行方式: python fetch_sciencedaily.py
"""

import json
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# ── 配置 ───────────────────────────────────────────────────────
CORPUS_PATH = Path(__file__).resolve().parent / "local_corpus.json"
BASE_URL = "https://www.sciencedaily.com"

# 目标频道（15 个，多点开花）
CHANNEL_URLS = [
    # ── 核心专业相关（能动/物理）────────────────────────────
    f"{BASE_URL}/news/matter_energy/thermodynamics/",
    f"{BASE_URL}/news/matter_energy/energy_technology/",
    f"{BASE_URL}/news/matter_energy/physics/",
    f"{BASE_URL}/news/matter_energy/engineering/",
    f"{BASE_URL}/news/matter_energy/fossil_fuels/",
    f"{BASE_URL}/news/matter_energy/nuclear_energy/",
    f"{BASE_URL}/news/matter_energy/solar_energy/",
    f"{BASE_URL}/news/matter_energy/wind_energy/",
    # ── 前沿与交叉学科（扩充词汇量）──────────────────────────
    f"{BASE_URL}/news/matter_energy/nanotechnology/",
    f"{BASE_URL}/news/matter_energy/materials_science/",
    f"{BASE_URL}/news/matter_energy/chemistry/",
    f"{BASE_URL}/news/matter_energy/aviation/",
    f"{BASE_URL}/news/computers_math/artificial_intelligence/",
    f"{BASE_URL}/news/earth_climate/global_warming/",
    f"{BASE_URL}/news/earth_climate/renewable_energy/",
]

# 清洗后正文最低字符数（科普文密度高但篇幅偏短，适当放宽）
MIN_CONTENT_LENGTH = 2000

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

REQUEST_DELAY = 1.2


# ── 第一步：从目录页提取文章链接 ─────────────────────────────
def get_article_links() -> list[str]:
    """遍历所有目标频道页，从 div.latest-head a 中提取文章链接。"""
    all_links: list[str] = []
    session = requests.Session()
    session.headers.update(HEADERS)

    for channel_url in CHANNEL_URLS:
        print(f"[Channel] {channel_url}")
        try:
            resp = session.get(channel_url, timeout=15)
            if resp.status_code != 200:
                print(f"  -> HTTP {resp.status_code}, skipping")
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            page_links = []
            # 精准定位: div.latest-head 内的 a 标签
            for div in soup.find_all("div", class_="latest-head"):
                a_tag = div.find("a", href=True)
                if not a_tag:
                    continue
                href = a_tag["href"]
                # ScienceDaily 文章链接格式: /releases/2024/05/240501xxxx.htm
                if "/releases/" not in href:
                    continue
                full_url = f"{BASE_URL}{href}" if href.startswith("/") else href
                if full_url not in all_links:
                    all_links.append(full_url)
                    page_links.append(full_url)

            print(f"  -> Found {len(page_links)} article links")

        except Exception as exc:
            print(f"  -> Error: {exc}")

        time.sleep(REQUEST_DELAY)

    print(f"\n[Total] {len(all_links)} unique article links collected")
    return all_links


# ── 第二步：精准提取 + 深度清洗单篇文章 ──────────────────────
def fetch_clean_article(url: str, session: requests.Session) -> dict | None:
    """下载并清洗一篇 ScienceDaily 文章。

    正文容器: div#text
    标题: h1.headline
    """
    try:
        resp = session.get(url, timeout=15)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        # ── 提取标题: h1.headline ─────────────────────────────
        h1 = soup.find("h1", class_="headline")
        if not h1:
            h1 = soup.find("h1")
        if not h1:
            return None
        title = h1.get_text(strip=True)
        if not title:
            return None

        # ── 定位正文容器: div#text ────────────────────────────
        text_div = soup.find("div", id="text")
        if not text_div:
            return None

        # ── 深度清洗 ──────────────────────────────────────────
        # 相关阅读列表
        for tag in text_div.find_all("ul", class_="list-unstyled"):
            tag.decompose()
        # 推荐块
        for tag in text_div.find_all("div", class_="related-content"):
            tag.decompose()
        # 脚本/样式/iframe
        for tag in text_div.find_all(["script", "style", "iframe", "noscript"]):
            tag.decompose()
        # 图注
        for tag in text_div.find_all("figcaption"):
            tag.decompose()
        for tag in text_div.find_all("figure"):
            tag.decompose()

        # ── 提取段落并过滤 "Story Source:" 结尾 ───────────────
        paragraphs = text_div.find_all("p")
        clean_paragraphs: list[str] = []
        for p in paragraphs:
            text = p.get_text(strip=True)
            if not text:
                continue
            # 剔除 "Story Source:" 开头的结尾段落
            if text.startswith("Story Source:"):
                break  # 后面的段落都是来源/引用信息，一刀切
            if len(text) > 30:
                clean_paragraphs.append(text)

        content = "\n".join(clean_paragraphs)

        # ── 字数门槛 ─────────────────────────────────────────
        if len(content) < MIN_CONTENT_LENGTH:
            return None

        return {
            "title": title,
            "content": content,
            "category": "science",
        }

    except Exception:
        return None


# ── 语料库 IO ────────────────────────────────────────────────
def load_existing_corpus() -> list[dict]:
    if not CORPUS_PATH.exists():
        return []
    try:
        data = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def tag_existing_articles(corpus: list[dict]) -> int:
    """为已有的没有 category 字段的文章补标 'history'。"""
    count = 0
    for entry in corpus:
        if "category" not in entry:
            entry["category"] = "history"
            count += 1
    return count


def save_corpus(corpus: list[dict]) -> None:
    CORPUS_PATH.write_text(
        json.dumps(corpus, ensure_ascii=False, indent=4),
        encoding="utf-8",
    )


# ── 主流程 ───────────────────────────────────────────────────
def main() -> None:
    print("=" * 60)
    print("  ScienceDaily Corpus Fetcher (15 channels)")
    print(f"  Targeting {len(CHANNEL_URLS)} science channels")
    print("=" * 60)

    # 1) 获取文章链接
    urls = get_article_links()
    if not urls:
        print("[ABORT] No article links found.")
        return

    # 2) 逐篇抓取
    print(f"\n[Fetching] Downloading {len(urls)} articles...")
    session = requests.Session()
    session.headers.update(HEADERS)

    new_articles: list[dict] = []
    filtered = 0

    for url in tqdm(urls, desc="Fetching & cleaning"):
        article = fetch_clean_article(url, session)
        if article:
            new_articles.append(article)
        else:
            filtered += 1
        time.sleep(REQUEST_DELAY)

    print(f"\n[Result] {len(new_articles)} passed quality filter / {filtered} filtered out")

    if not new_articles:
        print("[WARN] No articles passed the 2000-char filter.")
        return

    # 3) 集成到现有语料库
    existing = load_existing_corpus()
    existing_count = len(existing)

    tagged = tag_existing_articles(existing)
    if tagged:
        print(f"[Tag] Marked {tagged} existing articles as 'history'")

    # 去重
    existing_titles = {entry.get("title", "") for entry in existing}
    added = 0
    for article in new_articles:
        if article["title"] not in existing_titles:
            existing.append(article)
            existing_titles.add(article["title"])
            added += 1

    save_corpus(existing)

    print(f"\n{'=' * 60}")
    print(f"  Corpus: {existing_count} existing + {added} new science articles")
    print(f"  Total: {len(existing)} articles in local_corpus.json")
    print(f"  Duplicates skipped: {len(new_articles) - added}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
