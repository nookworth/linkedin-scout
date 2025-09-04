"""
Company Navigator - Handles LinkedIn company page navigation and profile scraping
"""

import asyncio
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from linkedin_scout.types import BrowserConfig, Contact
import logging

logger = logging.getLogger(__name__)


class CompanyNavigator:
    """Handles navigation to LinkedIn company pages and profile extraction"""
    
    def __init__(self, config: BrowserConfig):
        self.config = config
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
        
    async def start(self):
        """Initialize browser and create page"""
        playwright = await async_playwright().start()
        
        # Launch browser with config settings
        self.browser = await playwright.chromium.launch(
            headless=self.config.headless,
            slow_mo=self.config.slow_mo
        )
        
        # Create context with user data dir for session persistence
        context_options = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        if self.config.user_data_dir:
            # Use persistent context for session persistence
            self.context = await self.browser.new_context(
                storage_state=self.config.user_data_dir,
                **context_options
            )
        else:
            self.context = await self.browser.new_context(**context_options)
            
        self.page = await self.context.new_page()
        
        # Set default timeout
        self.page.set_default_timeout(self.config.timeout)
        
        logger.info("Browser initialized successfully")
        
    async def close(self):
        """Clean up browser resources"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close() 
        if self.browser:
            await self.browser.close()
            
        logger.info("Browser closed")
        
    async def navigate_to_company_people(self, company_name: str) -> bool:
        """Navigate to a company's People page on LinkedIn"""
        if not self.page:
            raise RuntimeError("Browser not initialized. Use 'async with' or call start() first.")
            
        try:
            # First try direct company URL
            company_url = f"https://www.linkedin.com/company/{company_name.lower()}/people/"
            
            logger.info(f"Navigating to {company_url}")
            response = await self.page.goto(company_url, wait_until="networkidle")
            
            # Check if we're on the right page or need to search
            if "company" not in self.page.url or "people" not in self.page.url:
                logger.info(f"Direct URL failed, searching for company: {company_name}")
                return await self._search_and_navigate_to_company(company_name)
                
            # Wait for people section to load
            await self.page.wait_for_selector('[data-test-id="people-card"]', timeout=10000)
            
            logger.info(f"Successfully navigated to {company_name} people page")
            return True
            
        except Exception as e:
            logger.error(f"Failed to navigate to {company_name}: {e}")
            return False
            
    async def _search_and_navigate_to_company(self, company_name: str) -> bool:
        """Search for company and navigate to people page"""
        try:
            # Go to LinkedIn search
            await self.page.goto("https://www.linkedin.com/search/results/companies/")
            
            # Search for the company
            search_box = await self.page.wait_for_selector('input[aria-label="Search"]')
            await search_box.fill(company_name)
            await search_box.press("Enter")
            
            # Wait for results and click first company match
            first_company = await self.page.wait_for_selector('[data-test-id="search-result"] h3 a')
            company_url = await first_company.get_attribute('href')
            
            # Navigate to people page
            people_url = company_url.rstrip('/') + '/people/'
            await self.page.goto(people_url, wait_until="networkidle")
            
            return True
            
        except Exception as e:
            logger.error(f"Company search failed: {e}")
            return False
            
    async def filter_by_job_title(self, job_title: str) -> bool:
        """Apply job title filter on company people page"""
        try:
            # Look for filter buttons/dropdowns
            # LinkedIn's UI changes frequently, so we'll try multiple selectors
            filter_selectors = [
                'button[aria-label*="Current company filter"]',
                'button[aria-label*="Title filter"]', 
                '[data-test-id="filter-button"]',
                'button:has-text("All filters")'
            ]
            
            filter_button = None
            for selector in filter_selectors:
                try:
                    filter_button = await self.page.wait_for_selector(selector, timeout=5000)
                    break
                except:
                    continue
                    
            if not filter_button:
                logger.warning("Could not find filter button, attempting text search")
                return await self._search_in_people_results(job_title)
                
            # Click filter and add job title
            await filter_button.click()
            
            # Look for title input field
            title_input = await self.page.wait_for_selector('input[placeholder*="title"], input[placeholder*="Title"]')
            await title_input.fill(job_title)
            await title_input.press("Enter")
            
            # Apply filters
            apply_button = await self.page.wait_for_selector('button:has-text("Show results"), button:has-text("Apply")')
            await apply_button.click()
            
            # Wait for filtered results
            await self.page.wait_for_timeout(2000)
            
            logger.info(f"Applied job title filter: {job_title}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply job title filter: {e}")
            return False
            
    async def _search_in_people_results(self, job_title: str) -> bool:
        """Fallback: use page search to filter by job title"""
        try:
            # Use browser search functionality
            await self.page.keyboard.press("Control+F" if "win" in self.page.context.browser.platform else "Meta+F")
            await self.page.keyboard.type(job_title.lower())
            
            logger.info(f"Using text search for: {job_title}")
            return True
            
        except Exception as e:
            logger.error(f"Text search failed: {e}")
            return False
            
    async def extract_profiles(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Extract profile information from current people page"""
        profiles = []
        
        try:
            # Scroll to load more profiles
            await self._scroll_to_load_profiles(limit)
            
            # Extract profile cards
            profile_selectors = [
                '[data-test-id="people-card"]',
                '.entity-result',
                '.search-result__info',
                '.artdeco-entity-lockup'
            ]
            
            profile_cards = None
            for selector in profile_selectors:
                profile_cards = await self.page.query_selector_all(selector)
                if profile_cards:
                    break
                    
            if not profile_cards:
                logger.warning("No profile cards found")
                return profiles
                
            logger.info(f"Found {len(profile_cards)} profile cards")
            
            for i, card in enumerate(profile_cards[:limit]):
                try:
                    profile = await self._extract_single_profile(card)
                    if profile:
                        profiles.append(profile)
                        
                    # Rate limiting
                    if i % 10 == 0:
                        await asyncio.sleep(self.config.rate_limit_delay / 1000)
                        
                except Exception as e:
                    logger.warning(f"Failed to extract profile {i}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Profile extraction failed: {e}")
            
        logger.info(f"Extracted {len(profiles)} profiles")
        return profiles
        
    async def _scroll_to_load_profiles(self, target_count: int):
        """Scroll page to trigger loading of more profiles"""
        scroll_attempts = 0
        max_scrolls = 10
        
        while scroll_attempts < max_scrolls:
            # Scroll down
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            
            # Wait for potential new content
            await asyncio.sleep(2)
            
            # Check if we have enough profiles loaded
            profile_count = len(await self.page.query_selector_all('[data-test-id="people-card"], .entity-result'))
            
            if profile_count >= target_count:
                break
                
            scroll_attempts += 1
            
        logger.info(f"Completed {scroll_attempts} scroll attempts")
        
    async def _extract_single_profile(self, card_element) -> Optional[Dict[str, Any]]:
        """Extract information from a single profile card"""
        try:
            profile = {}
            
            # Name
            name_selectors = [
                'h3 a span[aria-hidden="true"]',
                '.entity-result__title-text a span:first-child',
                '.artdeco-entity-lockup__title a'
            ]
            
            for selector in name_selectors:
                name_elem = await card_element.query_selector(selector)
                if name_elem:
                    profile['name'] = await name_elem.text_content()
                    break
                    
            # Title/Position
            title_selectors = [
                '.entity-result__primary-subtitle',
                '.artdeco-entity-lockup__subtitle',
                '[data-test-id="people-card-subtitle"]'
            ]
            
            for selector in title_selectors:
                title_elem = await card_element.query_selector(selector)
                if title_elem:
                    profile['title'] = await title_elem.text_content()
                    break
                    
            # Profile URL
            url_selectors = [
                'h3 a',
                '.entity-result__title-text a',
                '.artdeco-entity-lockup__title a'
            ]
            
            for selector in url_selectors:
                url_elem = await card_element.query_selector(selector)
                if url_elem:
                    profile['profile_url'] = await url_elem.get_attribute('href')
                    break
                    
            # Location
            location_selectors = [
                '.entity-result__secondary-subtitle',
                '.artdeco-entity-lockup__caption'
            ]
            
            for selector in location_selectors:
                location_elem = await card_element.query_selector(selector)
                if location_elem:
                    profile['location'] = await location_elem.text_content()
                    break
                    
            # Only return if we have at least name and title
            if profile.get('name') and profile.get('title'):
                return profile
                
        except Exception as e:
            logger.warning(f"Failed to extract profile: {e}")
            
        return None