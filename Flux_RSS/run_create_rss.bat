@echo off
REM Lance le script Python placé dans le même dossier; double-cliquez ce fichier pour exécuter
pushd "%~dp0"
@echo on
REM Lance automatiquement Site.xlsx dans le même dossier
if not exist "Site.xlsx" (
	echo Fichier Site.xlsx introuvable dans "%~dp0"
	pause
	popd
	exit /b 1
)
REM Créer le sous-dossier de sortie si besoin (mkdir ignore s'il existe)
mkdir "%~dp0liste_des_flux" 2>nul
python "%~dp0create_rss.py" "%~dp0Site.xlsx"
IF %ERRORLEVEL% NEQ 0 (
	echo Une erreur est survenue.
)
@echo off
echo.
pause
popd
