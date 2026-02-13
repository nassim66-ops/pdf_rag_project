#!/usr/bin/env python3
"""
PDF Crawler CLI Tool (Selenium Version)
Crawls HTML pages, discovers PDF links, and downloads them with validation.
Uses Selenium WebDriver to bypass bot detection.

"""

import argparse
import json
import hashlib
import logging
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Set, Dict, List, Optional
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import WebDriverException, TimeoutException

class SeleniumPDFCrawler:
    """Crawls websites using Selenium and downloads PDF files."""

    PDF_MAGIC_BYTES = b'%PDF'

    def __init__(
        self,
        start_url: str,
        output_dir: str,
        max_depth: int = 2,
        allowed_domains: Optional[List[str]] = None,
        timeout: int = 30,
        delay: float = 0.5,
        headless: bool = False
    ):
        self.start_url = start_url
        self.output_dir = Path(output_dir)
        self.max_depth = max_depth
        self.timeout = timeout
        self.delay = delay
        self.headless = headless

        # Set allowed domains (default to start URL domain)
        parsed_start = urlparse(start_url)
        self.allowed_domains = allowed_domains or [parsed_start.netloc]

        # Tracking sets
        self.visited_pages: Set[str] = set()
        self.discovered_pdfs: Set[str] = set()
        self.downloaded_pdfs: Set[str] = set()
        self.failed_downloads: List[Dict] = []

        # Download manifest
        self.manifest: List[Dict] = []

        # Setup output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Setup Selenium driver
        self.driver = None

        # Setup logging
        self._setup_logging()

    def _setup_logging(self):
        """Configure logging."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.output_dir / 'crawler.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def _setup_driver(self):
        """Setup Chrome driver with anti-detection options."""
        options = Options()

        options.page_load_strategy = "eager"  # <<< FIX: prevent timeout on heavy JS pages

        if self.headless:
            options.add_argument("--headless=new")

        prefs = {
            "download.default_directory": str(self.output_dir.resolve()),
            "download.prompt_for_download": False,
            "plugins.always_open_pdf_externally": True,
        }

        options.add_experimental_option("prefs", prefs)
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        try:
            self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
            self.driver.set_page_load_timeout(15)  # <<< shorter timeout
        except Exception as e:
            self.logger.error(f"Failed to initialize Chrome driver: {e}")
            self.logger.error("Make sure Chrome and ChromeDriver are installed")
            raise

    def normalize_url(self, url: str) -> str:
        """Normalize URL by removing fragments and ensuring consistency."""
        parsed = urlparse(url)
        normalized = urlunparse(parsed._replace(fragment=''))
        return normalized

    def is_allowed_url(self, url: str) -> bool:
        """Check if URL is within allowed domains."""
        parsed = urlparse(url)
        return any(parsed.netloc == domain or parsed.netloc.endswith('.' + domain)
                   for domain in self.allowed_domains)

    def is_pdf_url(self, url: str) -> bool:
        """Quick check if URL likely points to a PDF."""
        parsed = urlparse(url)
        return parsed.path.lower().endswith('.pdf')

    def validate_pdf_content(self, content: bytes) -> bool:
        """Validate that content is actually a PDF using magic bytes."""
        return content.startswith(self.PDF_MAGIC_BYTES)

    def generate_filename(self, url: str) -> str:
        """Generate a safe filename for the PDF."""
        parsed = urlparse(url)
        path = parsed.path

        if path.endswith('.pdf'):
            filename = os.path.basename(path)
        else:
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            filename = f"document_{url_hash}.pdf"

        filename = "".join(c for c in filename if c.isalnum() or c in '._-')

        base_path = self.output_dir / filename
        counter = 1
        while base_path.exists():
            name, ext = os.path.splitext(filename)
            base_path = self.output_dir / f"{name}_{counter}{ext}"
            counter += 1

        return base_path.name

    # def download_pdf(self, url: str) -> Optional[Dict]:
    #     """Download a PDF and return manifest entry."""
    #     self.logger.info(f"Downloading PDF: {url}")
    #     if self.delay > 0:
    #         time.sleep(self.delay)

    #     try:
    #         cookies = {c['name']: c['value'] for c in self.driver.get_cookies()}
    #         headers = {
    #             "User-Agent": self.driver.execute_script("return navigator.userAgent;"),
    #             "Referer": self.start_url
    #         }

    #         response = requests.get(
    #             url,
    #             headers=headers,
    #             cookies=cookies,
    #             timeout=self.timeout
    #         )
    #         response.raise_for_status()

    #         content = response.content
    #         content_type = response.headers.get('Content-Type', '').lower()
    #         is_pdf_content_type = 'application/pdf' in content_type
    #         is_valid_pdf = self.validate_pdf_content(content)

    #         if not is_valid_pdf:
    #             error_msg = "Invalid PDF content (magic bytes check failed)"
    #             self.logger.warning(f"{url}: {error_msg}")
    #             self.failed_downloads.append({'url': url, 'reason': error_msg})
    #             return None

    #         filename = self.generate_filename(url)
    #         local_path = self.output_dir / filename
    #         with open(local_path, 'wb') as f:
    #             f.write(content)

    #         sha256_hash = hashlib.sha256(content).hexdigest()
    #         self.downloaded_pdfs.add(url)

    #         manifest_entry = {
    #             'source_url': url,
    #             'local_path': str(local_path.relative_to(self.output_dir)),
    #             'downloaded_at': datetime.now(timezone.utc).isoformat(),
    #             'http_status': response.status_code,
    #             'content_length': len(content),
    #             'sha256': sha256_hash,
    #             'content_type': content_type,
    #             'validated': is_valid_pdf and is_pdf_content_type
    #         }

    #         self.logger.info(f"Successfully downloaded: {filename} ({len(content)} bytes)")
    #         return manifest_entry

    #     except requests.exceptions.RequestException as e:
    #         error_msg = f"Download failed: {str(e)}"
    #         self.logger.error(f"{url}: {error_msg}")
    #         self.failed_downloads.append({'url': url, 'reason': error_msg})
    #         return None
    #     except Exception as e:
    #         error_msg = f"Unexpected error: {str(e)}"
    #         self.logger.error(f"{url}: {error_msg}")
    #         self.failed_downloads.append({'url': url, 'reason': error_msg})
    #         return None

    # def download_pdf(self, url: str) -> Optional[Dict]:
    #     self.logger.info(f"Downloading PDF (via browser): {url}")

    #     try:
    #         before = set(os.listdir(self.output_dir))

    #         self.driver.get(url)

    #         # wait for download
    #         timeout = time.time() + 20
    #         while time.time() < timeout:
    #             after = set(os.listdir(self.output_dir))
    #             diff = after - before
    #             if diff:
    #                 filename = diff.pop()
    #                 filepath = self.output_dir / filename

    #                 # wait until file finished
    #                 while filepath.suffix == ".crdownload":
    #                     time.sleep(0.5)

    #                 with open(filepath, "rb") as f:
    #                     content = f.read()

    #                 if not self.validate_pdf_content(content):
    #                     self.failed_downloads.append({
    #                         "url": url,
    #                         "reason": "Not valid PDF"
    #                     })
    #                     return None

    #                 sha = hashlib.sha256(content).hexdigest()

    #                 self.downloaded_pdfs.add(url)

    #                 return {
    #                     "source_url": url,
    #                     "local_path": filename,
    #                     "downloaded_at": datetime.now(timezone.utc).isoformat(),
    #                     "content_length": len(content),
    #                     "sha256": sha,
    #                     "validated": True
    #                 }

    #             time.sleep(0.5)

    #         self.failed_downloads.append({
    #             "url": url,
    #             "reason": "Download timeout"
    #         })
    #         return None

    #     except Exception as e:
    #         self.failed_downloads.append({
    #             "url": url,
    #             "reason": str(e)
    #         })
    #         return None
    def download_pdf(self, url: str) -> Optional[Dict]:
        self.logger.info(f"Downloading PDF (via browser): {url}")
        try:
            before = set(os.listdir(self.output_dir))
            self.driver.get(url)

            # max wait per file
            total_wait = 30
            elapsed = 0
            filename = None

            while elapsed < total_wait:
                after = set(os.listdir(self.output_dir))
                diff = after - before
                if diff:
                    filename = diff.pop()
                    filepath = self.output_dir / filename

                    # wait until file finishes downloading
                    file_wait = 0
                    while filepath.suffix == ".crdownload" and file_wait < 30:
                        time.sleep(0.5)
                        file_wait += 0.5

                    # final check
                    if not filepath.exists():
                        self.logger.warning(f"{url}: file missing after download")
                        return None

                    with open(filepath, "rb") as f:
                        content = f.read()

                    if not self.validate_pdf_content(content):
                        self.failed_downloads.append({
                            "url": url,
                            "reason": "Not valid PDF"
                        })
                        return None

                    sha = hashlib.sha256(content).hexdigest()
                    self.downloaded_pdfs.add(url)

                    return {
                        "source_url": url,
                        "local_path": filename,
                        "downloaded_at": datetime.now(timezone.utc).isoformat(),
                        "content_length": len(content),
                        "sha256": sha,
                        "validated": True
                    }

                time.sleep(0.5)
                elapsed += 0.5

            self.failed_downloads.append({
                "url": url,
                "reason": "Download timeout"
            })
            return None

        except Exception as e:
            self.failed_downloads.append({
                "url": url,
                "reason": str(e)
            })
            return None


    def wait_for_all_downloads(self, timeout=120):
        """Wait until there are no .crdownload files in the output directory."""
        start = time.time()
        while time.time() - start < timeout:
            cr_files = list(self.output_dir.glob("*.crdownload"))
            if not cr_files:
                return True
            time.sleep(1)
        return False


    def extract_links(self, url: str) -> tuple[Set[str], Set[str]]:
        """Extract links using Selenium (bypasses bot detection)."""
        page_links = set()
        pdf_links = set()

        try:
            try:
                self.driver.get(url)
            except TimeoutException:
                self.logger.warning(f"Timeout loading {url}")
                return page_links, pdf_links

            time.sleep(2)
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')

            for tag in soup.find_all('a', href=True):
                href = tag['href']
                absolute_url = urljoin(url, href)
                normalized_url = self.normalize_url(absolute_url)

                if not self.is_allowed_url(normalized_url):
                    continue

                if self.is_pdf_url(normalized_url):
                    pdf_links.add(normalized_url)
                else:
                    parsed = urlparse(normalized_url)
                    if not parsed.path or parsed.path == '/' or \
                       parsed.path.endswith(('.html', '.htm', '')) or \
                       '.' not in os.path.basename(parsed.path):
                        page_links.add(normalized_url)

        except Exception as e:
            self.logger.error(f"Failed to extract links from {url}: {e}")

        return page_links, pdf_links

    def crawl(self, url: str, depth: int = 0):
        """Crawl a single HTML page and discover links."""
        if depth > self.max_depth or url in self.visited_pages:
            return

        self.visited_pages.add(url)
        self.logger.info(f"Crawling (depth {depth}): {url}")
        if self.delay > 0 and len(self.visited_pages) > 1:
            time.sleep(self.delay)

        try:
            pages, pdfs = self.extract_links(url)
            new_pdfs = pdfs - self.discovered_pdfs
            self.discovered_pdfs.update(new_pdfs)
            self.logger.info(f"Found {len(new_pdfs)} new PDF(s) on {url}")

            if depth < self.max_depth:
                for p in pages:
                    if p not in self.visited_pages:
                        self.crawl(p, depth + 1)
        except Exception as e:
            self.logger.error(f"Unexpected error crawling {url}: {e}")

    def run(self):
        """Execute the crawling and downloading process."""
        self.logger.info("=" * 60)
        self.logger.info("Starting PDF Crawler (Selenium)")
        self.logger.info(f"Start URL: {self.start_url}")
        self.logger.info(f"Max Depth: {self.max_depth}")
        self.logger.info(f"Allowed Domains: {', '.join(self.allowed_domains)}")
        self.logger.info(f"Output Directory: {self.output_dir}")
        self.logger.info(f"Headless Mode: {self.headless}")
        self.logger.info("=" * 60)

        self.logger.info("Initializing browser...")
        self._setup_driver()

        try:
            self.logger.info("\n[Phase 1] Crawling pages...")
            self.crawl(self.start_url)

            self.logger.info(f"\n[Phase 2] Downloading {len(self.discovered_pdfs)} PDF(s)...")
            for pdf_url in self.discovered_pdfs:
                if pdf_url not in self.downloaded_pdfs:
                    manifest_entry = self.download_pdf(pdf_url)
                    if manifest_entry:
                        self.manifest.append(manifest_entry)
            
            # NEW: Wait for any incomplete downloads to finish
            self.logger.info("Waiting for all downloads to complete...")
            if self.wait_for_all_downloads(timeout=120):  # e.g., 2 minutes max
                self.logger.info("All downloads completed")
            else:
                self.logger.warning("Some downloads did not complete in time")

            self.logger.info("\n[Phase 3] Writing manifest...")
            self.write_manifest()

            self.print_summary()

        finally:
            if self.driver:
                self.driver.quit()

    def write_manifest(self):
        """Write the manifest file."""
        manifest_path = self.output_dir / 'manifest.json'

        manifest_data = {
            'crawl_metadata': {
                'start_url': self.start_url,
                'crawled_at': datetime.now(timezone.utc).isoformat(),
                'max_depth': self.max_depth,
                'allowed_domains': self.allowed_domains,
                'crawler_type': 'selenium'
            },
            'statistics': {
                'pages_visited': len(self.visited_pages),
                'pdfs_discovered': len(self.discovered_pdfs),
                'pdfs_downloaded': len(self.downloaded_pdfs),
                'failures': len(self.failed_downloads)
            },
            'downloads': self.manifest,
            'failures': self.failed_downloads
        }

        with open(manifest_path, 'w') as f:
            json.dump(manifest_data, f, indent=2)

        self.logger.info(f"Manifest written to: {manifest_path}")

    def print_summary(self):
        """Print end-of-run summary."""
        print("\n" + "=" * 60)
        print("CRAWL SUMMARY")
        print("=" * 60)
        print(f"Pages visited:     {len(self.visited_pages)}")
        print(f"PDFs found:        {len(self.discovered_pdfs)}")
        print(f"PDFs downloaded:   {len(self.downloaded_pdfs)}")
        print(f"Failures:          {len(self.failed_downloads)}")

        if self.failed_downloads:
            print("\nFailure Details:")
            failure_reasons = defaultdict(int)
            for failure in self.failed_downloads:
                reason = failure['reason'].split(':')[0]
                failure_reasons[reason] += 1

            for reason, count in failure_reasons.items():
                print(f"  - {reason}: {count}")

        print(f"\nOutput directory:  {self.output_dir}")
        print(f"Manifest file:     {self.output_dir / 'manifest.json'}")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description='Crawl HTML pages and download PDFs (Selenium version for bot-protected sites)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s https://example.com/docs -o ./pdfs
  %(prog)s https://example.com -o ./output -d 3 --headless
  %(prog)s https://example.com --domains example.com,docs.example.com
Note: Requires Chrome browser and ChromeDriver to be installed.
Install: pip install selenium
        """
    )

    parser.add_argument('start_url', metavar='START_URL', help='Starting URL for crawling')
    parser.add_argument('-o', '--output', metavar='DIR', default='./pdf_downloads', help='Output directory for PDFs')
    parser.add_argument('-d', '--max-depth', type=int, default=2, metavar='N', help='Maximum crawl depth')
    parser.add_argument('--domains', metavar='DOMAIN[,DOMAIN...]', help='Comma-separated list of allowed domains')
    parser.add_argument('--timeout', type=int, default=30, metavar='SEC', help='Request timeout in seconds')
    parser.add_argument('--delay', type=float, default=0.5, metavar='SEC', help='Delay between requests in seconds')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')

    args = parser.parse_args()

    allowed_domains = None
    if args.domains:
        allowed_domains = [d.strip() for d in args.domains.split(',')]

    try:
        crawler = SeleniumPDFCrawler(
            start_url=args.start_url,
            output_dir=args.output,
            max_depth=args.max_depth,
            allowed_domains=allowed_domains,
            timeout=args.timeout,
            delay=args.delay,
            headless=args.headless
        )
        crawler.run()
    except KeyboardInterrupt:
        print("\n\nCrawl interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nFatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
