@echo off
setlocal
pushd "%~dp0" || exit /b 1

if not defined ODOO_PG_BIN set "ODOO_PG_BIN=D:\Programming\Programs\PostgreSQL\bin"
set "ODOO_LOCAL_CONFIG=.odoorc"
if not exist "%ODOO_LOCAL_CONFIG%" set "ODOO_LOCAL_CONFIG=odoo.conf"

if not exist "%ODOO_PG_BIN%\pg_ctl.exe" (
    echo PostgreSQL was not found. Set ODOO_PG_BIN to its bin folder.
    goto :failed
)
if not exist "pgdata\PG_VERSION" (
    echo The project's local PostgreSQL data folder is missing.
    goto :failed
)
if not exist "venv\Scripts\python.exe" (
    echo The Python environment is missing. See README.md.
    goto :failed
)
if not exist "odoo19\odoo-bin" (
    echo Odoo 19 source files are missing. See README.md.
    goto :failed
)
if not exist "%ODOO_LOCAL_CONFIG%" (
    echo The Odoo configuration file is missing.
    goto :failed
)

"%ODOO_PG_BIN%\pg_isready.exe" -q -h 127.0.0.1 -p 5433
if errorlevel 1 (
    echo Starting PostgreSQL...
    "%ODOO_PG_BIN%\pg_ctl.exe" -D "%CD%\pgdata" -l "%CD%\postgres-local.log" -o "-h 127.0.0.1 -p 5433" -w start
    if errorlevel 1 (
        echo PostgreSQL did not start. See postgres-local.log.
        goto :failed
    )
)

curl.exe --noproxy "*" --silent --fail --max-time 2 "http://127.0.0.1:8069/web/health" >nul 2>&1
if errorlevel 1 (
    echo Starting Odoo...
    powershell.exe -NoProfile -Command "$ErrorActionPreference = 'Stop'; Start-Process -FilePath '.\venv\Scripts\python.exe' -ArgumentList '-B','odoo19\odoo-bin','-c',$env:ODOO_LOCAL_CONFIG,'--db_port=5433','--dev=all','--logfile=odoo-local.log','--without-demo' -WindowStyle Hidden"
    if errorlevel 1 goto :failed
)

echo Waiting for Odoo and the database...
powershell.exe -NoProfile -Command "$deadline = (Get-Date).AddSeconds(60); do { try { $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8069/web/health?db_server_status=1' -TimeoutSec 2 -ErrorAction Stop; if ($health.status -eq 'pass' -and $health.db_server_status -eq $true) { exit 0 } } catch {} Start-Sleep -Seconds 1 } while ((Get-Date) -lt $deadline); exit 1"
if errorlevel 1 (
    echo Odoo did not become ready. See odoo-local.log.
    goto :failed
)

echo Odoo is ready: http://127.0.0.1:8069/odoo?db=library_db
if /i not "%~1"=="--no-browser" start "" "http://127.0.0.1:8069/odoo?db=library_db"
popd
exit /b 0

:failed
if /i not "%~1"=="--no-browser" pause
popd
exit /b 1
