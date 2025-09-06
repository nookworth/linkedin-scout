"""
Session Manager - Handles LinkedIn login session persistence with automatic authentication.
"""
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from ..types import BrowserConfig
from .logging_config import get_logger, log_error_with_context


class SessionManager:
    """Manages LinkedIn session persistence with automatic login fallback."""
    
    def __init__(self, session_dir: str = "./session_data"):
        """
        Initialize session manager.
        
        Args:
            session_dir: Directory to store session files
        """
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(exist_ok=True)
        self.storage_state_file = self.session_dir / "linkedin_storage_state.json"
        self.logger = get_logger("session")
    
    def has_valid_session(self) -> bool:
        """
        Check if we have a valid LinkedIn session.
        
        Returns:
            True if valid session exists, False otherwise
        """
        if not self.storage_state_file.exists():
            self.logger.debug("No storage state file found")
            return False
        
        try:
            with open(self.storage_state_file, 'r') as f:
                storage_state = json.load(f)
            
            # Check if session has LinkedIn cookies
            cookies = storage_state.get('cookies', [])
            linkedin_cookies = [c for c in cookies if 'linkedin.com' in c.get('domain', '')]
            
            has_cookies = len(linkedin_cookies) > 0
            self.logger.debug(f"Session validation - LinkedIn cookies found: {has_cookies}")
            return has_cookies
            
        except Exception as e:
            self.logger.warning(f"Session validation failed: {str(e)}")
            return False
    
    def get_storage_state_path(self) -> Optional[str]:
        """
        Get path to storage state file if valid session exists.
        
        Returns:
            Path to storage state file or None if no valid session
        """
        if self.has_valid_session():
            self.logger.info("Valid session found, returning storage state path")
            return str(self.storage_state_file)
        self.logger.info("No valid session found")
        return None
    
    async def save_storage_state(self, context) -> None:
        """
        Save browser storage state for session persistence.
        
        Args:
            context: Playwright browser context
        """
        try:
            self.logger.info("Saving browser storage state")
            storage_state = await context.storage_state()
            with open(self.storage_state_file, 'w') as f:
                json.dump(storage_state, f, indent=2)
            self.logger.info(f"Storage state saved successfully to {self.storage_state_file}")
                
        except Exception as e:
            log_error_with_context(self.logger, e, {"function": "save_storage_state"})
            raise RuntimeError(f"Failed to save session state: {e}")
    
    async def ensure_linkedin_login(self, page) -> bool:
        """
        Ensure user is logged into LinkedIn. Handle login if needed.
        
        Args:
            page: Playwright page object
            
        Returns:
            True if login successful, False otherwise
        """
        try:
            self.logger.info("Checking LinkedIn login status")
            
            # First check if already logged in
            await page.goto("https://www.linkedin.com/feed/", wait_until="networkidle")
            
            # Check if we're logged in by looking for navigation elements
            try:
                await page.wait_for_selector('[data-test-id="nav-global-index"], .global-nav__me, .nav__button-secondary', timeout=5000)
                self.logger.info("LinkedIn login verified - user is already logged in")
                return True
            except:
                self.logger.info("User not logged in, attempting automatic login")
            
            # If not logged in, try automatic login
            return await self._perform_login(page)
                
        except Exception as e:
            log_error_with_context(self.logger, e, {"function": "ensure_linkedin_login"})
            print(f"Login check failed: {e}")
            return False
    
    async def _perform_login(self, page) -> bool:
        """
        Perform LinkedIn login using environment credentials.
        
        Args:
            page: Playwright page object
            
        Returns:
            True if login successful, False otherwise
        """
        try:
            # Get credentials from environment
            email = os.getenv('LINKEDIN_EMAIL')
            password = os.getenv('LINKEDIN_PASSWORD')
            
            if not email or not password:
                print("\n🔐 LinkedIn credentials not found in environment variables.")
                print("Please set LINKEDIN_EMAIL and LINKEDIN_PASSWORD in your .env file or environment.")
                print("\nExample .env file:")
                print("LINKEDIN_EMAIL=your-email@example.com")
                print("LINKEDIN_PASSWORD=your-password")
                return False
            
            print("🔐 Attempting LinkedIn login...")
            
            # Navigate to login page
            await page.goto("https://www.linkedin.com/login", wait_until="networkidle")
            
            # Fill in credentials
            await page.fill('#username', email)
            await page.fill('#password', password)
            
            # Click sign in
            await page.click('button[type="submit"]')
            
            # Wait for login to complete
            try:
                await page.wait_for_selector('[data-test-id="nav-global-index"], .global-nav__me', timeout=15000)
                print("✅ LinkedIn login successful")
                return True
            except:
                # Check if we need to handle 2FA or captcha
                current_url = page.url
                if "challenge" in current_url or "checkpoint" in current_url:
                    print("⚠️ LinkedIn requires additional verification (2FA/captcha)")
                    print("Please complete verification in the browser and press Enter when done...")
                    input()
                    
                    # Check again after manual verification
                    try:
                        await page.wait_for_selector('[data-test-id="nav-global-index"], .global-nav__me', timeout=5000)
                        print("✅ LinkedIn login successful after verification")
                        return True
                    except:
                        print("❌ Login verification failed")
                        return False
                else:
                    print("❌ LinkedIn login failed - check credentials")
                    return False
                    
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    def clear_session(self) -> None:
        """Clear all saved session data."""
        if self.storage_state_file.exists():
            self.storage_state_file.unlink()
    
    def get_session_info(self) -> Dict[str, Any]:
        """
        Get information about the current session.
        
        Returns:
            Dictionary with session information
        """
        has_session = self.has_valid_session()
        has_credentials = bool(os.getenv('LINKEDIN_EMAIL') and os.getenv('LINKEDIN_PASSWORD'))
        
        return {
            "has_valid_session": has_session,
            "has_credentials": has_credentials,
            "storage_state_exists": self.storage_state_file.exists(),
            "session_file": str(self.storage_state_file)
        }