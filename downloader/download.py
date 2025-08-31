import os
import time
import asyncio # Add this import
from concurrent.futures import ThreadPoolExecutor

import cloudscraper
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TransferSpeedColumn, TimeRemainingColumn

from downloader.scraper import get_image_urls, BASE_HEADERS
from config import MAX_IMAGE_THREADS, RETRY_ATTEMPTS, DOWNLOAD_PATH

console = Console()

# cloudscraper init
scraper = cloudscraper.create_scraper(
    browser={"browser": "chrome", "platform": "windows", "mobile": False}
)

console = Console()

def download_image(scraper, url: str, path: str, chapter_url: str, retries: int = RETRY_ATTEMPTS):
    """
    Downloads an image from a URL to a specified path with retries.
    """
    for attempt in range(retries):
        try:
            # Add Referer header dynamically for cloudscraper
            headers = BASE_HEADERS.copy()
            headers["Referer"] = chapter_url # Use the chapter_url as the Referer

            response = scraper.get(url, headers=headers, stream=True, timeout=10)
            response.raise_for_status()
            with open(path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except Exception as e: # Catching general Exception for cloudscraper errors
            console.print(f"[bold yellow]Attempt {attempt + 1}/{retries} failed for {url}:[/bold yellow] {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt) # Exponential backoff
            else:
                console.print(f"[bold red]Failed to download image from {url} after {retries} attempts.[/bold red]")
                return False

async def download_chapter(chapter_url: str, manga_title: str, chapter_name: str, overall_progress=None):
    """
    Downloads all images for a given chapter.
    """
    local_console = overall_progress.console if overall_progress else console
    local_console.print(f"Downloading chapter: [bold blue]{chapter_name}[/bold blue]")
    
    # Create directory for the manga and chapter
    manga_dir = os.path.join(DOWNLOAD_PATH, manga_title.replace(" ", "_"))
    chapter_dir = os.path.join(manga_dir, chapter_name.replace(" ", "_"))
    os.makedirs(chapter_dir, exist_ok=True)

    # Get image URLs from the chapter URL
    image_urls = await get_image_urls(chapter_url) # Await the async function
    if not image_urls:
        local_console.print(f"[bold red]No images found for {chapter_name}. Skipping download.[/bold red]")
        return chapter_dir # Return chapter_dir even if no images found
    
    progress_context = None # Initialize to None
    # Use overall_progress to add a task for this chapter's image downloads
    # If overall_progress is None (for standalone testing), create a temporary one.
    if overall_progress is None:
        progress_context = Progress(
            TextColumn("[bold blue]{task.description}", justify="right"),
            BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.1f}%",
            "•",
            TransferSpeedColumn(),
            "•",
            TimeRemainingColumn(),
            console=local_console,
        )
        progress_context.__enter__() # Manually enter the context
        progress = progress_context
    else:
        progress = overall_progress

    task = progress.add_task(f"[cyan]Downloading {chapter_name} images...", total=len(image_urls))
    
    # Use ThreadPoolExecutor for concurrent image downloads
    # Note: ThreadPoolExecutor is not ideal for async functions.
    # For truly async image downloads, aiohttp or similar would be better.
    # However, for simplicity and to integrate cloudscraper, we'll keep this for now.
    with ThreadPoolExecutor(max_workers=MAX_IMAGE_THREADS) as executor:
        futures = []
        loop = asyncio.get_event_loop() # Get the current event loop
        for i, img_url in enumerate(image_urls):
            img_path = os.path.join(chapter_dir, f"page_{i+1}.png") # Use page_x.png for consistent naming
            futures.append(loop.run_in_executor(executor, download_image, scraper, img_url, img_path, chapter_url, RETRY_ATTEMPTS))
        
        # Await all futures
        for future in asyncio.as_completed(futures):
            if await future: # Await the future result
                progress.update(task, advance=1)
            else:
                pass
    
    # Ensure the task is completed and removed from the progress bar
    progress.remove_task(task)

    # If a temporary progress context was created, exit it.
    if overall_progress is None and progress_context is not None: # Check if it was actually created
        progress_context.__exit__(None, None, None)

    local_console.print(f"[bold green]Finished downloading {chapter_name}[/bold green]")
    return chapter_dir # Return chapter_dir for conversion

if __name__ == "__main__":
    # Example usage for testing
    test_manga_title = "Eleceed"
    test_chapter_name = "Chapter 1"
    test_chapter_url = "https://mangabuddy.com/eleceed-chapter-1" # This URL needs to be scraped for actual image links

    # Need to run the async function
    import asyncio
    async def test_download():
        await download_chapter(test_chapter_url, test_manga_title, test_chapter_name)
    
    asyncio.run(test_download())