#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test single Moltbook post"""
import os
import sys
import asyncio
import aiohttp
from pathlib import Path
from dotenv import load_dotenv

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Load .env
load_dotenv(Path(__file__).parent.parent / '.env')

MOLTBOOK_HOST_KEY = os.getenv("MOLTBOOK_HOST_KEY", "")
BASE_URL = "https://www.moltbook.com/api/v1"

async def test_single_post():
    """Test posting a single message to Moltbook"""
    
    if not MOLTBOOK_HOST_KEY:
        print("错误：未设置 MOLTBOOK_HOST_KEY")
        return
    
    print("=" * 60)
    print("MOLTBOOK 单次发帖测试")
    print("=" * 60)
    print(f"\nAPI Key: {MOLTBOOK_HOST_KEY[:20]}...")
    print(f"API URL: {BASE_URL}")
    
    title = "Port Monad 测试帖子"
    content = """
**Port Monad World Report**

这是一个测试帖子，用于验证 Moltbook API 集成。

Tick: 1
Active Agents: 3

**Market Prices:**
- Iron: 10 credits
- Wood: 8 credits
- Fish: 5 credits

---
*Port Monad: A persistent world for AI agents on Monad*
"""
    
    print("\n正在发帖...")
    print(f"标题: {title}")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{BASE_URL}/posts",
                headers={
                    "Authorization": f"Bearer {MOLTBOOK_HOST_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "submolt": "general",
                    "title": title,
                    "content": content
                }
            ) as resp:
                print(f"\n响应状态: {resp.status}")
                
                if resp.status in [200, 201]:
                    data = await resp.json()
                    post_id = data.get("id", "")
                    print(f"[SUCCESS] 发帖成功!")
                    print(f"   帖子 ID: {post_id}")
                    print(f"   返回数据: {data}")
                    return post_id
                elif resp.status == 429:
                    text = await resp.text()
                    print(f"[RATE LIMIT] 速率限制 - 请求太频繁")
                    print(f"   状态码: {resp.status}")
                    print(f"   响应: {text}")
                    print(f"\n建议：等待 1-2 分钟后再试")
                    return None
                else:
                    text = await resp.text()
                    print(f"[FAILED] 发帖失败")
                    print(f"   状态码: {resp.status}")
                    print(f"   错误信息: {text}")
                    return None
                    
        except Exception as e:
            print(f"[ERROR] 发生错误: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(test_single_post())
