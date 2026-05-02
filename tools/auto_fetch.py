import json
import time
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# 伪装头部
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
}

# 抓取数量限制 (先设置个 100 篇测试一下水，你可以随时改到 1000)
MAX_ARTICLES = 1000

def get_all_article_links():
    """第一步：从网站的索引/分类页，像蜘蛛一样把所有真实链接抓出来"""
    print("🕸️ 正在获取全站真实的链接地图...")
    
    # 世界历史百科有一个 A-Z 的索引页
    index_url = "https://www.worldhistory.org/index/"
    
    try:
        response = requests.get(index_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        real_links = []
        # 寻找索引页里所有指向文章的 <a> 标签
        # (通常他们的文章链接没有特殊前缀，直接挂在域名下)
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            # 过滤掉关于我们、赞助、图片等非文章链接
            if href.startswith('/') and not any(x in href for x in ['/image/', '/video/', '/collection/', '/about/']):
                full_url = f"https://www.worldhistory.org{href}"
                if full_url not in real_links:
                    real_links.append(full_url)
                    
        print(f"✅ 成功从索引中提取了 {len(real_links)} 个真实的主题链接！")
        return real_links
        
    except Exception as e:
        print(f"❌ 获取全站链接失败: {e}")
        return []

def fetch_clean_article(url):
    """第二步：精准打击，下载并物理超度脏数据"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 🔪 核心清洗逻辑：斩草除根
        for tag in soup.find_all(['figure', 'figcaption', 'img', 'script', 'style', 'iframe', 'nav', 'footer']):
            tag.decompose() 
            
        title_tag = soup.find('h1')
        if not title_tag:
            return None
        title = title_tag.get_text(strip=True)
        
        paragraphs = soup.find_all('p')
        content = "\n".join([p.get_text(strip=True) for p in paragraphs if len(p.text) > 80])
        
        return {"title": title, "content": content}
        
    except Exception:
        return None 

def ultimate_build_corpus():
    urls_to_scrape = get_all_article_links()
    
    if not urls_to_scrape:
        print("没有找到链接，爬虫终止。")
        return

    # 截取我们需要限制的数量
    urls_to_scrape = urls_to_scrape[:MAX_ARTICLES]
    
    print(f"\n🚀 开始精准抓取这 {len(urls_to_scrape)} 篇文章的内容...")
    corpus_data = []
    
    for url in tqdm(urls_to_scrape, desc="下载并清洗中"):
        article = fetch_clean_article(url)
        
        if article and len(article['content']) > 500:
            corpus_data.append(article)
            
        time.sleep(1) # 依然要保持礼貌，防止 IP 被拉黑

    with open('local_corpus.json', 'w', encoding='utf-8') as f:
        json.dump(corpus_data, f, ensure_ascii=False, indent=4)
        
    print(f"\n🎉 大满贯！成功从真实地图中提取了 {len(corpus_data)} 篇绝赞长文！")

if __name__ == "__main__":
    ultimate_build_corpus()