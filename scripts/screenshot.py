import asyncio
from playwright.async_api import async_playwright

BASE = "http://localhost:8000"
OUT  = r"c:\Projetos\Sistema tarefas\scripts\screenshots"

import os; os.makedirs(OUT, exist_ok=True)

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await ctx.new_page()

        # 1. Login page
        await page.goto(f"{BASE}/auth/login")
        await page.screenshot(path=f"{OUT}/01_login.png")
        print("01_login.png")

        # 2. Setup (first run – may redirect to login if user exists)
        await page.goto(f"{BASE}/auth/setup")
        await page.screenshot(path=f"{OUT}/02_setup.png")
        print("02_setup.png")

        # 3. Login
        await page.goto(f"{BASE}/auth/login")
        await page.fill("input[name=email]", "brasildjavansantos@gmail.com")
        await page.fill("input[name=password]", "senha123")
        await page.click("button[type=submit]")
        await page.wait_for_url(f"{BASE}/dashboard")
        await page.screenshot(path=f"{OUT}/03_dashboard.png")
        print("03_dashboard.png")

        # 4. Projects
        await page.goto(f"{BASE}/projects")
        await page.screenshot(path=f"{OUT}/04_projects.png")
        print("04_projects.png")

        # 5. Missions
        await page.goto(f"{BASE}/missions")
        await page.screenshot(path=f"{OUT}/05_missions.png")
        print("05_missions.png")

        # 6. Mission detail
        await page.goto(f"{BASE}/missions/1")
        await page.screenshot(path=f"{OUT}/06_mission_detail.png")
        print("06_mission_detail.png")

        # 7. Capture
        await page.goto(f"{BASE}/capture")
        await page.screenshot(path=f"{OUT}/07_capture.png")
        print("07_capture.png")

        # 8. Process
        await page.goto(f"{BASE}/process")
        await page.screenshot(path=f"{OUT}/08_process.png")
        print("08_process.png")

        await browser.close()
        print("Done.")

asyncio.run(run())
