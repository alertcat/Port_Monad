#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test Moltbook post with automatic retry"""
import os
import sys
import asyncio
import aiohttp
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Load .env
load_dotenv(Path(__file__).parent.parent / '.env')

MOLTBOOK_HOST_KEY = os.getenv("MOLTBOOK_HOST_KEY", "")
MOLTBOOK_MINER_KEY = os.getenv("MOLTBOOK_MINER_KEY", "")
MOLTBOOK_TRADER_KEY = os.getenv("MOLTBOOK_TRADER_KEY", "")
MOLTBOOK_GOVERNOR_KEY = os.getenv("MOLTBOOK_GOVERNOR_KEY", "")

BASE_URL = "https://www.moltbook.com/api/v1"

async def post_to_moltbook(session, api_key, title, content):
    """Post to Moltbook"""
    try:
        async with session.post(
            f"{BASE_URL}/posts",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "submolt": "general",
                "title": title,
                "content": content
            }
        ) as resp:
            if resp.status in [200, 201]:
                data = await resp.json()
                return {"success": True, "data": data}
            elif resp.status == 429:
                data = await resp.json()
                retry_after = data.get("retry_after_seconds", 60)
                return {"success": False, "error": "rate_limit", "retry_after": retry_after}
            else:
                text = await resp.text()
                return {"success": False, "error": f"HTTP {resp.status}", "message": text}
    except Exception as e:
        return {"success": False, "error": "exception", "message": str(e)}

async def comment_on_post(session, api_key, post_id, content):
    """Comment on a Moltbook post"""
    try:
        async with session.post(
            f"{BASE_URL}/posts/{post_id}/comments",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={"content": content}
        ) as resp:
            if resp.status in [200, 201]:
                return {"success": True}
            else:
                return {"success": False, "status": resp.status}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def main():
    """Main test with retry logic"""
    
    if not MOLTBOOK_HOST_KEY:
        print("错误：未设置 MOLTBOOK_HOST_KEY")
        return
    
    print("=" * 70)
    print("MOLTBOOK 发帖测试 - 带自动重试")
    print("=" * 70)
    print(f"\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API: {BASE_URL}")
    print(f"Host Key: {MOLTBOOK_HOST_KEY[:20]}...")
    
    # Test post content
    title = f"Port Monad Demo - {datetime.now().strftime('%H:%M:%S')}"
    content = """
**Port Monad World Report**

这是一个 Moltbook 集成测试。

Tick: 1
Active Agents: 3

**Market Prices:**
- Iron: 10 credits
- Wood: 8 credits  
- Fish: 5 credits

**Agent Status:**
- MinerBot: at mine, 1000 credits
- TraderBot: at market, 1000 credits
- GovernorBot: at dock, 1000 credits

---
*Port Monad: A persistent world for AI agents on Monad*
"""
    
    async with aiohttp.ClientSession() as session:
        # Try to post
        print(f"\n[1/3] 尝试发帖...")
        print(f"标题: {title}")
        
        result = await post_to_moltbook(session, MOLTBOOK_HOST_KEY, title, content)
        
        if result["success"]:
            post_id = result["data"].get("id", "")
            print(f"[SUCCESS] 发帖成功!")
            print(f"   帖子 ID: {post_id}")
            
            # Test comments
            print(f"\n[2/3] 测试评论功能...")
            
            bots = [
                ("MinerBot", MOLTBOOK_MINER_KEY, "MinerBot reporting! Currently mining iron in the mines. 🔨"),
                ("TraderBot", MOLTBOOK_TRADER_KEY, "TraderBot here! Watching the market prices closely. 📈"),
                ("GovernorBot", MOLTBOOK_GOVERNOR_KEY, "GovernorBot checking in! Managing the world state. 🏛️")
            ]
            
            for bot_name, bot_key, comment_text in bots:
                if bot_key:
                    await asyncio.sleep(2)  # Rate limiting
                    result = await comment_on_post(session, bot_key, post_id, comment_text)
                    if result["success"]:
                        print(f"   [OK] {bot_name} 评论成功")
                    else:
                        print(f"   [FAILED] {bot_name} 评论失败: {result}")
                else:
                    print(f"   [SKIP] {bot_name} (未配置 API key)")
            
            print(f"\n[3/3] 测试完成!")
            print(f"\n可以访问 Moltbook 查看帖子: https://www.moltbook.com/m/general/posts/{post_id}")
            
        elif result["error"] == "rate_limit":
            retry_after = result["retry_after"]
            print(f"[RATE LIMIT] 速率限制")
            print(f"   需要等待: {retry_after} 秒 ({retry_after // 60} 分钟 {retry_after % 60} 秒)")
            
            # Ask user if they want to wait
            print(f"\n是否等待并重试? (将在 {retry_after} 秒后自动重试)")
            print(f"按 Ctrl+C 取消...")
            
            try:
                # Show countdown
                for remaining in range(retry_after, 0, -10):
                    print(f"   等待中... 剩余 {remaining} 秒", end='\r')
                    await asyncio.sleep(min(10, remaining))
                
                print("\n\n重试发帖...")
                result = await post_to_moltbook(session, MOLTBOOK_HOST_KEY, title, content)
                
                if result["success"]:
                    post_id = result["data"].get("id", "")
                    print(f"[SUCCESS] 重试成功!")
                    print(f"   帖子 ID: {post_id}")
                    print(f"   访问: https://www.moltbook.com/m/general/posts/{post_id}")
                else:
                    print(f"[FAILED] 重试失败: {result}")
            
            except KeyboardInterrupt:
                print("\n\n[CANCELLED] 用户取消")
        
        else:
            print(f"[FAILED] 发帖失败")
            print(f"   错误: {result}")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
