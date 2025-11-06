@echo off
REM ========================================================================
REM  Script de mise à jour automatique des flux RSS DRAAF
REM  Fichier: update_flux_rss.bat
REM ========================================================================

echo.
echo ========================================================================
echo   Mise a jour des flux RSS DRAAF
echo ========================================================================
echo.

cd /d "%~dp0"

REM Configuration - Modifiez ces lignes selon vos besoins
REM -------------------------------------------------------

REM Viticulture Auvergne
echo [1/3] Mise a jour : Viticulture Auvergne...
python create_rss_robust.py "https://draaf.auvergne-rhone-alpes.agriculture.gouv.fr/viticulture-auvergne-2025-r1445.html" "Viticulture_Auvergne.xml"
if %errorlevel% neq 0 (
    echo ERREUR lors de la mise a jour de Viticulture Auvergne
) else (
    echo OK - Viticulture Auvergne mis a jour
)
echo.

REM Ajoutez d'autres flux ici si nécessaire
REM Exemple pour Grandes Cultures :
REM echo [2/3] Mise a jour : Grandes Cultures...
REM python create_rss_robust.py "URL_GRANDES_CULTURES" "GrandesCultures.xml"
REM echo.

REM Exemple pour Arboriculture :
REM echo [3/3] Mise a jour : Arboriculture...
REM python create_rss_robust.py "URL_ARBORICULTURE" "Arboriculture.xml"
REM echo.

echo ========================================================================
echo   Mise a jour terminee
echo ========================================================================
echo.
echo Les flux RSS sont disponibles dans le dossier : liste_des_flux\
echo.

pause
