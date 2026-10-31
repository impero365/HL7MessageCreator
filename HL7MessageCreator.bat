@echo off
cd /d "%~dp0"

REM --- Check if Python 3.12 is available ---
echo Checking for Python 3.12...
py -3.12 --version >nul 2>nul
if errorlevel 1 (
    echo Python 3.12 not found. Attempting to install...
    where winget >nul 2>nul
    if errorlevel 1 (
        echo winget is not available. Install Python 3.12 from https://www.python.org/downloads/
        pause
        exit /b 1
    )
    winget install --silent --accept-package-agreements --accept-source-agreements Python.Python.3.12
    if errorlevel 1 (
        echo Failed to install Python 3.12.
        pause
        exit /b 1
    )
    echo.
    echo Python 3.12 has been installed.
    echo Please close this window and run the script again to complete setup.
    pause
    exit /b 0
) else (
    echo Python 3.12 is available.
)

REM --- Remove old/broken virtual environment if it exists ---
if exist ".venv" (
    echo Checking virtual environment...
    .venv\Scripts\python.exe --version 2>nul | findstr /C:"Python 3.12" >nul
    if errorlevel 1 (
        echo Virtual environment is missing or is not Python 3.12. Removing...
        rmdir /s /q .venv
        if exist ".venv" (
            echo WARNING: Could not remove .venv folder. Please delete it manually and run again.
            pause
            exit /b 1
        )
        echo Old virtual environment removed.
    ) else (
        echo Virtual environment is OK.
    )
)

REM --- Create virtual environment if not already created ---
if not exist ".venv" (
    echo Creating virtual environment...
    py -3.12 -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo Virtual environment created successfully.
)

REM --- Activate virtual environment ---
echo Activating virtual environment...
call .venv\Scripts\activate
if errorlevel 1 (
    echo Failed to activate virtual environment!
    pause
    exit /b 1
)

REM --- Ensure pip is up to date inside venv ---
echo Updating pip...
python -m pip install --upgrade pip --quiet

REM --- Install required packages inside venv ---
echo Installing required packages...
python -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo Failed to install required packages!
    pause
    exit /b 1
)

REM --- Optional: install the dev tools, including PyInstaller ---
REM python -m pip install -r requirements-dev.txt --quiet

echo.
echo ========================================
echo Setup complete!
echo ========================================
echo.

REM --- Run your Python script inside the venv ---
echo Running HL7MessageCreator.py ...
echo.
python HL7MessageCreator.py
if errorlevel 1 (
    echo.
    echo The application exited with an error.
)

echo.
echo ========================================
echo Application closed.
echo ========================================
echo Virtual environment is still active.
echo To deactivate, type: deactivate
echo.

pause
