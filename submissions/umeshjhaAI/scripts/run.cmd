@echo off
rem Launch the Job Scheduler SPA: start the backend server and open the frontend.
rem
rem Usage:  scripts\run.cmd [port]
rem
rem The single server (server.py) serves both the static frontend (GET /) and
rem the scheduler API (POST /api/schedule), so this one command runs everything.

setlocal

set "PORT=%~1"
if "%PORT%"=="" set "PORT=8380"

rem Resolve the project root (one level up from this script's directory).
set "ROOT_DIR=%~dp0.."

rem Pick a Python interpreter: PYTHON env var, then py, then python.
set "PYTHON_BIN=%PYTHON%"
if not defined PYTHON_BIN set "PYTHON_BIN=py"
if not defined PYTHON_BIN set "PYTHON_BIN=python"

set "URL=http://localhost:%PORT%"

rem Open the browser best-effort (the server keeps running either way).
start "" "%URL%" 2>nul

cd /d "%ROOT_DIR%"
echo Starting Job Scheduler SPA on %URL% ...
"%PYTHON_BIN%" server.py %PORT%

endlocal
