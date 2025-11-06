#!/usr/bin/env python3
"""create_rss_from_index.py
Parse une page index DRAAF (ex: liste de bulletins BSV) et génère un flux RSS
complet avec tous les bulletins et leurs dates réelles extraites de la page.

Usage:
    python create_rss_from_index.py
    Ou:
    python create_rss_from_index.py <URL_page_index> <nom_fichier_sortie>
"""

import sys
import os
import urllib.request
import urllib.error
from urllib.parse import urlparse, urljoin
import re
import html
import xml.etree.ElementTree as ET
from datetime import datetime
import time
import email.utils
from hashlib import md5


def fetch(url, timeout=15):
    """Récupère le contenu HTML d'une URL."""
    headers = {'User-Agent': 'Mozilla/5.0 (python)'}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = None
        try:
            charset = resp.headers.get_content_charset()
        except Exception:
            charset = None
        data = resp.read()
        charset = charset or 'utf-8'
        return data.decode(charset, errors='replace')


def parse_french_date(day, month_fr, year):
    """Convertit une date française (22 juillet 2025) en format RFC 822."""
    months_fr = {
        'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4,
        'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8,
        'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12
    }
    try:
        month_num = months_fr.get(month_fr.lower())
        if not month_num:
            return None
        dt = datetime(int(year), month_num, int(day))
        return email.utils.formatdate(dt.timestamp(), usegmt=True)
    except Exception:
        return None


def extract_bulletins_from_index(html_text, base_url):
    """
    Parse une page index DRAAF et extrait tous les bulletins.
    Retourne une liste de dict avec: title, link, description, pubDate
    """
    bulletins = []
    seen_urls = set()  # Pour éviter les doublons
    
    # Chercher tous les liens contenant des bulletins BSV
    # Format typique: <a href="bsv-viticulture-auvergne-no16-du-22-juillet-2025-a6266.html">
    #                   BSV Viticulture Auvergne N°16 du 22 juillet 2025</a>
    
    link_pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]*BSV[^<]*)</a>'
    matches = re.findall(link_pattern, html_text, re.I)
    
    for link, title_html in matches:
        # Nettoyer le titre (retirer les entités HTML comme &deg;)
        clean_title = html.unescape(title_html).strip()
        
        # Filtrer les liens de navigation/breadcrumb
        if len(clean_title) < 15:  # Trop court, probablement un lien de menu
            continue
        
        if any(nav in clean_title.lower() for nav in ['accéder', 'menu', 'recherche', 'fil d\'arianne']):
            continue
        
        # Construire l'URL complète
        full_url = urljoin(base_url, link)
        
        # Éviter les doublons
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)
        
        # Extraire la date depuis le titre
        # Format: "BSV Viticulture Auvergne N°16 du 22 juillet 2025"
        date_match = re.search(r'\bdu\s+(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})', 
                              clean_title, re.I)
        
        if date_match:
            day, month_fr, year = date_match.groups()
            pub_date = parse_french_date(day, month_fr, year)
        else:
            # Essayer de chercher dans le contexte autour du lien
            link_pos = html_text.find(link)
            if link_pos != -1:
                context_start = max(0, link_pos - 300)
                context_end = min(len(html_text), link_pos + 300)
                context = html_text[context_start:context_end]
                
                context_date_match = re.search(r'(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})', 
                                              context, re.I)
                if context_date_match:
                    day, month_fr, year = context_date_match.groups()
                    pub_date = parse_french_date(day, month_fr, year)
                else:
                    pub_date = email.utils.formatdate(time.time(), usegmt=True)
            else:
                pub_date = email.utils.formatdate(time.time(), usegmt=True)
        
        bulletins.append({
            'title': clean_title,
            'link': full_url,
            'description': clean_title,
            'pubDate': pub_date,
            'guid': md5(full_url.encode('utf-8')).hexdigest()
        })
    
    # Trier par date (plus récent en premier)
    if bulletins:
        bulletins.sort(key=lambda x: email.utils.parsedate_to_datetime(x['pubDate']), reverse=True)
    
    return bulletins


def extract_page_info(html_text, url):
    """Extrait le titre et la description de la page index."""
    # Titre
    title_match = re.search(r'<title[^>]*>(.*?)</title>', html_text, re.I | re.S)
    title = html.unescape(title_match.group(1).strip()) if title_match else 'Bulletins DRAAF'
    
    # Description
    desc_match = re.search(r"<meta[^>]+name=[\"']description[\"'][^>]*content=[\"'](.*?)[\"']", html_text, re.I)
    description = html.unescape(desc_match.group(1).strip()) if desc_match else title
    
    return title, description


def make_rss(channel_title, channel_link, channel_desc, items, author=None, category=None):
    """Génère le XML RSS avec tous les items."""
    rss = ET.Element('rss', version='2.0')
    channel = ET.SubElement(rss, 'channel')
    ET.SubElement(channel, 'title').text = channel_title
    ET.SubElement(channel, 'link').text = channel_link
    ET.SubElement(channel, 'description').text = channel_desc
    ET.SubElement(channel, 'lastBuildDate').text = email.utils.formatdate(time.time(), usegmt=True)
    
    if category:
        ET.SubElement(channel, 'category').text = category
    
    for it in items:
        item = ET.SubElement(channel, 'item')
        ET.SubElement(item, 'title').text = it.get('title')
        ET.SubElement(item, 'link').text = it.get('link')
        ET.SubElement(item, 'description').text = it.get('description')
        ET.SubElement(item, 'pubDate').text = it.get('pubDate')
        
        if author or it.get('author'):
            ET.SubElement(item, 'author').text = author or it.get('author')
        
        if category or it.get('category'):
            ET.SubElement(item, 'category').text = category or it.get('category')
        
        if it.get('guid'):
            ET.SubElement(item, 'guid').text = it.get('guid')
    
    return ET.tostring(rss, encoding='utf-8', xml_declaration=True)


def process_index_page(index_url, output_filename=None):
    """
    Traite une page index et génère un flux RSS complet.
    Retourne (success: bool, message: str)
    """
    print(f"📥 Récupération de la page: {index_url}")
    
    try:
        html_content = fetch(index_url)
    except Exception as e:
        return False, f"Erreur lors de la récupération: {e}"
    
    print(f"✅ Page récupérée ({len(html_content)} caractères)")
    
    # Extraire les informations de la page
    channel_title, channel_desc = extract_page_info(html_content, index_url)
    print(f"📋 Titre: {channel_title}")
    
    # Extraire tous les bulletins
    bulletins = extract_bulletins_from_index(html_content, index_url)
    print(f"📰 {len(bulletins)} bulletin(s) trouvé(s)")
    
    if not bulletins:
        return False, "Aucun bulletin trouvé sur cette page"
    
    # Afficher les bulletins trouvés
    for i, bull in enumerate(bulletins[:5], 1):  # Afficher les 5 premiers
        date_obj = email.utils.parsedate_to_datetime(bull['pubDate'])
        print(f"  {i}. {bull['title'][:60]}... ({date_obj.strftime('%d/%m/%Y')})")
    if len(bulletins) > 5:
        print(f"  ... et {len(bulletins) - 5} autres")
    
    # Déterminer la catégorie et l'auteur
    category = None
    if 'viticulture' in channel_title.lower():
        category = 'Viticulture'
    elif 'grandes cultures' in channel_title.lower():
        category = 'Grandes Cultures'
    
    author = None
    if 'draaf' in index_url.lower():
        author = 'DRAAF Auvergne-Rhône-Alpes'
    
    # Générer le RSS
    rss_content = make_rss(channel_title, index_url, channel_desc, bulletins, author, category)
    
    # Déterminer le nom du fichier de sortie
    if not output_filename:
        # Extraire un nom depuis l'URL
        parsed = urlparse(index_url)
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
    print("=" * 70)
    print("  Générateur de flux RSS depuis une page index DRAAF")
    print("=" * 70)
    print()
    
    # Récupérer l'URL et le nom de fichier
    if len(sys.argv) >= 2:
        index_url = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) >= 3 else None
    else:
        try:
            index_url = input("URL de la page index (liste des bulletins): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n❌ Abandon.")
            sys.exit(1)
        
        if not index_url:
            print("❌ Aucune URL fournie.")
            sys.exit(1)
        
        output_file = input("Nom du fichier de sortie (laisser vide pour auto): ").strip() or None
    
    # Ajouter http:// si nécessaire
    if not urlparse(index_url).scheme:
        index_url = 'https://' + index_url
    
    # Traiter la page
    success, message = process_index_page(index_url, output_file)
    
    print()
    if success:
        print(f"✅ SUCCÈS: {message}")
        print()
        print("💡 Vous pouvez maintenant utiliser ce flux RSS dans votre site web.")
        print("   Les bulletins sont triés par date (plus récent en premier).")
    else:
        print(f"❌ ERREUR: {message}")
        sys.exit(1)


if __name__ == '__main__':
    main()
