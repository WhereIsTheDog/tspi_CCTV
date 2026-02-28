@echo off
REM Creates a deployment package for ARM devices (e.g. TSPI RK3566)

echo ==========================================
echo   Create ARM Deployment Package
echo ==========================================
echo.

REM Build the deploy directory
set DEPLOY_DIR=cctv_monitor_arm_deploy
if exist %DEPLOY_DIR% rmdir /s /q %DEPLOY_DIR%
mkdir %DEPLOY_DIR%

echo [1/3] Copying files...
copy cctv_monitor.py %DEPLOY_DIR%\
copy requirements_arm.txt %DEPLOY_DIR%\
copy install_arm.sh %DEPLOY_DIR%\
copy systemd_service.sh %DEPLOY_DIR%\

echo [2/3] Writing run script...
(
echo #!/bin/bash
echo cd "$(dirname "$0")"
echo python3 cctv_monitor.py
) > %DEPLOY_DIR%\run_cctv.sh

echo [3/3] Compressing...
powershell Compress-Archive -Path %DEPLOY_DIR% -DestinationPath cctv_monitor_arm.zip -Force

echo.
echo ==========================================
echo   Done! Package: cctv_monitor_arm.zip
echo ==========================================
echo.
echo Deployment steps:
echo   1. Transfer cctv_monitor_arm.zip to the ARM device
echo   2. unzip cctv_monitor_arm.zip
echo   3. cd cctv_monitor_arm_deploy
echo   4. sudo bash install_arm.sh
echo.
pause
