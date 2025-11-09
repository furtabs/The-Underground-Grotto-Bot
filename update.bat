@echo off
echo ================================================================
echo The Underground Grotto Bot - Update Dependencies
echo ================================================================
echo.

REM Activate virtual environment
call git pull
if errorlevel 1 (
    echo ERROR: Failed to pull repo
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist venv (
    echo Virtual environment not found. Please run setup.bat first.
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

echo Updating pip...
pip install --upgrade pip

echo.
echo Installing/updating required packages...
pip install -r requirements.txt --upgrade

if errorlevel 1 (
    echo.
    echo ERROR: Failed to update packages
    pause
    exit /b 1
)

echo.
echo ================================================================
echo Dependencies updated successfully!
echo ================================================================
echo.
pause


