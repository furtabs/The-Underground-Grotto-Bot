@echo off
echo ================================================================
echo The Underground Grotto Bot - Starting...
echo ================================================================
echo.

REM Check if virtual environment exists
if not exist venv (
    echo Virtual environment not found. Running setup...
    echo.
    call setup.bat
    if errorlevel 1 (
        echo Setup failed. Please check the errors above.
        pause
        exit /b 1
    )
)

REM Check if config.json5 exists
if not exist config.json5 (
    echo.
    echo WARNING: config.json5 not found!
    echo Please create config.json5 with your bot token and settings.
    echo.
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    echo Try running setup.bat again
    pause
    exit /b 1
)

REM Start the bot
echo Starting bot...
echo.
python main.py

REM If bot exits, pause to see error messages
if errorlevel 1 (
    echo.
    echo ================================================================
    echo Bot exited with an error
    echo ================================================================
    echo.
)
pause


