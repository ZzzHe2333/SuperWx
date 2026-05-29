@echo off
REM wxauto4 regression test runner (Windows batch)
REM Usage: scripts\run_regression.bat [--online]

echo ========================================
echo wxauto4 Regression Tests
echo ========================================

cd /d "%~dp0\.."

echo.
echo [1/3] Safety Check...
python tests\safety_check.py
if errorlevel 1 (
    echo SAFETY CHECK FAILED
    exit /b 1
)

echo.
echo [2/3] Offline Regression...
python tests\regression_all.py
if errorlevel 1 (
    echo REGRESSION FAILED
    exit /b 1
)

echo.
echo [3/3] Done.
if "%1"=="--online" (
    echo Running online tests...
    python tests\regression_all.py --online
)

echo.
echo ALL TESTS PASSED
