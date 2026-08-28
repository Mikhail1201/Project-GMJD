@echo off
REM ============================================================
REM Sube main.py e i2c_lcd.py al ESP32 simulado (Wokwi VS Code)
REM y lo reinicia para que arranque main.py automaticamente.
REM
REM Requisito: la simulacion debe estar CORRIENDO (con el >>> del
REM REPL visible) antes de ejecutar este script.
REM ============================================================

set PUERTO=port:rfc2217://localhost:4000

echo.
echo [1/3] Subiendo i2c_lcd.py...
mpremote connect %PUERTO% fs cp i2c_lcd.py :i2c_lcd.py
if errorlevel 1 goto error

echo.
echo [2/3] Subiendo main.py...
mpremote connect %PUERTO% fs cp main.py :main.py
if errorlevel 1 goto error

echo.
echo [3/3] Reiniciando el ESP32 simulado...
mpremote connect %PUERTO% exec "import machine; machine.reset()"
if errorlevel 1 goto error

echo.
echo Listo. Revisa la consola de la simulacion en VS Code.
goto fin

:error
echo.
echo ERROR: alguno de los pasos fallo. Verifica que la simulacion
echo este corriendo (el ">>>" visible) antes de ejecutar este script.

:fin
