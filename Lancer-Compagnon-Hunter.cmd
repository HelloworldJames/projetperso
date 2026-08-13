@echo off
title Compagnon Hunter - Recepteur local
cd /d "%~dp0"
powershell.exe -NoLogo -NoExit -ExecutionPolicy Bypass -File "%~dp0tools\hunter_link_scanner\start.ps1"
