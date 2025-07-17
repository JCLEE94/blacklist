<#
.SYNOPSIS
  모든 페이지를 자동으로 순회하여 지정된 기간의 전체 데이터를 가져오고, 모든 실행 과정을 로그 파일로 남깁니다.
#>

# 1. 로그 파일 경로 설정 및 기록 시작
$logPath = "C:\temp" # 로그를 저장할 폴더 경로
if (-not (Test-Path -Path $logPath)) { New-Item -ItemType Directory -Path $logPath }
$logFile = Join-Path -Path $logPath -ChildPath "collection_log_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
Start-Transcript -Path $logFile

# [수정] TLS 1.2 프로토콜을 호환성을 위해 숫자 값으로 직접 설정
[Net.ServicePointManager]::SecurityProtocol = 3072 

try {
    # 2. WebRequestSession 객체 생성 및 설정
    $session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    $session.UserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"

    # 세션에 쿠키 추가 (만료되지 않은 새 쿠키로 교체해야 합니다)
    $uriObject = New-Object System.Uri("https://regtech.fsec.or.kr")
    $session.Cookies.Add($uriObject, (New-Object System.Net.Cookie("_ga", "GA1.1.1689204774.1752555033")))
    $session.Cookies.Add($uriObject, (New-Object System.Net.Cookie("regtech-front", "2F3B7CE1B26084FCD546BDB56CE9ABAC")))
    $session.Cookies.Add($uriObject, (New-Object System.Net.Cookie("regtech-va", "BearereyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJuZXh0cmFkZSIsIm9yZ2FubmFtZSI6IuuEpeyKpO2KuOugiOydtOuTnCIsImlkIjoibmV4dHJhZGUiLCJleHAiOjE3NTI4Mjk2NDUsInVzZXJuYW1lIjoi7J6l7ZmN7KSAIn0.ha36VHXTf1AnziAChasI68mh9nrDawyrKRXyXKV6liPCOA1MFnoR5kTg3pSw3RNM_zkDD2NnfX5PcbdzwPET1w")))
    $session.Cookies.Add($uriObject, (New-Object System.Net.Cookie("_ga_7WRDYHF66J", 'GS2.1.s1752743223$o3$g1$t1752746099$j38$l0$h0')))

    # 3. 요청 파라미터 설정
    $uri = "https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList"
    $headers = @{ "Referer" = "https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList" }
    
    $startDate = (Get-Date).AddMonths(-3).ToString('yyyyMMdd')
    $endDate = (Get-Date).ToString('yyyyMMdd')

    $allResults = @()
    $page = 0

    Write-Host "데이터 조회를 시작합니다 (기간: $startDate ~ $endDate)" -ForegroundColor Yellow
    
    while ($true) {
        $bodyParams = @{ page = $page; tabSort = "blacklist"; startDate = $startDate; endDate = $endDate; findCondition = "all"; findKeyword = ""; size = 50 }
        $body = ($bodyParams.GetEnumerator() | ForEach-Object { "$($_.Name)=$($_.Value)" }) -join "&"

        Write-Host "페이지 $page 요청 중..." -ForegroundColor Cyan
        $response = Invoke-WebRequest -Uri $uri -Method "POST" -WebSession $session -Headers $headers -ContentType "application/x-www-form-urlencoded" -Body $body

        $tableBody = $response.ParsedHtml.body.getElementsByTagName("tbody") | Where-Object { $_.parentElement.caption.innerText -eq "요주의 IP 목록" }
        
        if (-not $tableBody -or $response.Content -like '*총 <em>0</em>*') {
            Write-Host "더 이상 데이터가 없어 조회를 종료합니다." -ForegroundColor Yellow
            break
        }
        
        $rows = $tableBody.getElementsByTagName("tr")
        $currentPageResults = foreach ($row in $rows) {
            $cells = $row.getElementsByTagName("td")
            [PSCustomObject]@{ IP = $cells[0].innerText.Trim(); Country = $cells[1].innerText.Trim(); Reason = $cells[2].innerText.Trim(); RegistrationDate = $cells[3].innerText.Trim(); ReleaseDate = $cells[4].innerText.Trim(); Views = $cells[5].innerText.Trim() }
        }

        $allResults += $currentPageResults
        Write-Host " -> $($currentPageResults.Count)개 항목 발견. (누적: $($allResults.Count)개)" -ForegroundColor Green

        $page++
        Start-Sleep -Seconds 1
    }

    Write-Host "----------------------------------------"
    Write-Host "최종적으로 총 $($allResults.Count)개의 데이터를 가져왔습니다." -ForegroundColor Magenta
    $allResults
}
catch {
    Write-Error "스크립트 실행 중 예외가 발생했습니다: $($_.Exception.Message)"
}
finally {
    # 4. 스크립트 종료 시 항상 로그 기록 중지 및 파일 저장
    Stop-Transcript
}