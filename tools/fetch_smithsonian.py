"""Smithsonian Magazine 科学语料爬虫（Selenium 版）。

使用真实 Chrome 浏览器绕过 Cloudflare Turnstile 防护。
抓取 Science & Nature 分类下的深度长文，清洗后追加到 local_corpus.json。
所有新文章标记 "category": "science"，已有文章补标 "category": "history"。

运行方式: python fetch_smithsonian.py
  - 第一次加载时如遇 Cloudflare 验证页面，请在弹出的浏览器中手动点击验证。
  - 验证通过后脚本会自动继续抓取。
"""

import json
import time
from pathlib import Path

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# ── 配置 ───────────────────────────────────────────────────────
CORPUS_PATH = Path(__file__).resolve().parent / "local_corpus.json"
BASE_URL = "https://www.smithsonianmag.com"
CATEGORY_URL = f"{BASE_URL}/category/science-nature/"

# 分页范围
MAX_PAGES = 5

# 清洗后正文最低字符数
MIN_CONTENT_LENGTH = 800

# 页面加载等待（秒）
PAGE_LOAD_WAIT = 4


# ── 创建浏览器 ─────────────────────────────────────────────────
def create_driver() -> webdriver.Chrome:
    """创建可见的 Chrome 浏览器实例（不使用 headless，方便手动过验证）。"""
    opts = Options()
    # 不使用 headless，让用户看到并手动通过 Cloudflare 验证
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1280,900")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)

    # 隐藏 webdriver 标记
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )
    return driver


def wait_for_cloudflare(driver: webdriver.Chrome, timeout: int = 60) -> None:
    """等待 Cloudflare 验证通过。如果遇到验证页面，暂停让用户手动点击。"""
    print("[CF] Checking for Cloudflare challenge...")
    start = time.time()
    while time.time() - start < timeout:
        page_source = driver.page_source.lower()
        title = driver.title.lower()
        # Cloudflare 验证页面的特征
        if any(kw in title for kw in ["just a moment", "attention required", "cloudflare"]):
            print("[CF] Cloudflare challenge detected! Please solve it in the browser window...")
            time.sleep(3)
            continue
        if "challenge-platform" in page_source and "<article" not in page_source:
            time.sleep(3)
            continue
        # 验证通过
        print("[CF] Cloudflare check passed!")
        return
    print("[CF] WARNING: Cloudflare timeout, proceeding anyway...")


# ── 第一步：从分页列表中提取文章链接 ──────────────────────────
def get_article_links(driver: webdriver.Chrome) -> list[str]:
    """遍历分类页的多页，提取所有文章 URL。"""
    all_links: list[str] = []

    for page_num in range(1, MAX_PAGES + 1):
        url = f"{CATEGORY_URL}?page={page_num}"
        print(f"\n[Page {page_num}/{MAX_PAGES}] {url}")

        driver.get(url)
        wait_for_cloudflare(driver)
        time.sleep(PAGE_LOAD_WAIT)

        soup = BeautifulSoup(driver.page_source, "html.parser")

        page_links = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if not href.startswith("/"):
                continue
            # 排除非文章链接
            if any(skip in href for skip in [
                "/category/", "/image/", "/video/", "/quiz/",
                "/photos/", "/tag/", "/author/", "/subscribe",
                "/about/", "/contact/", "/privacy/", "/terms/",
                "/shop/", "/newsletters/", "/search/",
            ]):
                continue
            # 文章 URL 至少有 section/slug 两段路径
            segments = [s for s in href.strip("/").split("/") if s]
            if len(segments) < 2:
                continue

            full_url = f"{BASE_URL}{href}" if not href.startswith("http") else href
            if full_url not in all_links:
                all_links.append(full_url)
                page_links.append(full_url)

        print(f"  -> Found {len(page_links)} new article links (total: {len(all_links)})")

    print(f"\n[Total] {len(all_links)} unique article links collected")
    return all_links


# ── 第二步：精准提取 + 深度清洗单篇文章 ──────────────────────
def fetch_clean_article(driver: webdriver.Chrome, url: str) -> dict | None:
    """用浏览器加载文章页面，精准提取 .article-body 并深度清洗。"""
    try:
        driver.get(url)
        time.sleep(PAGE_LOAD_WAIT)

        soup = BeautifulSoup(driver.page_source, "html.parser")

        # ── 提取标题 ──────────────────────────────────────────
        h1 = soup.find("h1")
        if not h1:
            return None
        title = h1.get_text(strip=True)
        if not title:
            return None

        # ── 定位正文容器 ──────────────────────────────────────
        article_body = soup.find(class_="article-body")
        if not article_body:
            article_body = soup.find("article")
        if not article_body:
            return None

        # ── 深度清洗：彻底销毁脏数据 ─────────────────────────
        for selector in [
            "article-image", "inline-ad", "related-content",
            "ad-container", "newsletter-signup", "sidebar",
            "social-share", "article-tags", "promo",
            "callout", "pull-quote-container",
        ]:
            for tag in article_body.find_all(class_=selector):
                tag.decompose()

        for tag_name in ["figcaption", "figure", "script", "style", "iframe", "noscript", "svg"]:
            for tag in article_body.find_all(tag_name):
                tag.decompose()

        # ── 提取纯文本段落 ────────────────────────────────────
        paragraphs = article_body.find_all("p")
        clean_paragraphs = [
            p.get_text(strip=True)
            for p in paragraphs
            if len(p.get_text(strip=True)) > 40
        ]
        content = "\n".join(clean_paragraphs)

        if len(content) < MIN_CONTENT_LENGTH:
            return None

        return {
            "title": title,
            "content": content,
            "category": "science",
        }

    except Exception as exc:
        print(f"  -> Error: {exc}")
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
    print("  Smithsonian Magazine Science Corpus Fetcher (Selenium)")
    print("=" * 60)

    driver = create_driver()

    try:
        # 1) 先访问首页让 Cloudflare cookie 生效
        print("\n[Init] Loading Smithsonian homepage for Cloudflare cookie...")
        driver.get(BASE_URL)
        wait_for_cloudflare(driver, timeout=90)
        time.sleep(3)

        # 2) 获取文章链接
        urls = get_article_links(driver)
        if not urls:
            print("[ABORT] No article links found.")
            return

        # 3) 逐篇抓取并清洗
        print(f"\n[Fetching] Downloading {len(urls)} articles...")
        new_articles: list[dict] = []
        failed = 0

        for i, url in enumerate(urls, 1):
            print(f"  [{i}/{len(urls)}] {url[:80]}...")
            article = fetch_clean_article(driver, url)
            if article:
                new_articles.append(article)
                print(f"    OK: \"{article['title'][:50]}\" ({len(article['content'])} chars)")
            else:
                failed += 1

        print(f"\n[Result] {len(new_articles)} passed / {failed} filtered out")

        if not new_articles:
            print("[WARN] No articles passed the quality filter.")
            return

        # 4) 集成到现有语料库
        existing = load_existing_corpus()
        existing_count = len(existing)

        tagged = tag_existing_articles(existing)
        if tagged:
            print(f"[Tag] Marked {tagged} existing articles as 'history'")

        existing_titles = {entry.get("title", "") for entry in existing}
        added = 0
        for article in new_articles:
            if article["title"] not in existing_titles:
                existing.append(article)
                existing_titles.add(article["title"])
                added += 1

        save_corpus(existing)

        print(f"\n{'=' * 60}")
        print(f"  Corpus: {existing_count} existing + {added} new science")
        print(f"  Total: {len(existing)} articles")
        print(f"  Duplicates skipped: {len(new_articles) - added}")
        print(f"{'=' * 60}")

    finally:
        driver.quit()
        print("[Done] Browser closed.")


if __name__ == "__main__":
    main()
