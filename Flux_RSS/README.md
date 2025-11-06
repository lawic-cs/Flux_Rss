# Création de flux RSS à partir d'une URL

Ce petit script Python demande une URL, télécharge la page, extrait le titre et la description (si disponibles) et génère un flux RSS 2.0 contenant la page comme un item.

Prérequis
- Python 3.x (le script utilise uniquement la bibliothèque standard)

Usage (PowerShell sous Windows)

Ouvrez PowerShell dans le dossier `C:\Users\lalan\Documents\Python\Flux_RSS` puis lancez :

```powershell
python .\create_rss.py
```

Suivez les instructions :
- Entrez l'URL (ex. https://example.com)
- Entrez le nom du fichier de sortie (par défaut `feed.xml`)

Le script créera le fichier RSS dans le répertoire courant.

Notes
- Si l'URL ne contient pas de schéma (http/https), `http://` sera préfixé automatiquement.
- Le script essaie d'extraire `<title>` et la meta `description` ou `og:description`.
- Le fichier RSS est au format RSS 2.0 et contient un seul item (la page fournie). Pour créer un flux multi-items, on peut adapter le script pour lire plusieurs URL depuis un fichier ou une boucle.
 - Si l'URL ne contient pas de schéma (http/https), `http://` sera préfixé automatiquement.
 - Le script essaie d'extraire `<title>` et la meta `description` ou `og:description`.
 - Le fichier RSS est au format RSS 2.0 et contient un seul item (la page fournie). Pour créer un flux multi-items, on peut adapter le script pour lire plusieurs URL depuis un fichier ou une boucle.

Double-cliquer pour lancer
--------------------------------
Si vous préférez lancer le script en double-cliquant, un fichier batch est fourni : `run_create_rss.bat`.
Double-cliquez sur `run_create_rss.bat` dans l'Explorateur Windows — le batch exécutera automatiquement `Site.xlsx` situé dans le même dossier (chemin : `C:\Users\lalan\Documents\Python\Flux_RSS\Site.xlsx`).

Remarques:
- Le batch utilise la commande `python` ; assurez-vous que Python est dans votre PATH. Si ce n'est pas le cas, éditez `run_create_rss.bat` et remplacez `python` par le chemin complet de l'exécutable Python (ex. `C:\Python39\python.exe`).
- Le fichier batch se trouve dans le même dossier que `create_rss.py` et utilise `%~dp0` pour trouver le script.

Traitement par liste (Excel / CSV)
----------------------------------
Le script peut maintenant lire un fichier Excel (.xlsx) ou un fichier CSV contenant les URL à traiter :

- Format attendu : colonne A = URL (à partir de A1), colonne B = nom du fichier de sortie (optionnel). Si la colonne B est vide, le script génèrera un nom depuis le domaine.
- Exemples de formats supportés : `liste.xlsx`, `liste.csv`.
- Pour `.xlsx` : installez `openpyxl` si nécessaire :

```powershell
pip install openpyxl
```

Utilisation : lancez `create_rss.py` (ou double-cliquez `run_create_rss.bat`), et à l'invite entrez le chemin complet du fichier `.xlsx` ou `.csv`.

Exemple d'une ligne Excel:

| A (URL) | B (nom du fichier) |
|---------|---------------------|
| https://example.com | monflux.xml |

Le script parcourra chaque ligne et créera un fichier XML par URL. À la fin un résumé est affiché (traités / échecs).
Les fichiers XML générés sont placés dans le sous-dossier `liste_des_flux` situé dans le même dossier que le script.
Si le dossier n'existe pas, il sera créé automatiquement.
Exemples d'améliorations possibles
- Ajouter la prise en charge d'une liste d'URL (fichier CSV / TXT)
- Sauvegarder la date de publication réelle si elle est détectable dans la page
- Ajouter un mode "daemon" qui vérifie les changements et met à jour le flux

Auteur: généré automatiquement
