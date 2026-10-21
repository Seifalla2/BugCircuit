$ErrorActionPreference = 'Stop'
if (Test-Path '.git') {
    throw 'Git metadata already exists. Inspect status and remote before publishing.'
}
# Preconditions: create an empty PUBLIC repo at the destination first.
git init
if ($LASTEXITCODE -ne 0) { throw 'git init failed' }
git branch -M main
if ($LASTEXITCODE -ne 0) { throw 'git branch failed' }
git add .
if ($LASTEXITCODE -ne 0) { throw 'git add failed' }
git commit -m 'feat: initial evidence-first BugCircuit v0.1 alpha'
if ($LASTEXITCODE -ne 0) { throw 'git commit failed; configure local name/email if needed' }
git remote add origin 'https://github.com/Seifalla2/BugCircuit.git'
if ($LASTEXITCODE -ne 0) { throw 'git remote add failed' }
Write-Host 'Review the commit and push by running: git push -u origin main'
