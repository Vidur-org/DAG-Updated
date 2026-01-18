# WebGPT Testing Script for PowerShell

# Test chat endpoint and display full response
$response = Invoke-RestMethod `
  -Uri "http://localhost:8000/chat" `
  -Method POST `
  -Headers @{ "Content-Type" = "application/json" } `
  -Body '{"message":"tesla Q3 FY2022-23 (October-December 2022) financial results: net profit, total income, key fundamentals."}'

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "WEBGPT RESPONSE" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Type: " -NoNewline -ForegroundColor Yellow
Write-Host $response.type

Write-Host "`nQuick Answer:" -ForegroundColor Yellow
Write-Host $response.quick_answer

Write-Host "`nFull Reply:" -ForegroundColor Yellow
Write-Host $response.reply

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "SOURCES USED" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

$sourceNum = 1
foreach ($source in $response.sources) {
    Write-Host "[$sourceNum] " -NoNewline -ForegroundColor Cyan
    Write-Host $source.title -ForegroundColor White
    Write-Host "    URL: " -NoNewline -ForegroundColor Yellow
    Write-Host $source.url -ForegroundColor Blue
    Write-Host "    Snippet: " -NoNewline -ForegroundColor Yellow
    Write-Host $source.snippet -ForegroundColor Gray
    Write-Host ""
    $sourceNum++
}

Write-Host "`n========================================`n" -ForegroundColor Cyan

# Save to file for detailed inspection
$response | ConvertTo-Json -Depth 10 | Out-File "webgpt_response.json"
Write-Host "Full response saved to: webgpt_response.json" -ForegroundColor Green