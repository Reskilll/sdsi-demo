@echo off
REM Build & test script for Flash Sale Inventory Reservation System
REM Requires: JDK 21+ on PATH
setlocal enabledelayedexpansion

set OUT_DIR=out
set MAIN_SRC=src\main\java
set TEST_SRC=src\test\java

echo === Compiling main sources ===
if not exist %OUT_DIR%\classes mkdir %OUT_DIR%\classes
dir /s /b %MAIN_SRC%\*.java > %OUT_DIR%\sources.txt
javac --release 21 -d %OUT_DIR%\classes @%OUT_DIR%\sources.txt
if %ERRORLEVEL% neq 0 (
    echo COMPILE FAILED
    exit /b 1
)
echo Main sources compiled OK.

echo === Compiling test sources ===
if not exist %OUT_DIR%\test-classes mkdir %OUT_DIR%\test-classes
dir /s /b %TEST_SRC%\*.java > %OUT_DIR%\test-sources.txt
javac --release 21 -cp %OUT_DIR%\classes -d %OUT_DIR%\test-classes @%OUT_DIR%\test-sources.txt
if %ERRORLEVEL% neq 0 (
    echo TEST COMPILE FAILED
    exit /b 1
)
echo Test sources compiled OK.

echo === Running tests ===
java -ea -cp %OUT_DIR%\classes;%OUT_DIR%\test-classes com.flashsale.TestRunner
if %ERRORLEVEL% neq 0 (
    echo TESTS FAILED
    exit /b 1
)

echo === Building JAR ===
jar --create --file %OUT_DIR%\flash-sale.jar --main-class=com.flashsale.cli.ReservationCli -C %OUT_DIR%\classes .
echo JAR built: %OUT_DIR%\flash-sale.jar

echo.
echo === BUILD SUCCESS ===
echo Run:  java -jar %OUT_DIR%\flash-sale.jar demo
echo Test: java -ea -cp %OUT_DIR%\classes;%OUT_DIR%\test-classes com.flashsale.TestRunner