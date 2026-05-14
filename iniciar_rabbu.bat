@echo off
setlocal

cd /d "%~dp0"

echo ==========================================
echo      RABBU - Inicializacao automatica
echo ==========================================
echo.

set "PYTHON_BOOTSTRAP="
where py >nul 2>nul
if %errorlevel%==0 set "PYTHON_BOOTSTRAP=py -3.12"

if not defined PYTHON_BOOTSTRAP (
    where python >nul 2>nul
    if %errorlevel%==0 set "PYTHON_BOOTSTRAP=python"
)

if not defined PYTHON_BOOTSTRAP (
    echo Python nao foi encontrado nesta maquina.
    echo Instale o Python 3.12 e tente novamente.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Criando ambiente virtual...
    %PYTHON_BOOTSTRAP% -m venv .venv
    if errorlevel 1 goto :erro
)

call .venv\Scripts\activate.bat
if errorlevel 1 goto :erro

echo Instalando dependencias...
python -m pip install -r requirements.txt
if errorlevel 1 goto :erro

echo Aplicando migracoes...
python manage.py migrate
if errorlevel 1 goto :erro

echo Carregando dados de demonstracao...
python manage.py seed_demo
if errorlevel 1 goto :erro

echo Abrindo o sistema no navegador...
start "" http://127.0.0.1:8000/login/

echo.
echo Servidor iniciado. Para encerrar, feche esta janela.
echo.
python manage.py runserver
goto :eof

:erro
echo.
echo Ocorreu um erro durante a inicializacao do sistema.
echo Revise as mensagens acima.
pause
exit /b 1
