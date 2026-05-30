@echo off
chcp 65001 >nul 2>&1
setlocal

set "SCRIPT_DIR=%~dp0"
set "LOG_DIR=%SCRIPT_DIR%log"
set "PROJECT_DIR=%SCRIPT_DIR%.."

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: Generate timestamp for log filename
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%i"
set "LOG_FILE=%LOG_DIR%\mcp_%STAMP%.log"

echo ============================================
echo  superwx4 MCP Server
echo  Log: %LOG_FILE%
echo ============================================

cd /d "%PROJECT_DIR%"

:: stdout = MCP protocol (for Claude), stderr = logs (to file)
python -m mcp.server --log-level INFO 2>"%LOG_FILE%"

endlocal
