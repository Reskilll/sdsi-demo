@REM ----------------------------------------------------------------------------
@REM Maven Wrapper startup batch script, version 3.3.2
@REM ----------------------------------------------------------------------------
@REM Required ENV vars:
@REM JAVA_HOME - location of a JDK home dir
@REM ----------------------------------------------------------------------------

@setlocal EnableDelayedExpansion

set "MAVEN_PROJECTBASEDIR=%cd%"

@REM Find the project base dir
if not "%MAVEN_PROJECTBASEDIR%"=="" goto endChdir

set "MAVEN_PROJECTBASEDIR=%~dp0.."
:endChdir
cd /d "%MAVEN_PROJECTBASEDIR%"

@REM Resolve JAVACMD
if "%JAVA_HOME%"=="" set "JAVA_HOME=C:\Program Files\Java\jdk-25"
if not exist "%JAVA_HOME%\bin\java.exe" (
    echo ERROR: JAVA_HOME is not set and no 'java' command could be found in your PATH.
    echo Please set the JAVA_HOME variable in your environment to match the
    echo location of your Java installation.
    exit /b 1
)
set "JAVACMD=%JAVA_HOME%\bin\java.exe"

set "WRAPPER_JAR=%MAVEN_PROJECTBASEDIR%\.mvn\wrapper\maven-wrapper.jar"
set "WRAPPER_LAUNCHER=org.apache.maven.wrapper.MavenWrapperMain"

if not exist "%WRAPPER_JAR%" goto downloadWrapperJar

:run
%JAVACMD% ^
    %MAVEN_OPTS% ^
    %MAVEN_DEBUG_OPTS% ^
    -classpath "%WRAPPER_JAR%" ^
    "-Dmaven.multiModuleProjectDirectory=%MAVEN_PROJECTBASEDIR%" ^
    %WRAPPER_LAUNCHER% %MAVEN_CONFIG% %* ^
    -Dmaven.repo.local="%MAVEN_PROJECTBASEDIR%\.m2"
if %ERRORLEVEL% neq 0 goto fail
goto end

:downloadWrapperJar
echo Downloading Maven wrapper...
mkdir "%MAVEN_PROJECTBASEDIR%\.mvn\wrapper" 2>nul

@REM Try PowerShell download
powershell -Command "& { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%MAVEN_WRAPPER_URL%' -OutFile '%WRAPPER_JAR%'; }"
if exist "%WRAPPER_JAR%" goto run

@REM Fallback: try certutil
for /f "tokens=2 delims==" %%I in ('type "%MAVEN_PROJECTBASEDIR%\.mvn\wrapper\maven-wrapper.properties" ^| findstr "wrapperUrl"') do set "MAVEN_WRAPPER_URL=%%I"
certutil -urlcache -split -f "%MAVEN_WRAPPER_URL%" "%WRAPPER_JAR%" 2>nul
if exist "%WRAPPER_JAR%" goto run

echo ERROR: Could not download Maven wrapper JAR from %MAVEN_WRAPPER_URL%
exit /b 1

:end
endlocal
exit /b %ERRORLEVEL%

:fail
echo Maven execution failed.
endlocal
exit /b 1