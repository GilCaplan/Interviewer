import unittest
import os
import sys
import asyncio
from playwright.async_api import async_playwright


class FeatureUITest(unittest.TestCase):
    """UI Tests for feature pages using Playwright async API"""

    async def asyncSetUp(self):
        """Initialize browser asynchronously"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        self.base_url = "http://localhost:3000"  # Update to match your React app URL

        # Navigate to the home page
        try:
            print(f"Navigating to {self.base_url}")
            await self.page.goto(self.base_url, timeout=10000)
            # Wait for the page to load
            await self.page.wait_for_selector("text=Interview Process Assistant", timeout=5000)
            print("Page loaded successfully")
        except Exception as e:
            print(f"Error navigating to page: {e}")
            # Take a screenshot for debugging
            screenshot_path = f"error_{self._testMethodName}.png"
            await self.page.screenshot(path=screenshot_path)
            print(f"Screenshot saved to {screenshot_path}")
            self.fail(f"Failed to load page: {e}")

    async def asyncTearDown(self):
        """Clean up asynchronously"""
        if hasattr(self, 'page') and self.page:
            await self.page.close()
        if hasattr(self, 'context') and self.context:
            await self.context.close()
        if hasattr(self, 'browser') and self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright') and self.playwright:
            await self.playwright.stop()

    def setUp(self):
        """Setup wrapper for synchronous unittest"""
        self.loop = asyncio.get_event_loop()
        self.loop.run_until_complete(self.asyncSetUp())

    def tearDown(self):
        """Teardown wrapper for synchronous unittest"""
        self.loop.run_until_complete(self.asyncTearDown())

    async def _test_home_page_loads(self):
        """Test that the home page loads with the correct title"""
        # Check that the title is present
        title = await self.page.inner_text("h1")
        self.assertEqual(title, "Interview Process Assistant")

        # Check that the subtitle is present
        subtitle = await self.page.inner_text(".header p")
        self.assertTrue("journey to interview success" in subtitle.lower())

    def test_home_page_loads(self):
        """Wrapper for home page test"""
        self.loop.run_until_complete(self._test_home_page_loads())

    async def _test_feature_cards_display(self):
        """Test that the feature cards are displayed correctly"""
        # Wait for features to load
        await self.page.wait_for_selector(".features-list")

        # Check that feature cards exist
        feature_cards = await self.page.query_selector_all(".feature-card")
        self.assertGreater(len(feature_cards), 0, "Feature cards should be displayed")

        # Check content of the first feature card
        first_feature = feature_cards[0]
        feature_title = await first_feature.query_selector("h3")
        title_text = await feature_title.inner_text()
        self.assertTrue(len(title_text) > 0, "Feature should have a title")

    def test_feature_cards_display(self):
        """Wrapper for feature cards test"""
        self.loop.run_until_complete(self._test_feature_cards_display())

    async def _test_feature_navigation(self):
        """Test that clicking on a feature card navigates to the feature page"""
        # Wait for features to load
        await self.page.wait_for_selector(".features-list")

        # Click on the first feature card
        await self.page.click(".feature-card")

        # Wait for navigation to complete
        await self.page.wait_for_selector(".feature-page")

        # Check that we're on a feature detail page
        back_button = await self.page.query_selector("text=Back to Features")
        self.assertIsNotNone(back_button, "Back button should be present on feature page")

        # Check that the feature detail content is displayed
        feature_content = await self.page.query_selector(".feature-description")
        self.assertIsNotNone(feature_content, "Feature description should be displayed")

    def test_feature_navigation(self):
        """Wrapper for feature navigation test"""
        self.loop.run_until_complete(self._test_feature_navigation())

    async def _test_back_navigation(self):
        """Test that the Back button returns to the home page"""
        # First navigate to a feature page
        await self.page.wait_for_selector(".features-list")
        await self.page.click(".feature-card")
        await self.page.wait_for_selector(".feature-page")

        # Click the Back button
        await self.page.click("text=Back to Features")

        # Check that we're back on the home page
        await self.page.wait_for_selector(".features-list")
        title = await self.page.inner_text("h1")
        self.assertEqual(title, "Interview Process Assistant")

    def test_back_navigation(self):
        """Wrapper for back navigation test"""
        self.loop.run_until_complete(self._test_back_navigation())

    async def _test_invalid_feature_id(self):
        """Test that invalid feature IDs are handled properly"""
        # Navigate directly to a non-existent feature
        await self.page.goto(f"{self.base_url}/feature/999")

        # Check for the "Feature Not Found" message
        await self.page.wait_for_selector("text=Feature Not Found")
        error_message = await self.page.inner_text("text=Feature Not Found")
        self.assertTrue("Feature Not Found" in error_message)

    def test_invalid_feature_id(self):
        """Wrapper for invalid feature ID test"""
        self.loop.run_until_complete(self._test_invalid_feature_id())


if __name__ == "__main__":
    unittest.main()