@echo off
REM Poshmark Web Scraper - Task Scheduler Batch File
REM This script activates the virtual environment and runs the scraper

REM Navigate to project directory
cd /d "C:\Users\mguan\OneDrive - Restaurant Services, Inc\Desktop\Personal\posh"

REM Activate virtual environment
call venv\Scripts\activate

REM Run the scraper
python main.py

REM Pause to see output (remove this line for Task Scheduler)
REM pause
