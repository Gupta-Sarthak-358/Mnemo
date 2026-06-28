@echo off
cd /d "%~dp0"
start "" /B ".venv\Scripts\python.exe" -m mnemo.daemon
echo Mnemo started. Press Ctrl+M to open.
