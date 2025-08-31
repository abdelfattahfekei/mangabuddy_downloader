# config.py

MAX_CHAPTER_THREADS = 5
MAX_IMAGE_THREADS = 10
DOWNLOAD_PATH = './downloads/'
DELETE_IMAGES_AFTER_CONVERSION = False
RETRY_ATTEMPTS = 3

# Playwright settings
PLAYWRIGHT_HEADLESS = True
PLAYWRIGHT_WAIT_AFTER_NAV = 5000 # milliseconds to wait after navigation
PLAYWRIGHT_WARNING_BUTTON_TIMEOUT = 5000 # milliseconds to wait for 18+ warning button
PLAYWRIGHT_WAIT_AFTER_WARNING_CLICK = 2000 # milliseconds to wait after clicking 18+ warning
PLAYWRIGHT_IMAGE_LOAD_WAIT = 5000 # milliseconds to wait for images to load