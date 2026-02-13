#!/usr/bin/env python3
"""
Test script for PDF Crawler
Creates a simple HTTP server with test HTML pages and mock PDFs for demonstration.
"""

import http.server
import socketserver
import threading
import time
from pathlib import Path
import tempfile
import shutil

# HTML pages for testing
INDEX_HTML = """<!DOCTYPE html>
<html>
<head><title>Test Site - Home</title></head>
<body>
    <h1>Test Documentation Site</h1>
    <ul>
        <li><a href="/docs">Documentation</a></li>
        <li><a href="/reports">Reports</a></li>
        <li><a href="/manual.pdf">User Manual (PDF)</a></li>
    </ul>
</body>
</html>
"""

DOCS_HTML = """<!DOCTYPE html>
<html>
<head><title>Documentation</title></head>
<body>
    <h1>Documentation</h1>
    <ul>
        <li><a href="/docs/guide.pdf">User Guide (PDF)</a></li>
        <li><a href="/docs/api.pdf">API Reference (PDF)</a></li>
        <li><a href="/docs/advanced">Advanced Topics</a></li>
    </ul>
</body>
</html>
"""

REPORTS_HTML = """<!DOCTYPE html>
<html>
<head><title>Reports</title></head>
<body>
    <h1>Reports</h1>
    <ul>
        <li><a href="/reports/q1-2024.pdf">Q1 2024 Report (PDF)</a></li>
        <li><a href="/reports/q2-2024.pdf">Q2 2024 Report (PDF)</a></li>
    </ul>
</body>
</html>
"""

ADVANCED_HTML = """<!DOCTYPE html>
<html>
<head><title>Advanced Topics</title></head>
<body>
    <h1>Advanced Topics</h1>
    <p>Deep content here.</p>
    <ul>
        <li><a href="/docs/advanced/deep-dive.pdf">Deep Dive (PDF)</a></li>
    </ul>
</body>
</html>
"""

# Create mock PDF content
MOCK_PDF = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF Document) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000317 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
410
%%EOF
"""


class TestHTTPHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler for test server."""
    
    def do_GET(self):
        """Handle GET requests."""
        # Route handling
        routes = {
            '/': INDEX_HTML,
            '/docs': DOCS_HTML,
            '/reports': REPORTS_HTML,
            '/docs/advanced': ADVANCED_HTML,
        }
        
        pdf_routes = [
            '/manual.pdf',
            '/docs/guide.pdf',
            '/docs/api.pdf',
            '/reports/q1-2024.pdf',
            '/reports/q2-2024.pdf',
            '/docs/advanced/deep-dive.pdf',
        ]
        
        if self.path in routes:
            # Serve HTML
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(routes[self.path].encode())
        
        elif self.path in pdf_routes:
            # Serve PDF
            self.send_response(200)
            self.send_header('Content-Type', 'application/pdf')
            self.send_header('Content-Length', str(len(MOCK_PDF)))
            self.end_headers()
            self.wfile.write(MOCK_PDF)
        
        else:
            # 404
            self.send_response(404)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<html><body><h1>404 Not Found</h1></body></html>')
    
    def log_message(self, format, *args):
        """Suppress request logging."""
        pass


def run_test_server(port=8000):
    """Run the test HTTP server."""
    handler = TestHTTPHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"Test server running on http://localhost:{port}")
        print("Available test pages:")
        print(f"  http://localhost:{port}/")
        print(f"  http://localhost:{port}/docs")
        print(f"  http://localhost:{port}/reports")
        print(f"\nTest PDFs available:")
        print(f"  http://localhost:{port}/manual.pdf")
        print(f"  http://localhost:{port}/docs/guide.pdf")
        print(f"  http://localhost:{port}/docs/api.pdf")
        print(f"  http://localhost:{port}/reports/q1-2024.pdf")
        print(f"  http://localhost:{port}/reports/q2-2024.pdf")
        print(f"  http://localhost:{port}/docs/advanced/deep-dive.pdf (depth 3)")
        print("\nPress Ctrl+C to stop the server\n")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")


def run_crawler_test():
    """Run the PDF crawler against the test server."""
    import subprocess
    import os
    
    # Create temporary output directory
    output_dir = tempfile.mkdtemp(prefix='pdf_crawler_test_')
    
    print("=" * 70)
    print("PDF CRAWLER TEST")
    print("=" * 70)
    
    # Start test server in background thread
    port = 8000
    server_thread = threading.Thread(target=run_test_server, args=(port,), daemon=True)
    server_thread.start()
    
    # Wait for server to start
    time.sleep(2)
    
    print(f"\nRunning crawler with output directory: {output_dir}\n")
    
    # Run crawler
    try:
        result = subprocess.run([
            'python3', 'pdf_crawler.py',
            f'http://localhost:{port}',
            '-o', output_dir,
            '-d', '3',  # Depth 3 to catch the deep-dive.pdf
        ], capture_output=False, text=True)
        
        print("\n" + "=" * 70)
        print("TEST RESULTS")
        print("=" * 70)
        
        # Show downloaded files
        output_path = Path(output_dir)
        pdf_files = list(output_path.glob('*.pdf'))
        
        print(f"\nDownloaded PDFs ({len(pdf_files)}):")
        for pdf_file in pdf_files:
            size = pdf_file.stat().st_size
            print(f"  - {pdf_file.name} ({size} bytes)")
        
        # Show manifest
        manifest_file = output_path / 'manifest.json'
        if manifest_file.exists():
            print(f"\nManifest file created: {manifest_file}")
            import json
            with open(manifest_file) as f:
                manifest = json.load(f)
            print(f"\nManifest statistics:")
            for key, value in manifest['statistics'].items():
                print(f"  {key}: {value}")
        
        print(f"\nAll files saved to: {output_dir}")
        print("\nTo clean up test files, run:")
        print(f"  rm -rf {output_dir}")
        
    except Exception as e:
        print(f"Error running test: {e}")
    finally:
        # Cleanup note
        print("\n" + "=" * 70)


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'server':
        # Run only the test server
        run_test_server()
    else:
        # Run full test
        run_crawler_test()