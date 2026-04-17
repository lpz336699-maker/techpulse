"""
TechPulse - AI技术情报站
核心模块：数据源管理 + 爬虫 + AI摘要
"""

import feedparser
import httpx
import json
import os
from datetime import datetime
from typing import List, Optional
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# 初始化OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

# ============================================================
# 数据模型
# ============================================================

class Article:
    def __init__(self, title, url, source, published, summary, credibility_score=7):
        self.id = f"{hash(url)}"[:12]
        self.title = title
        self.url = url
        self.source = source
        self.published = published
        self.summary = summary  # 原始摘要
        self.ai_summary = None   # AI生成摘要
        self.credibility_score = credibility_score
        self.domain = source.lower().replace(" ", "-")
        self.created_at = datetime.now().isoformat()

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "published": self.published,
            "summary": self.summary[:200] + "..." if len(self.summary) > 200 else self.summary,
            "ai_summary": self.ai_summary,
            "credibility_score": self.credibility_score,
            "domain": self.domain
        }

# ============================================================
# 预置订阅源
# ============================================================

RSS_FEEDS = [
    {"name": "Hacker News AI", "url": "https://hnrss.org/newest?q=AI%20OR%20machine%20learning%20OR%20GPT", "score": 9},
    {"name": "MIT Tech Review", "url": "https://www.technologyreview.com/feed/", "score": 9},
    {"name": "VentureBeat AI", "url": "https://venturebeat.com/ai/feed/", "score": 8},
    {"name": "The Verge AI", "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "score": 8},
    {"name": "arXiv cs.AI", "url": "https://rss.arxiv.org/rss/cs.AI", "score": 9},
    {"name": "AI Weekly", "url": "https://www.wearemarketers.io/feed/", "score": 7},
    {"name": "DeepMind Blog", "url": "https://deepmind.com/blog/feed/basic/", "score": 10},
    {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss/", "score": 10},
    {"name": "Anthropic Blog", "url": "https://www.anthropic.com/news/rss", "score": 10},
    {"name": "Google AI Blog", "url": "https://blog.google/technology/ai/rss/", "score": 9},
]

# ============================================================
# 爬虫核心
# ============================================================

def parse_rss_feed(feed_info: dict) -> List[Article]:
    """解析单个RSS源"""
    articles = []
    try:
        feed = feedparser.parse(feed_info["url"])

        for entry in feed.entries[:10]:  # 每个源最多取10条
            # 提取标题
            title = entry.get("title", "No Title")

            # 提取链接
            url = entry.get("link", "")
            if not url and hasattr(entry, 'links'):
                url = entry.links[0].href if entry.links else ""

            # 提取发布时间
            published = ""
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                dt = datetime(*entry.published_parsed[:6])
                published = dt.strftime("%Y-%m-%d %H:%M")
            else:
                published = datetime.now().strftime("%Y-%m-%d")

            # 提取摘要
            summary = ""
            if hasattr(entry, 'summary'):
                summary = BeautifulSoup(entry.summary, 'html.parser').get_text()
            elif hasattr(entry, 'description'):
                summary = BeautifulSoup(entry.description, 'html.parser').get_text()
            elif hasattr(entry, 'summary_detail'):
                summary = entry.summary_detail.get('value', '')

            if title and url:
                article = Article(
                    title=title,
                    url=url,
                    source=feed_info["name"],
                    published=published,
                    summary=summary,
                    credibility_score=feed_info["score"]
                )
                articles.append(article)

    except Exception as e:
        print(f"[ERROR] Failed to parse {feed_info['name']}: {e}")

    return articles

def fetch_all_articles() -> List[Article]:
    """抓取所有订阅源"""
    all_articles = []

    for feed in RSS_FEEDS:
        articles = parse_rss_feed(feed)
        all_articles.extend(articles)
        print(f"[OK] {feed['name']}: {len(articles)} articles")

    # 按发布时间排序
    all_articles.sort(key=lambda x: x.published, reverse=True)

    # 去重（基于标题相似度）
    seen = set()
    unique_articles = []
    for article in all_articles:
        title_key = article.title.lower()[:50]
        if title_key not in seen:
            seen.add(title_key)
            unique_articles.append(article)

    return unique_articles

# ============================================================
# AI摘要功能
# ============================================================

def generate_ai_summary(article: Article) -> str:
    """使用GPT生成文章摘要"""
    if not article.summary:
        return "无法生成摘要：原文内容为空"

    try:
        prompt = f"""请为以下技术文章生成一个简洁的中文摘要（50字以内）：

标题：{article.title}
来源：{article.source}
内容：{article.summary[:500]}

要求：
1. 提炼文章的核心观点或技术要点
2. 用中文回答
3. 50字以内
4. 直接输出摘要，不要前缀"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "你是一个专业的技术资讯编辑，擅长提炼文章要点。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.7
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"[ERROR] AI summary failed for {article.title[:30]}: {e}")
        return f"[AI摘要生成失败] {article.summary[:100]}..."

def generate_ai_summaries_batch(articles: List[Article], limit: int = 5) -> List[Article]:
    """批量为文章生成AI摘要（默认处理最新5条）"""
    count = 0
    for article in articles:
        if count >= limit:
            break
        if not article.ai_summary:
            print(f"[AI] Generating summary for: {article.title[:40]}...")
            article.ai_summary = generate_ai_summary(article)
            count += 1
    return articles

# ============================================================
# 数据存储（内存）
# ============================================================

class DataStore:
    def __init__(self):
        self.articles: List[Article] = []
        self.last_updated: Optional[str] = None

    def update(self, articles: List[Article]):
        self.articles = articles
        self.last_updated = datetime.now().isoformat()

    def get_all(self) -> List[dict]:
        return [a.to_dict() for a in self.articles]

    def get_by_id(self, article_id: str) -> Optional[dict]:
        for a in self.articles:
            if a.id == article_id:
                return a.to_dict()
        return None

    def add_summary(self, article_id: str, summary: str) -> bool:
        for a in self.articles:
            if a.id == article_id:
                a.ai_summary = summary
                return True
        return False

# 全局数据存储
store = DataStore()

# ============================================================
# 主函数
# ============================================================

def initialize_data():
    """初始化数据"""
    print("=" * 50)
    print("TechPulse 正在抓取数据...")
    print("=" * 50)

    articles = fetch_all_articles()
    print(f"\n[INFO] 共抓取 {len(articles)} 篇文章")

    # 生成AI摘要
    print("\n[INFO] 正在生成AI摘要（处理最新5条）...")
    articles = generate_ai_summaries_batch(articles, limit=5)

    store.update(articles)

    print(f"[INFO] 数据更新完成！最后更新时间: {store.last_updated}")
    return store.get_all()

if __name__ == "__main__":
    articles = initialize_data()
    print(f"\n📰 已加载 {len(articles)} 条资讯")
