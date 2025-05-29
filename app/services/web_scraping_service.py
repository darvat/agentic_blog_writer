from __future__ import annotations
import re
from typing import Dict, Set, List

from crawl4ai import AsyncWebCrawler, CrawlResult, CrawlerRunConfig, BrowserConfig
from app.models.article_schemas import ResearchNotes


class WebScrapingService:
    """
    Handles web scraping operations for research notes.
    """

    async def extract_and_scrape_urls(self, research_notes: ResearchNotes | None) -> ResearchNotes | None:
        """
        Extract URLs from research notes and scrape their content.
        Returns updated research notes with scraped content.
        """
        if not research_notes:
            return None

        # Extract all unique URLs from research notes
        urls_to_scrape = self._extract_urls_from_research(research_notes)
        
        if not urls_to_scrape:
            return research_notes

        # Create a deep copy to avoid modifying the original
        notes_to_augment = research_notes.model_copy(deep=True)
        
        # Scrape content and create a mapping
        scraped_content_map = await self._scrape_urls(list(urls_to_scrape))
        
        # Update research notes with scraped content
        self._update_notes_with_scraped_content(notes_to_augment, scraped_content_map)
        
        return notes_to_augment

    def _extract_urls_from_research(self, research_notes: ResearchNotes) -> Set[str]:
        """Extract unique URLs from research notes"""
        urls_to_scrape = set()
        
        if research_notes.notes_by_section:
            for section_note in research_notes.notes_by_section:
                for finding in section_note.findings:
                    if finding.source_url:
                        urls_to_scrape.add(finding.source_url)
        
        print(f"🎯 Total unique URLs found: {len(urls_to_scrape)}")
        return urls_to_scrape

    def _filter_scrapable_urls(self, urls: List[str]) -> List[str]:
        """
        Filter URLs to only include those that can be scraped as web pages.
        Excludes PDFs and other file types that require special handling.
        """
        scrapable_urls = []
        excluded_urls = []
        
        for url in urls:
            url_lower = url.lower()
            # Skip PDF files and other document types
            if (url_lower.endswith('.pdf') or 
                url_lower.endswith('.doc') or 
                url_lower.endswith('.docx') or 
                url_lower.endswith('.xls') or 
                url_lower.endswith('.xlsx') or 
                url_lower.endswith('.ppt') or 
                url_lower.endswith('.pptx') or
                '.pdf' in url_lower.split('?')[0]):  # Handle URLs with PDF in path
                excluded_urls.append(url)
            else:
                scrapable_urls.append(url)
        
        if excluded_urls:
            print(f"📄 Excluded {len(excluded_urls)} document URLs (PDF, Office docs):")
            for url in excluded_urls:
                print(f"  ❌ {url}")
        
        return scrapable_urls

    async def _scrape_urls(self, urls: List[str]) -> Dict[str, str]:
        """
        Scrape content from a list of URLs and return a mapping of URL to cleaned content.
        """
        scraped_content_map = {}
        
        print(f"🔍 Starting to scrape {len(urls)} URLs:")
        for i, url in enumerate(urls, 1):
            print(f"  {i}. {url}")
        
        # Filter out URLs that can't be scraped as web pages
        
        print(f"----- Filtering scrapable URLs -----")
        
        scrapable_urls = self._filter_scrapable_urls(urls)
        
        print(f"----- Scrapable URLs -----")
        
        if not scrapable_urls:
            print("⚠️ No scrapable URLs found after filtering")
            return scraped_content_map
        
        print(f"🌐 Proceeding with {len(scrapable_urls)} scrapable URLs")
        
        # Separate browser config from crawler config
        browser_config = BrowserConfig(
            headless=True,
            verbose=False,  # Reduce verbosity to avoid spam
        )
        
        crawler_config = CrawlerRunConfig(
            exclude_external_images=True,
            exclude_external_links=True,
            verbose=False,  # Reduce verbosity to avoid spam
            page_timeout=30000,  # 30 second timeout per page
        )
        
        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                print(f"🌐 Starting crawl operation...")
                crawl_results: List[CrawlResult] = await crawler.arun_many(
                    urls=scrapable_urls, 
                    config=crawler_config
                )
                
                print(f"📊 Received {len(crawl_results)} results")
            
            for i, result in enumerate(crawl_results):
                print(f"📄 Result {i+1}: {result.url}")
                print(f"  ✅ Success: {result.success}")
                
                if result.success:
                    if result.markdown:
                        content = (
                            result.markdown.fit_markdown 
                            if result.markdown.fit_markdown 
                            else result.markdown.raw_markdown
                        )
                        
                        if content and len(content.strip()) > 100:  # Ensure meaningful content
                            cleaned_content = self._clean_scraped_content(content)
                            scraped_content_map[result.url] = cleaned_content
                            print(f"  📝 Content length: {len(cleaned_content)} chars")
                        else:
                            print(f"  ⚠️ Content too short or empty")
                    else:
                        print(f"  ⚠️ No markdown in result")
                else:
                    print(f"  ❌ Error: {result.error_message}")
                    print(f"  📊 Status code: {result.status_code}")
                        
        except Exception as e:
            # Log error but don't fail - return what we have
            print(f"💥 Error during scraping: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"🎯 Successfully scraped {len(scraped_content_map)}/{len(urls)} URLs")
        print(f"   ({len(scraped_content_map)}/{len(scrapable_urls)} scrapable URLs)")
        return scraped_content_map

    def _clean_scraped_content(self, content: str) -> str:
        """
        Clean scraped content by removing images, links, and formatting artifacts.
        """
        # Remove markdown image links: ![alt text](url)
        content = re.sub(r"!\[.*?\]\(.*?\)", "", content)
        
        # Remove HTML img tags: <img src="..." alt="...">
        content = re.sub(r"<img .*?>", "", content)
        
        # Remove HTTP links within parentheses: (http*) -> ()
        content = re.sub(r"\(http[^)]*\)", "()", content)
        
        # Remove empty markdown links: [   ]()
        content = re.sub(r"\[\s*\]\(\)", "", content)
        
        # Replace multiple newlines with single newline
        content = re.sub(r"\n{2,}", "\n", content)
        
        return content.strip()

    def _update_notes_with_scraped_content(
        self, 
        notes: ResearchNotes, 
        scraped_content_map: Dict[str, str]
    ) -> None:
        """
        Update research notes with scraped content from the content map.
        """
        if notes.notes_by_section:
            for section_note in notes.notes_by_section:
                for finding in section_note.findings:
                    if finding.source_url and finding.source_url in scraped_content_map:
                        finding.scraped_content = scraped_content_map[finding.source_url]

    def get_scraping_stats(self, research_notes: ResearchNotes) -> tuple[int, int, float]:
        """
        Calculate scraping statistics.
        Returns: (total_urls, scraped_urls, success_rate)
        """
        total_urls = 0
        scraped_urls = 0
        
        if research_notes.notes_by_section:
            for section_note in research_notes.notes_by_section:
                section_total = len(section_note.findings)
                section_scraped = sum(
                    1 for finding in section_note.findings 
                    if finding.scraped_content
                )
                total_urls += section_total
                scraped_urls += section_scraped
        
        success_rate = (scraped_urls / total_urls * 100) if total_urls > 0 else 0
        return total_urls, scraped_urls, success_rate 