import requests
from bs4 import BeautifulSoup
from rich.console import Console
from playwright.async_api import async_playwright
from config import (
    PLAYWRIGHT_HEADLESS,
    PLAYWRIGHT_WAIT_AFTER_NAV,
    PLAYWRIGHT_WARNING_BUTTON_TIMEOUT,
    PLAYWRIGHT_WAIT_AFTER_WARNING_CLICK,
    PLAYWRIGHT_IMAGE_LOAD_WAIT,
)
import re
import asyncio

console = Console()

# Base HEADERS, Referer will be added dynamically where needed
BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

def get_manga_details(url: str):
    """
    Scrapes manga title and chapter URLs from a MangaBuddy URL.
    """
    try:
        # Add Referer header dynamically for requests.get
        headers = BASE_HEADERS.copy()
        headers["Referer"] = url
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors

        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract manga title
        name_box = soup.find('div', class_='name box')
        title_tag = name_box.find('h1') if name_box else None
        manga_title = title_tag.get_text(strip=True) if title_tag else "Unknown Title"

        # Extract chapter URLs
        chapter_list_ul = soup.find('ul', class_='chapter-list', id='chapter-list')
        chapters = []
        if chapter_list_ul:
            for a_tag in chapter_list_ul.find_all('a', href=True): # Ensure href attribute exists
                chapter_url = a_tag.get('href')
                chapter_name_tag = a_tag.find('strong', class_='chapter-title')
                chapter_name = chapter_name_tag.get_text(strip=True) if chapter_name_tag else "Unknown Chapter"
                if chapter_url: # Only add if URL is present
                    # MangaBuddy chapter URLs are relative, prepend base URL
                    chapters.append({"name": chapter_name, "url": f"https://mangabuddy.com{chapter_url}"})
        
        # MangaBuddy chapters are usually listed in descending order, reverse to get ascending.
        chapters.reverse()

        return manga_title, chapters

    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Error fetching URL:[/bold red] {e}")
        return None, None
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred during scraping manga details:[/bold red] {e}")
        return None, None

async def get_image_urls(chapter_url: str):
    """
    Scrapes image URLs from a given MangaBuddy chapter URL using Playwright.
    """
    img_urls = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=PLAYWRIGHT_HEADLESS)
        # Create a new context with the base headers and dynamic Referer
        context_headers = BASE_HEADERS.copy()
        context_headers["Referer"] = chapter_url # Set Referer for the chapter page
        context = await browser.new_context(user_agent=context_headers["User-Agent"], extra_http_headers=context_headers)
        page = await context.new_page()

        try:
            console.print(f"Navigating to {chapter_url} ...")
            await page.goto(chapter_url, wait_until="domcontentloaded", timeout=PLAYWRIGHT_WAIT_AFTER_NAV)

            # 🚨 Check for 18+ warning and click "Accept"
            try:
                button = await page.wait_for_selector("button.btn.btn-warning", timeout=PLAYWRIGHT_WARNING_BUTTON_TIMEOUT)
                if button:
                    console.print("⚠️ Age warning detected → clicking Accept...")
                    await button.click()
                    await page.wait_for_timeout(PLAYWRIGHT_WAIT_AFTER_WARNING_CLICK)  # short wait after click
            except:
                console.print("✅ No age warning")

            # ⏳ Wait for all images to load
            console.print("⌛ Waiting for images to load...")
            await page.wait_for_timeout(PLAYWRIGHT_IMAGE_LOAD_WAIT)

            # Grab all image URLs
            img_urls = await page.eval_on_selector_all(
                "div.chapter-image img",
                "imgs => imgs.map(img => img.getAttribute('data-src') || img.getAttribute('src'))"
            )
            # Clean URLs
            img_urls = [re.sub(r"\?.*$", "", u) for u in img_urls if u]

            console.print(f"✅ Found {len(img_urls)} images")

        except Exception as e:
            console.print(f"[bold red]An error occurred during Playwright scraping:[/bold red] {e}")
        finally:
            await browser.close()
    return img_urls

if __name__ == "__main__":
    # Example usage for testing get_manga_details
    test_manga_url = "https://mangabuddy.com/codename-anastasia"
    title, chapter_data = get_manga_details(test_manga_url)

    if title and chapter_data:
        console.print(f"\n[bold green]Manga Title:[/bold green] {title}")
        console.print("[bold green]Chapters:[/bold green]")
        for i, chapter in enumerate(chapter_data[:5]): # Print first 5 chapters for brevity
            console.print(f"  {i+1}. [cyan]{chapter['name']}[/cyan]: {chapter['url']}")
        if len(chapter_data) > 5:
            console.print(f"  ...and {len(chapter_data) - 5} more chapters.")
    
    # Example usage for testing get_image_urls
    if chapter_data and len(chapter_data) > 0:
        first_chapter_url = chapter_data[0]['url']
        console.print(f"\n[bold green]Testing image scraping for:[/bold green] {first_chapter_url}")
        # Need to run the async function
        image_urls = asyncio.run(get_image_urls(first_chapter_url))
        if image_urls:
            console.print(f"[bold green]Found {len(image_urls)} images for the first chapter.[/bold green]")
            for i, img_url in enumerate(image_urls[:3]): # Print first 3 image URLs
                console.print(f"  {i+1}. {img_url}")
            if len(image_urls) > 3:
                console.print(f"  ...and {len(image_urls) - 3} more images.")
        else:
            console.print("[bold red]No image URLs found for the first chapter.[/bold red]")