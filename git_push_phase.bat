@echo off
REM Git Push Script for Phase Completion (Windows)
REM Usage: git_push_phase.bat "Phase 1: Database Schema"

set PHASE_NAME=%1
set COMMIT_MESSAGE=Complete %PHASE_NAME% - Add suitability analysis models and admin

REM Check if we're in a git repository
git rev-parse --git-dir >nul 2>&1
if errorlevel 1 (
    echo Error: Not a git repository
    exit /b 1
)

REM Check if there are changes to commit
git diff --quiet
if errorlevel 1 goto has_changes
git diff --cached --quiet
if errorlevel 1 goto has_changes
echo No changes to commit
exit /b 0

:has_changes
REM Add all changes
echo Adding all changes...
git add .

REM Commit with phase message
echo Committing changes: %COMMIT_MESSAGE%
git commit -m "%COMMIT_MESSAGE%"

REM Get current branch
for /f "tokens=*" %%i in ('git branch --show-current') do set CURRENT_BRANCH=%%i

REM Push to current branch
echo Pushing to branch: %CURRENT_BRANCH%
git push origin %CURRENT_BRANCH%

echo ✅ Successfully pushed %PHASE_NAME% to GitHub!

