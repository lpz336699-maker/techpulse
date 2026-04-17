# TechPulse - AI技术情报站

> 自动化追踪AI/大模型领域最新技术动态，智能聚合后推送给AI产品经理

## 技术栈

- **后端**: Python + FastAPI
- **爬虫**: feedparser (RSS) + httpx
- **AI摘要**: OpenAI GPT-3.5-turbo
- **前端**: HTML + TailwindCSS + Vanilla JS
- **部署**: Netlify

## 数据源

### 预置订阅源 (MVP)
1. Hacker News (AI/ML)
2. MIT Technology Review
3. The Verge AI
4. VentureBeat AI
5. arXiv cs.AI
6. GitHub Trending (AI)
7. AI Weekly Newsletter
8. DeepMind Blog
9. OpenAI Blog
10. Anthropic Blog

## API Endpoints

- `GET /` - 首页资讯流
- `GET /api/news` - 获取所有新闻
- `GET /api/summary/:id` - 获取AI摘要
- `POST /api/subscribe` - 订阅领域
- `GET /api/refresh` - 手动刷新数据

## 运行

```bash
pip install -r requirements.txt
python main.py
```
