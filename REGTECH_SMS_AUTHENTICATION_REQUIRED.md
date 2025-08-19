# REGTECH SMS Authentication Required

## Current Status (2025-01-19)

### Issue Discovered
REGTECH has implemented SMS-based two-factor authentication for data downloads. When attempting to download blacklist data:

1. **Login**: Successful with username/password
2. **Session**: Cookie authentication works (`regtech-front` cookie obtained)
3. **Data Access**: Blocked by SMS verification requirement

### Authentication Flow
```
Login → Session Cookie → Navigate to Data → SMS Code Required → Download
                                              ↑
                                       [BLOCKED HERE]
```

### Technical Details
- **Endpoint**: `https://regtech.fsec.or.kr/board/excelDownload?menuCode=HPHB0620101`
- **Response**: HTML page requesting SMS verification code
- **Message**: "회원 가입 시 입력한 휴대폰 번호로 인증번호를 발송하였습니다" (Authentication code sent to registered phone)
- **Timeout**: 3 minutes to enter 6-digit code

### Previous Success (Docker Logs)
The Docker logs showed 2,252 IPs were collected previously, but this was likely:
1. Before SMS authentication was implemented, OR
2. With manual SMS code entry, OR  
3. Using a different authentication method

### Current Workaround Options

1. **Manual Collection**:
   - Login manually through browser
   - Enter SMS code when prompted
   - Download Excel file
   - Import to system using import script

2. **API Access** (if available):
   - Request API access from REGTECH
   - Use API key instead of web scraping

3. **Cached Data**:
   - Use previously collected data if available
   - Set up scheduled manual updates

### Code Status
- ✅ Login authentication working
- ✅ Cookie management implemented
- ✅ Excel parsing ready
- ❌ SMS bypass not possible (security feature)

### Recommendation
Contact REGTECH administrator to:
1. Request API access for automated collection
2. Inquire about machine-to-machine authentication options
3. Set up service account without SMS requirement

## Files Created During Investigation
- `src/core/regtech_real_collector.py` - Collector with proper Excel download path
- `test_regtech_html_parser.py` - HTML response analyzer
- `regtech_board_page.html` - Saved board page response
- `regtech_excel_response.html` - SMS authentication page

## Credentials (Working)
- Username: `nextrade`
- Password: `Sprtmxm1@3`
- Status: Login successful, but SMS verification blocks data access