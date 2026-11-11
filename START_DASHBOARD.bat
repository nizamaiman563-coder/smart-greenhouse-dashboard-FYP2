@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title GreenEdge Fuzzy PWM Dashboard Launcher

cls
echo ============================================================
echo   GREENEDGE FUZZY PWM COMMAND CENTRE
echo   One-click launcher for Windows / Anaconda
echo ============================================================
echo.
echo Project folder:
echo %CD%
echo.

REM ------------------------------------------------------------
REM Find a usable Python installation.
REM Prefer Anaconda/Miniconda because this project was tested there.
REM ------------------------------------------------------------
set "PYEXE="

if exist "%USERPROFILE%\anaconda3\python.exe" set "PYEXE=%USERPROFILE%\anaconda3\python.exe"
if not defined PYEXE if exist "%USERPROFILE%\miniconda3\python.exe" set "PYEXE=%USERPROFILE%\miniconda3\python.exe"
if not defined PYEXE if exist "%LOCALAPPDATA%\anaconda3\python.exe" set "PYEXE=%LOCALAPPDATA%\anaconda3\python.exe"
if not defined PYEXE if exist "%LOCALAPPDATA%\miniconda3\python.exe" set "PYEXE=%LOCALAPPDATA%\miniconda3\python.exe"
if not defined PYEXE if exist "C:\ProgramData\anaconda3\python.exe" set "PYEXE=C:\ProgramData\anaconda3\python.exe"
if not defined PYEXE if exist "C:\ProgramData\miniconda3\python.exe" set "PYEXE=C:\ProgramData\miniconda3\python.exe"

if not defined PYEXE (
    for /f "delims=" %%P in ('where python 2^>nul') do (
        if not defined PYEXE set "PYEXE=%%P"
    )
)

if not defined PYEXE (
    echo [ERROR] Python was not found on this computer.
    echo.
    echo Install Anaconda or Python, then double-click this file again.
    echo Recommended: Anaconda with Python 3.11 or newer.
    echo.
    pause
    exit /b 1
)

echo Using Python:
echo "%PYEXE%"
"%PYEXE%" --version
echo.

REM ------------------------------------------------------------
REM Verify project files before doing anything else.
REM ------------------------------------------------------------
if not exist "%CD%\app.py" (
    echo [ERROR] app.py is missing from:
    echo %CD%
    echo.
    echo Keep START_DASHBOARD.bat in the SAME folder as app.py.
    pause
    exit /b 1
)

if not exist "%CD%\assets\greenhouse_digital_twin.png" (
    echo [ERROR] Greenhouse visual is missing:
    echo %CD%\assets\greenhouse_digital_twin.png
    echo.
    echo Re-extract the complete project ZIP and try again.
    pause
    exit /b 1
)

REM ------------------------------------------------------------
REM Check required packages. Install only when something is missing.
REM ------------------------------------------------------------
"%PYEXE%" -c "import streamlit, pandas, plotly" >nul 2>&1
if errorlevel 1 (
    echo Required Python packages are missing.
    echo Installing Streamlit, Pandas and Plotly...
    echo.
    "%PYEXE%" -m pip install --disable-pip-version-check -r "%CD%\requirements.txt"
    if errorlevel 1 (
        echo.
        echo [ERROR] Package installation failed.
        echo Check your internet connection, then run this launcher again.
        echo.
        pause
        exit /b 1
    )
)

echo Packages: OK
echo Dashboard: READY
echo.

REM ------------------------------------------------------------
REM Find the first free Streamlit port so an older dashboard
REM cannot block the new one.
REM ------------------------------------------------------------
set "PORT=8501"
for /f %%P in ('powershell -NoProfile -Command "$p=8501; while(Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue){$p++}; $p"') do set "PORT=%%P"

echo Starting Streamlit...
echo The browser should open automatically at http://localhost:%PORT%
echo.
echo IMPORTANT: Keep this window open while using the dashboard.
echo To stop the dashboard, press Ctrl+C in this window.
echo ============================================================
echo.

"%PYEXE%" -m streamlit run "%CD%\app.py" --server.port %PORT% --server.headless false

set "EXITCODE=%ERRORLEVEL%"
echo.
if not "%EXITCODE%"=="0" (
    echo [ERROR] The dashboard stopped with exit code %EXITCODE%.
    echo Copy the error shown above if you need troubleshooting.
) else (
    echo Dashboard stopped normally.
)
echo.
pause
exit /b %EXITCODE%
