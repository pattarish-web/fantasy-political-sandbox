# ใส่ Gemini API key 3 ตัวใน GitHub Secrets (รันบนเครื่องคุณ)
# Usage: .\scripts\set-github-secrets.ps1

$Repo = "pattarish-web/fantasy-political-sandbox"

Write-Host "Repo: $Repo"
Write-Host "แต่ละขั้นจะให้วาง API key แล้วกด Enter (key ไม่แสดงบนหน้าจอ)"
Write-Host ""

foreach ($n in 1, 2, 3) {
    $name = "GEMINI_API_KEY_$n"
    Write-Host "--- $name ---" -ForegroundColor Cyan
    gh secret set $name -R $Repo
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ล้มเหลวที่ $name" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "เสร็จแล้ว ตรวจรายการ:" -ForegroundColor Green
gh secret list -R $Repo
