#!/usr/bin/env python3
"""
Manual REGTECH Excel Import Script
Use this after manually downloading Excel file from REGTECH with SMS authentication
"""

import sys
import os
import pandas as pd
import psycopg2
from datetime import datetime
from pathlib import Path
from loguru import logger

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from src.core.data_storage_fixed import FixedDataStorage


def import_regtech_excel(excel_path: str):
    """
    Import REGTECH Excel file to PostgreSQL database
    
    Args:
        excel_path: Path to the downloaded Excel file
    """
    if not os.path.exists(excel_path):
        logger.error(f"File not found: {excel_path}")
        return False
    
    logger.info(f"Reading Excel file: {excel_path}")
    
    try:
        # Read Excel file
        df = pd.read_excel(excel_path, engine='openpyxl')
        logger.info(f"Excel shape: {df.shape}")
        logger.info(f"Columns: {df.columns.tolist()}")
        
        # Find IP column
        ip_columns = ['IP', 'ip', 'IP주소', 'IP Address', '악성IP', 'IP_ADDRESS', 
                     '악성 IP', 'Malicious IP', '차단IP', '차단 IP']
        ip_col = None
        
        for col in ip_columns:
            if col in df.columns:
                ip_col = col
                break
        
        if not ip_col:
            # Try to find column with IP-like data
            for col in df.columns:
                sample = df[col].dropna().head(5).astype(str)
                if any('.' in str(val) and len(str(val).split('.')) == 4 for val in sample):
                    ip_col = col
                    break
        
        if not ip_col:
            logger.error("Could not find IP column in Excel file")
            logger.info("Available columns: " + ", ".join(df.columns))
            return False
        
        logger.info(f"Using IP column: {ip_col}")
        
        # Extract IPs
        collected_ips = []
        for idx, row in df.iterrows():
            ip = str(row.get(ip_col, '')).strip()
            if ip and '.' in ip and ip != 'nan':
                # Clean IP (remove /32 if present)
                if '/' in ip:
                    ip = ip.split('/')[0]
                
                # Get description from various possible columns
                desc_columns = ['설명', 'Description', '비고', 'Remark', '내용', 'Content', 
                               '상세', 'Detail', '탐지사유', 'Reason']
                description = None
                for desc_col in desc_columns:
                    if desc_col in df.columns:
                        desc = row.get(desc_col)
                        if pd.notna(desc) and str(desc).strip():
                            description = str(desc).strip()
                            break
                
                if not description:
                    description = "Malicious IP from REGTECH"
                
                # Get date if available
                date_columns = ['탐지일', 'Detection Date', '등록일', 'Registration Date', 
                               '날짜', 'Date', '일자']
                detection_date = None
                for date_col in date_columns:
                    if date_col in df.columns:
                        date_val = row.get(date_col)
                        if pd.notna(date_val):
                            try:
                                if isinstance(date_val, pd.Timestamp):
                                    detection_date = date_val.strftime('%Y-%m-%d')
                                else:
                                    detection_date = str(date_val)[:10]
                                break
                            except:
                                pass
                
                if not detection_date:
                    detection_date = datetime.now().strftime('%Y-%m-%d')
                
                ip_data = {
                    "ip": ip,
                    "source": "REGTECH",
                    "description": description,
                    "detection_date": detection_date,
                    "confidence": "high"
                }
                collected_ips.append(ip_data)
        
        logger.info(f"Extracted {len(collected_ips)} IPs from Excel")
        
        if not collected_ips:
            logger.warning("No IPs found in Excel file")
            return False
        
        # Show sample
        logger.info("Sample IPs (first 5):")
        for i, ip_data in enumerate(collected_ips[:5], 1):
            logger.info(f"  {i}. {ip_data['ip']} - {ip_data['description'][:50]}")
        
        # Store in database
        logger.info("Storing IPs in PostgreSQL database...")
        storage = FixedDataStorage()
        
        # Clear existing REGTECH data if requested
        if '--clear' in sys.argv:
            logger.info("Clearing existing REGTECH data...")
            storage.clear_source_data("REGTECH")
        
        result = storage.store_ips(collected_ips, "REGTECH")
        
        if result.get("success"):
            logger.info(f"✅ Successfully imported {result.get('imported_count', 0)} IPs")
            logger.info(f"   Duplicates skipped: {result.get('duplicate_count', 0)}")
            
            # Get total count
            total = storage.get_stored_ips_count()
            logger.info(f"   Total IPs in database: {total}")
            return True
        else:
            logger.error(f"❌ Import failed: {result.get('error')}")
            return False
            
    except Exception as e:
        logger.error(f"Error importing Excel: {e}")
        return False


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python import_regtech_excel.py <path_to_excel_file> [--clear]")
        print("\nOptions:")
        print("  --clear  Clear existing REGTECH data before import")
        print("\nExample:")
        print("  python import_regtech_excel.py ~/Downloads/regtech_blacklist.xlsx")
        print("  python import_regtech_excel.py ~/Downloads/regtech_blacklist.xlsx --clear")
        sys.exit(1)
    
    excel_path = sys.argv[1]
    success = import_regtech_excel(excel_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()