import requests
from bs4 import BeautifulSoup
from rich.console import Console

console = Console()

def get_manga_details(url: str):
    """
    Scrapes manga title and chapter URLs from a MangaBuddy URL.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors

        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract manga title
        title_tag = soup.find('div', class_='name box').find('h1') if soup.find('div', class_='name box') else None
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

def get_image_urls(chapter_url: str):
    """
    Scrapes image URLs from a given MangaBuddy chapter URL.
    """
    try:
        response = requests.get(chapter_url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # MangaBuddy image containers are divs with class 'chapter-image'
        image_containers = soup.find_all('div', class_='chapter-image')
        image_urls = []
        for container in image_containers:
            img_tag = container.find('img')
            if img_tag:
                # Prioritize 'data-src' if available, otherwise use 'src'
                img_src = img_tag.get('data-src') or img_tag.get('src')
                if img_src and img_src.startswith('http'): # Ensure it's a full URL
                    image_urls.append(img_src)
        return image_urls

    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Error fetching chapter URL:[/bold red] {e}")
        return []
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred during image scraping:[/bold red] {e}")
        return []

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
        image_urls = get_image_urls(first_chapter_url)
        if image_urls:
            console.print(f"[bold green]Found {len(image_urls)} images for the first chapter.[/bold green]")
            for i, img_url in enumerate(image_urls[:3]): # Print first 3 image URLs
                console.print(f"  {i+1}. {img_url}")
            if len(image_urls) > 3:
                console.print(f"  ...and {len(image_urls) - 3} more images.")
        else:
            console.print("[bold red]No image URLs found for the first chapter.[/bold red]")