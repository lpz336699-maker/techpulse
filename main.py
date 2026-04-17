"""
TechPulse - FastAPI 服务
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import os
import asyncio
import threading

from crawler import store, initialize_data, generate_ai_summary, generate_ai_summaries_batch

# 创建FastAPI应用
app = FastAPI(title="TechPulse", description="AI技术情报站 API")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局锁
data_lock = threading.Lock()

# ============================================================
# 路由
# ============================================================

@app.on_event("startup")
async def startup_event():
    """启动时初始化数据"""
    print("🚀 TechPulse 启动中...")
    asyncio.create_task(run_crawler_async())

async def run_crawler_async():
    """异步运行爬虫"""
    await asyncio.to_thread(initialize_data)

# 首页
@app.get("/", response_class=HTMLResponse)
async def home():
    """返回前端页面"""
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

# API: 获取所有新闻
@app.get("/api/news")
async def get_news():
    """获取所有新闻"""
    with data_lock:
        return {
            "code": 0,
            "msg": "success",
            "data": store.get_all(),
            "total": len(store.articles),
            "last_updated": store.last_updated
        }

# API: 获取单条新闻详情
@app.get("/api/news/{article_id}")
async def get_news_detail(article_id: str):
    """获取单条新闻详情"""
    with data_lock:
        article = store.get_by_id(article_id)
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        return {"code": 0, "msg": "success", "data": article}

# API: 获取AI摘要
@app.get("/api/summary/{article_id}")
async def get_summary(article_id: str):
    """获取AI摘要（如果没有则生成）"""
    with data_lock:
        article_data = store.get_by_id(article_id)
        if not article_data:
            raise HTTPException(status_code=404, detail="Article not found")

        # 找到原始Article对象
        article = next((a for a in store.articles if a.id == article_id), None)
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")

        # 如果没有AI摘要，生成一个
        if not article.ai_summary:
            print(f"[API] Generating AI summary for {article_id}...")
            article.ai_summary = await asyncio.to_thread(generate_ai_summary, article)

        return {
            "code": 0,
            "msg": "success",
            "data": {
                "id": article.id,
                "title": article.title,
                "ai_summary": article.ai_summary
            }
        }

# API: 刷新数据
@app.post("/api/refresh")
async def refresh_data():
    """手动刷新数据"""
    print("[API] Refreshing data...")
    await asyncio.to_thread(initialize_data)
    return {
        "code": 0,
        "msg": "数据刷新成功",
        "total": len(store.articles)
    }

# API: 批量生成AI摘要
@app.post("/api/summaries/batch")
async def batch_summaries(limit: int = 10):
    """批量生成AI摘要"""
    with data_lock:
        asyncio.to_thread(generate_ai_summaries_batch, store.articles, limit)
    return {"code": 0, "msg": f"已提交 {limit} 条摘要生成任务"}

# 健康检查
@app.get("/health")
async def health():
    return {"status": "ok", "articles": len(store.articles)}

# ============================================================
# 启动
# ============================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
