#!/usr/bin/env python3
"""
Parse HTML response from REGTECH to extract IP data
"""

import os
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


def test_regtech_html_parsing():
    """Test parsing HTML response from REGTECH"""
    
    username = os.getenv('REGTECH_USERNAME', '')
    password = os.getenv('REGTECH_PASSWORD', '')
    base_url = "https://regtech.fsec.or.kr"
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
    })
    
    # Login
    logger.info(f"Logging in as {username}...")
    login_resp = session.post(
        f"{base_url}/login/loginProcess",
        data={'loginId': username, 'loginPw': password}
    )
    
    if 'regtech-front' not in session.cookies:
        logger.error("Login failed - no cookie")
        return
        
    logger.info("Login successful")
    
    # Try the board list page first to see the data
    board_url = f"{base_url}/board/boardList"
    board_params = {'menuCode': 'HPHB0620101'}
    
    logger.info("Fetching board list page...")
    board_resp = session.get(board_url, params=board_params)
    
    if board_resp.status_code == 200:
        # Parse HTML
        soup = BeautifulSoup(board_resp.text, 'html.parser')
        
        # Save HTML for inspection
        with open('regtech_board_page.html', 'w', encoding='utf-8') as f:
            f.write(board_resp.text)
        logger.info("Saved HTML to regtech_board_page.html")
        
        # Look for tables
        tables = soup.find_all('table')
        logger.info(f"Found {len(tables)} tables")
        
        # Look for IP patterns in the page
        ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
        all_ips = ip_pattern.findall(board_resp.text)
        logger.info(f"Found {len(all_ips)} IP addresses in page")
        
        if all_ips:
            logger.info("First 10 IPs found:")
            for ip in all_ips[:10]:
                print(f"  - {ip}")
        
        # Look for data in tables
        for i, table in enumerate(tables):
            rows = table.find_all('tr')
            logger.info(f"Table {i+1} has {len(rows)} rows")
            
            # Check first few rows
            for j, row in enumerate(rows[:3]):
                cells = row.find_all(['td', 'th'])
                if cells:
                    row_text = ' | '.join(cell.get_text(strip=True) for cell in cells[:5])
                    logger.info(f"  Row {j+1}: {row_text}")
        
        # Check for pagination or data count
        page_info = soup.find_all(text=re.compile(r'\d+건'))
        if page_info:
            logger.info(f"Page info: {page_info}")
        
        # Look for download button or link
        download_links = soup.find_all('a', href=re.compile(r'download|excel', re.I))
        logger.info(f"Found {len(download_links)} download links")
        for link in download_links:
            logger.info(f"  Link: {link.get('href')} - {link.get_text(strip=True)}")
            
        # Look for JavaScript that might load data
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and ('boardList' in script.string or 'ipPool' in script.string):
                logger.info("Found relevant JavaScript - data might be loaded dynamically")
                
    # Now try the Excel download with different approach
    logger.info("\nTrying Excel download endpoint...")
    excel_url = f"{base_url}/board/excelDownload"
    excel_params = {'menuCode': 'HPHB0620101'}
    
    excel_resp = session.get(excel_url, params=excel_params)
    logger.info(f"Excel response status: {excel_resp.status_code}")
    logger.info(f"Excel response size: {len(excel_resp.content)} bytes")
    
    # Check if it's HTML
    if excel_resp.headers.get('Content-Type', '').startswith('text/html'):
        logger.info("Excel endpoint returned HTML")
        soup = BeautifulSoup(excel_resp.text, 'html.parser')
        
        # Save for inspection
        with open('regtech_excel_response.html', 'w', encoding='utf-8') as f:
            f.write(excel_resp.text)
        logger.info("Saved to regtech_excel_response.html")
        
        # Check for error messages
        errors = soup.find_all(class_=re.compile('error|alert|message', re.I))
        if errors:
            logger.warning("Found error messages:")
            for err in errors:
                logger.warning(f"  {err.get_text(strip=True)}")


if __name__ == "__main__":
    test_regtech_html_parsing()