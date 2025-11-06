# 🚀 Guide Rapide - Générateur RSS Robuste

## ✅ Installation (Une seule fois)

```bash
pip install beautifulsoup4 requests lxml
```

## 📖 Utilisation

### Mode Simple (Recommandé)

```bash
python create_rss_robust.py
```

Puis saisir :
1. URL de la page index (ex: page listant les bulletins BSV)
2. Nom du fichier de sortie (ex: `Viticulture.xml`)
3. Mots-clés optionnels (ex: `bsv,bulletin`)

### Mode Ligne de Commande

```bash
python create_rss_robust.py "URL_PAGE" "FICHIER_SORTIE.xml"
```

**Exemple concret :**
```bash
python create_rss_robust.py "https://draaf.auvergne-rhone-alpes.agriculture.gouv.fr/viticulture-auvergne-2025-r1445.html" "Viticulture_2025.xml"
```

## 🎯 Résultat

Le script génère un fichier XML dans `liste_des_flux/` contenant :
- ✅ Tous les bulletins de la page
- ✅ Leurs **vraies dates** de publication
- ✅ Tri automatique (plus récent en premier)
- ✅ Catégorie, auteur, GUID

## 💻 Utilisation dans votre Site Web

```javascript
fetch('liste_des_flux/Viticulture_2025.xml')
  .then(response => response.text())
  .then(str => new DOMParser().parseFromString(str, "text/xml"))
  .then(data => {
    const items = data.querySelectorAll('item');
    const dernier = items[0]; // Le plus récent !
    
    const titre = dernier.querySelector('title').textContent;
    const lien = dernier.querySelector('link').textContent;
    const date = dernier.querySelector('pubDate').textContent;
    
    document.getElementById('dernier-bulletin').innerHTML = `
      <h2><a href="${lien}">${titre}</a></h2>
      <p>Publié le ${new Date(date).toLocaleDateString('fr-FR')}</p>
    `;
  });
```

## 🔄 Mise à Jour Automatique

### Windows : Créer `update_flux.bat`

```batch
@echo off
cd /d C:\Users\lalan\Documents\Python\Flux_RSS
python create_rss_robust.py "VOTRE_URL" "VOTRE_FICHIER.xml"
pause
```

Puis planifier dans le **Planificateur de tâches** Windows.

## ✅ Avantages de ce Script

| Fonctionnalité | Description |
|----------------|-------------|
| 🛡️ **Robuste** | Utilise BeautifulSoup → fonctionne même si le HTML change |
| 📅 **Dates réelles** | Extrait les vraies dates depuis le contenu (format français) |
| 🎯 **Intelligent** | Détecte automatiquement catégorie et auteur |
| 🔄 **Tri auto** | Bulletins triés par date (dernier en premier) |
| 🌐 **Universel** | Fonctionne avec n'importe quelle page web |

## 🆚 Comparaison avec l'Ancien Script

| Critère | `create_rss.py` (ancien) | `create_rss_robust.py` (nouveau) |
|---------|-------------------------|----------------------------------|
| Parsing HTML | ❌ Regex (fragile) | ✅ BeautifulSoup (robuste) |
| Plusieurs bulletins | ❌ Non | ✅ Oui (toute la page) |
| Dates réelles | ⚠️ Basique | ✅ Multi-formats |
| Résistance aux changements | ❌ Faible | ✅ Excellente |

## 📝 Exemple Complet

```bash
# 1. Générer le flux RSS
python create_rss_robust.py "https://draaf.auvergne-rhone-alpes.agriculture.gouv.fr/viticulture-auvergne-2025-r1445.html" "Viti.xml"

# 2. Vérifier le résultat
python verify_rss.py liste_des_flux/Viti.xml

# 3. Utiliser dans votre site web
# → Copier liste_des_flux/Viti.xml dans votre dossier web
# → Utiliser le code JavaScript ci-dessus
```

## 🔍 Vérification

Pour vérifier qu'un flux RSS contient les bonnes dates :

```bash
python verify_rss.py liste_des_flux/VOTRE_FICHIER.xml
```

Vous verrez :
- 📰 Nombre de bulletins
- 📅 Date de chaque bulletin
- 🔗 Liens complets
- 🏷️ Catégorie et auteur

## ❓ Questions Fréquentes

### Q: Aucun bulletin trouvé ?
**R:** Ajoutez des mots-clés personnalisés :
```bash
python create_rss_robust.py "URL" "fichier.xml" "bulletin,phyto,bsv"
```

### Q: Les dates sont toutes identiques ?
**R:** Le script n'a pas trouvé de dates dans la page. Vérifiez que les dates sont au format "22 juillet 2025".

### Q: Comment automatiser la mise à jour ?
**R:** Créez un fichier batch et planifiez-le avec le Planificateur de tâches Windows (voir section ci-dessus).

---

**🎉 C'est tout !** Votre flux RSS est prêt à être utilisé.
