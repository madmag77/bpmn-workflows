from __future__ import annotations

from typing import List, Optional
from urllib.parse import quote_plus
import random
import time
import os

import undetected_chromedriver as uc
from fake_useragent import UserAgent
from selenium import webdriver


WEB_SEARCH_URL = os.getenv("WEB_SEARCH_URL")
FILTER_OUT_TAGS = os.getenv("FILTER_OUT_TAGS", "").split(",") if os.getenv("FILTER_OUT_TAGS") else []

def search_and_scrape(
    query: str,
    top_k: int = 3,
    base_url: str = WEB_SEARCH_URL,
    filter_out_tags: Optional[list[str]] | None = FILTER_OUT_TAGS,
) -> List[str]:
    """Search the web using a headless browser and return page chunks."""
    ua = UserAgent()
    options = uc.ChromeOptions()
    options.headless = True
    options.add_argument(f'--user-agent={ua.random}')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("--incognito")
    options.add_argument("--disable-search-engine-choice-screen")
    
    try:
        driver = webdriver.Chrome(options=options)
        
        search_url = f"{base_url}?q={quote_plus(query)}"

        driver.get(search_url)
        time.sleep(random.uniform(2, 4))
        
        links = []
        elements = driver.find_elements("tag name", "a")
        for element in elements:
            href = element.get_attribute("href")
            if href and all(tag not in href for tag in filter_out_tags): 
                links.append(href)
                if len(links) >= top_k:
                    break
                    
        chunks = []
        for link in links:
            try:
                driver.get(link)
                time.sleep(random.uniform(2, 5))
                
                page_text = driver.find_element("tag name", "body").text
                if page_text:
                    # Clean and normalize the text
                    text = " ".join(page_text.split())
                    if len(text) > 100:  # Only keep substantial content
                        chunks.append(text[:10000])  # Limit chunk size
            except Exception as e:
                print(f"Failed to fetch {link}: {str(e)}")
                continue
                       
        return {"chunks": chunks}
        
    except Exception as e:
        print(f"Browser automation failed: {str(e)}")
        raise e
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass