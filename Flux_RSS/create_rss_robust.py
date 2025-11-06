#!/usr/bin/env python3
"""create_rss_robust.py
Générateur de flux RSS robuste utilisant BeautifulSoup pour parser le HTML.
Fonctionne quelle que soit la structure HTML de la page.

Usage:
    python create_rss_robust.py
    python create_rss_robust.py <URL_page_index> <nom_fichier_sortie>
"""

import sys
import os
import re
import time
import email.utils
from datetime import datetime
from hashlib import md5
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

try:
    from bs4 import BeautifulSoup
    import requests
    _HAS_LIBS = True
except ImportError:
    _HAS_LIBS = False
    print("⚠️  Bibliothèques manquantes. Installation nécessaire :")
    print("    pip install beautifulsoup4 requests lxml")
    sys.exit(1)


def fetch_page(url, timeout=15):
    """Récupère une page web avec requests."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or 'utf-8'
        return response.text
    except requests.RequestException as e:
        raise Exception(f"Erreur lors de la récupération de {url}: {e}")


def parse_french_date(text):
    """
    Extrait et parse une date française depuis du texte.
    Retourne un timestamp ou None.
    """
    months_fr = {
        'janvier': 1, 'février': 2, 'fevrier': 2, 'mars': 3, 'avril': 4,
        'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8, 'aout': 8,
        'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12, 'decembre': 12
    }
    
    # Format: "22 juillet 2025" ou "du 22 juillet 2025"
    pattern = r'\b(\d{1,2})\s+(janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre)\s+(\d{4})\b'
    match = re.search(pattern, text.lower())
    
    if match:
        day, month_name, year = match.groups()
        month = months_fr.get(month_name.lower())
        if month:
            try:
                dt = datetime(int(year), month, int(day))
                return dt.timestamp()
            except ValueError:
                pass
    
    return None


def parse_date_from_multiple_sources(link_tag, context_text=''):
    """
    Essaie d'extraire une date depuis plusieurs sources.
    Retourne un string RFC 822 ou None.
    """
    # 1. Chercher dans l'attribut datetime d'une balise <time>
    time_tag = link_tag.find_parent().find('time') if link_tag.find_parent() else None
    if time_tag and time_tag.get('datetime'):
        try:
            dt_str = time_tag['datetime']
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            return email.utils.formatdate(dt.timestamp(), usegmt=True)
        except Exception:
            pass
    
    # 2. Chercher dans le texte du lien
    link_text = link_tag.get_text(strip=True)
    timestamp = parse_french_date(link_text)
    if timestamp:
        return email.utils.formatdate(timestamp, usegmt=True)
    
    # 3. Chercher dans le titre ou l'attribut title
    if link_tag.get('title'):
        timestamp = parse_french_date(link_tag['title'])
        if timestamp:
            return email.utils.formatdate(timestamp, usegmt=True)
    
    # 4. Chercher dans le contexte autour du lien (parent, siblings)
    if link_tag.parent:
        parent_text = link_tag.parent.get_text(strip=True)
        timestamp = parse_french_date(parent_text)
        if timestamp:
            return email.utils.formatdate(timestamp, usegmt=True)
    
    # 5. Chercher dans le contexte fourni
    if context_text:
        timestamp = parse_french_date(context_text)
        if timestamp:
            return email.utils.formatdate(timestamp, usegmt=True)
    
    return None


def extract_bulletins_smart(html_content, base_url, keywords=None):
    """
    Extrait intelligemment les bulletins d'une page HTML.
    
    Args:
        html_content: Contenu HTML de la page
        base_url: URL de base pour construire les liens absolus
        keywords: Liste de mots-clés à rechercher (ex: ['bsv', 'bulletin'])
    
    Returns:
        Liste de dict avec title, link, description, pubDate, guid
    """
    if keywords is None:
        keywords = ['bsv', 'bulletin']
    
    soup = BeautifulSoup(html_content, 'lxml')
    bulletins = []
    seen_urls = set()
    
    # Chercher tous les liens
    for link_tag in soup.find_all('a', href=True):
        href = link_tag['href']
        text = link_tag.get_text(strip=True)
        
        # Filtrer : garder seulement les liens pertinents
        is_relevant = False
        
        # Vérifier si le texte ou l'URL contient un mot-clé
        for keyword in keywords:
            if keyword.lower() in text.lower() or keyword.lower() in href.lower():
                is_relevant = True
                break
        
        if not is_relevant:
            continue
        
        # Filtrer les liens de navigation/système
        if len(text) < 10:
            continue
        
        skip_keywords = ['accéder', 'menu', 'recherche', 'footer', 'partager', 
                        'imprimer', 'télécharger', 'retour', 'suivant', 'précédent']
        if any(skip in text.lower() for skip in skip_keywords):
            continue
        
        # Construire l'URL absolue
        full_url = urljoin(base_url, href)
        
        # Éviter les doublons
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)
        
        # Extraire la date
        pub_date = parse_date_from_multiple_sources(link_tag)
        if not pub_date:
            # Par défaut : date actuelle
            pub_date = email.utils.formatdate(time.time(), usegmt=True)
        
        # Créer le bulletin
        bulletins.append({
            'title': text,
            'link': full_url,
            'description': text,
            'pubDate': pub_date,
            'guid': md5(full_url.encode('utf-8')).hexdigest()
        })
    
    # Trier par date (plus récent en premier)
    bulletins.sort(
        key=lambda x: email.utils.parsedate_to_datetime(x['pubDate']), 
        reverse=True
    )
    
    return bulletins


def extract_page_metadata(html_content, url):
    """Extrait le titre et la description de la page."""
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Titre
    title = None
    title_tag = soup.find('title')
    if title_tag:
        title = title_tag.get_text(strip=True)
    
    # Si pas de titre, chercher dans og:title
    if not title:
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            title = og_title['content']
    
    if not title:
        title = 'Bulletins RSS'
    
    # Description
    description = title
    desc_tag = soup.find('meta', attrs={'name': 'description'})
    if desc_tag and desc_tag.get('content'):
        description = desc_tag['content']
    else:
        og_desc = soup.find('meta', property='og:description')
        if og_desc and og_desc.get('content'):
            description = og_desc['content']
    
    return title, description


def detect_category(html_content, url):
    """Détecte automatiquement la catégorie du flux."""
    text = html_content.lower()
    url_lower = url.lower()
    
    if 'viticulture' in text[:2000] or 'viticulture' in url_lower:
        return 'Viticulture'
    elif 'grandes cultures' in text[:2000]:
        return 'Grandes Cultures'
    elif 'arboriculture' in text[:2000] or 'arboriculture' in url_lower:
        return 'Arboriculture'
    elif 'maraîchage' in text[:2000] or 'maraichage' in text[:2000]:
        return 'Maraîchage'
    
    return None


def detect_author(html_content, url):
    """Détecte l'auteur ou l'organisme."""
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Chercher dans les métadonnées
    author_tag = soup.find('meta', attrs={'name': 'author'})
    if author_tag and author_tag.get('content'):
        return author_tag['content']
    
    # Détecter depuis l'URL ou le contenu
    url_lower = url.lower()
    if 'draaf' in url_lower or 'agriculture.gouv.fr' in url_lower:
        # Détecter la région
        if 'auvergne' in url_lower or 'rhone-alpes' in url_lower:
            return 'DRAAF Auvergne-Rhône-Alpes'
        return 'DRAAF'
    
    return None


def generate_rss(channel_title, channel_link, channel_desc, items, 
                 category=None, author=None):
    """Génère le XML RSS."""
    rss = ET.Element('rss', version='2.0')
    channel = ET.SubElement(rss, 'channel')
    
    ET.SubElement(channel, 'title').text = channel_title
    ET.SubElement(channel, 'link').text = channel_link
    ET.SubElement(channel, 'description').text = channel_desc
    ET.SubElement(channel, 'lastBuildDate').text = email.utils.formatdate(
        time.time(), usegmt=True
    )
    
    if category:
        ET.SubElement(channel, 'category').text = category
    
    for item_data in items:
        item = ET.SubElement(channel, 'item')
        ET.SubElement(item, 'title').text = item_data['title']
        ET.SubElement(item, 'link').text = item_data['link']
        ET.SubElement(item, 'description').text = item_data['description']
        ET.SubElement(item, 'pubDate').text = item_data['pubDate']
        ET.SubElement(item, 'guid').text = item_data['guid']
        
        if author or item_data.get('author'):
            ET.SubElement(item, 'author').text = author or item_data['author']
        
        if category or item_data.get('category'):
            ET.SubElement(item, 'category').text = category or item_data['category']
    
    return ET.tostring(rss, encoding='utf-8', xml_declaration=True)


def process_page_to_rss(page_url, output_filename=None, keywords=None):
    """
    Traite une page et génère un flux RSS.
    
    Args:
        page_url: URL de la page index
        output_filename: Nom du fichier de sortie
        keywords: Mots-clés pour filtrer les bulletins
    
    Returns:
        (success: bool, message: str)
    """
    print("=" * 70)
    print("  📡 Générateur de flux RSS robuste (BeautifulSoup)")
    print("=" * 70)
    print()
    print(f"📥 Récupération de la page: {page_url}")
    
    # Récupérer la page
    try:
        html_content = fetch_page(page_url)
        print(f"✅ Page récupérée ({len(html_content):,} caractères)")
    except Exception as e:
        return False, str(e)
    
    # Extraire les métadonnées
    title, description = extract_page_metadata(html_content, page_url)
    category = detect_category(html_content, page_url)
    author = detect_author(html_content, page_url)
    
    print(f"📋 Titre: {title}")
    if category:
        print(f"🏷️  Catégorie: {category}")
    if author:
        print(f"✍️  Auteur: {author}")
    
    # Extraire les bulletins
    bulletins = extract_bulletins_smart(html_content, page_url, keywords)
    print(f"📰 {len(bulletins)} bulletin(s) trouvé(s)")
    print()
    
    if not bulletins:
        return False, "Aucun bulletin trouvé sur cette page"
    
    # Afficher les bulletins trouvés
    for i, bull in enumerate(bulletins[:5], 1):
        date_obj = email.utils.parsedate_to_datetime(bull['pubDate'])
        print(f"  {i}. {bull['title'][:60]}...")
        print(f"     📅 {date_obj.strftime('%d/%m/%Y')}")
    
    if len(bulletins) > 5:
        print(f"  ... et {len(bulletins) - 5} autres")
    print()
    
    # Générer le RSS
    rss_content = generate_rss(title, page_url, description, bulletins, 
                               category, author)
    
    # Déterminer le nom du fichier
    if not output_filename:
        parsed = urlparse(page_url)
        path_parts = [p for p in parsed.path.split('/') if p]
        if path_parts:
            output_filename = path_parts[-1].replace('.html', '') + '.xml'
        else:
            output_filename = 'bulletins.xml'
    
    if not output_filename.endswith('.xml'):
        output_filename += '.xml'
    
    # Créer le dossier de sortie
    base_dir = os.path.dirname(os.path.abspath(__file__))
    outdir = os.path.join(base_dir, 'liste_des_flux')
    os.makedirs(outdir, exist_ok=True)
    
    output_path = os.path.join(outdir, output_filename)
    
    # Écrire le fichier
    with open(output_path, 'wb') as f:
        f.write(rss_content)
    
    print(f"💾 Flux RSS généré: {output_path}")
    return True, output_path


def main():
    """Point d'entrée principal."""
    # Récupérer les arguments
    if len(sys.argv) >= 2:
        page_url = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) >= 3 else None
        keywords = sys.argv[3].split(',') if len(sys.argv) >= 4 else None
    else:
        try:
            page_url = input("URL de la page index (liste des bulletins): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n❌ Abandon.")
            sys.exit(1)
        
        if not page_url:
            print("❌ Aucune URL fournie.")
            sys.exit(1)
        
        output_file = input("Nom du fichier de sortie (laisser vide pour auto): ").strip() or None
        keywords_input = input("Mots-clés à rechercher (séparés par des virgules, ex: bsv,bulletin) [bsv]: ").strip()
        keywords = keywords_input.split(',') if keywords_input else None
    
    # Ajouter https:// si nécessaire
    if not urlparse(page_url).scheme:
        page_url = 'https://' + page_url
    
    # Traiter la page
    success, message = process_page_to_rss(page_url, output_file, keywords)
    
    print()
    if success:
        print(f"✅ SUCCÈS: {message}")
        print()
        print("💡 Conseils d'utilisation :")
        print("   • Utilisez ce flux dans votre site web avec fetch() ou jQuery")
        print("   • Les bulletins sont triés par date (plus récent en premier)")
        print("   • Pour mettre à jour: relancez ce script régulièrement")
        print("   • Pour d'autres pages: python create_rss_robust.py <URL>")
    else:
        print(f"❌ ERREUR: {message}")
        sys.exit(1)


if __name__ == '__main__':
    main()
