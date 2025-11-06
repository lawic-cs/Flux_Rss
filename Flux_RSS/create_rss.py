#!/usr/bin/env python3
"""create_rss.py
Peut fonctionner en mode interactif (une URL) ou batch à partir d'un fichier
.xlsx (col A = URL, col B = nom du fichier) ou .csv.

Si vous voulez traiter un seul URL, laissez vide le chemin de fichier
à l'invite et saisissez l'URL puis le nom du fichier de sortie.
"""

import sys
import os
import urllib.request
import urllib.error
from urllib.parse import urlparse
import re
import html
import xml.etree.ElementTree as ET
from datetime import datetime
import time
import email.utils
import csv
import traceback
import locale
from hashlib import md5

try:
    import openpyxl
    _HAS_OPENPYXL = True
except Exception:
    _HAS_OPENPYXL = False


def fetch(url, timeout=15):
    headers = {'User-Agent': 'Mozilla/5.0 (python)'}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        # essayer à partir des en-têtes, sinon utf-8
        charset = None
        try:
            charset = resp.headers.get_content_charset()
        except Exception:
            charset = None
        data = resp.read()
        charset = charset or 'utf-8'
        return data.decode(charset, errors='replace')


def extract_title(html_text):
    m = re.search(r'<title[^>]*>(.*?)</title>', html_text, re.I | re.S)
    if m:
        return html.unescape(m.group(1).strip())
    m = re.search(r"<meta[^>]+property=[\"']og:title[\"'][^>]*content=[\"'](.*?)[\"']", html_text, re.I | re.S)
    if m:
        return html.unescape(m.group(1).strip())
    return None


def extract_description(html_text):
    m = re.search(r"<meta[^>]+name=[\"']description[\"'][^>]*content=[\"'](.*?)[\"']", html_text, re.I | re.S)
    if m:
        return html.unescape(m.group(1).strip())
    m = re.search(r"<meta[^>]+property=[\"']og:description[\"'][^>]*content=[\"'](.*?)[\"']", html_text, re.I | re.S)
    if m:
        return html.unescape(m.group(1).strip())
    return ''


def extract_pub_date(html_text, url=''):
    """
    Extrait la date de publication depuis la page HTML.
    Cherche dans les métadonnées, les balises time, ou le contenu textuel.
    Retourne un string au format RFC 822 ou None.
    """
    # 1. Chercher dans les métadonnées Open Graph ou article:published_time
    patterns = [
        r"<meta[^>]+property=[\"']article:published_time[\"'][^>]*content=[\"'](.*?)[\"']",
        r"<meta[^>]+name=[\"']published[\"'][^>]*content=[\"'](.*?)[\"']",
        r"<meta[^>]+name=[\"']date[\"'][^>]*content=[\"'](.*?)[\"']",
    ]
    for pat in patterns:
        m = re.search(pat, html_text, re.I | re.S)
        if m:
            date_str = m.group(1).strip()
            parsed = parse_date_string(date_str)
            if parsed:
                return parsed
    
    # 2. Chercher une balise <time datetime="...">
    m = re.search(r'<time[^>]+datetime=["\']([^"\']+)["\']', html_text, re.I)
    if m:
        date_str = m.group(1).strip()
        parsed = parse_date_string(date_str)
        if parsed:
            return parsed
    
    # 3. Chercher dans le contenu : dates au format français (ex: "22 juillet 2025", "17/07/2025")
    # Exemple pour les pages DRAAF qui affichent souvent "BSV ... du 22 juillet 2025"
    m = re.search(r'\b(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})\b', 
                  html_text, re.I)
    if m:
        day, month_fr, year = m.groups()
        parsed = parse_french_date(day, month_fr, year)
        if parsed:
            return parsed
    
    # 4. Chercher format dd/mm/yyyy ou dd-mm-yyyy
    m = re.search(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b', html_text)
    if m:
        day, month, year = m.groups()
        parsed = parse_date_string(f"{year}-{month.zfill(2)}-{day.zfill(2)}")
        if parsed:
            return parsed
    
    # 5. Si rien trouvé, retourner None (sera remplacé par la date actuelle dans process_single)
    return None


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


def parse_date_string(date_str):
    """
    Tente de parser une date string dans différents formats.
    Retourne un string RFC 822 ou None.
    """
    # Formats ISO 8601
    formats = [
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d',
        '%d/%m/%Y',
        '%d-%m-%Y',
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return email.utils.formatdate(dt.timestamp(), usegmt=True)
        except Exception:
            continue
    
    # Essayer de parser avec email.utils directement (format RFC 822)
    try:
        parsed = email.utils.parsedate_to_datetime(date_str)
        return email.utils.formatdate(parsed.timestamp(), usegmt=True)
    except Exception:
        pass
    
    return None


def extract_category(html_text, url=''):
    """Extrait la catégorie/thème de l'article (ex: Viticulture, Grandes Cultures...)."""
    # Chercher dans les métadonnées
    m = re.search(r"<meta[^>]+property=[\"']article:section[\"'][^>]*content=[\"'](.*?)[\"']", html_text, re.I)
    if m:
        return html.unescape(m.group(1).strip())
    
    m = re.search(r"<meta[^>]+name=[\"']category[\"'][^>]*content=[\"'](.*?)[\"']", html_text, re.I)
    if m:
        return html.unescape(m.group(1).strip())
    
    # Chercher dans l'URL ou le titre (ex: "BSV Viticulture...")
    if 'viticulture' in url.lower() or 'viticulture' in html_text[:2000].lower():
        return 'Viticulture'
    if 'grandes cultures' in html_text[:2000].lower():
        return 'Grandes Cultures'
    
    return None


def extract_author(html_text, url=''):
    """Extrait l'auteur ou l'organisme (ex: DRAAF)."""
    m = re.search(r"<meta[^>]+name=[\"']author[\"'][^>]*content=[\"'](.*?)[\"']", html_text, re.I)
    if m:
        return html.unescape(m.group(1).strip())
    
    # Détecter "DRAAF" dans le contenu ou l'URL
    if 'draaf' in url.lower():
        return 'DRAAF Auvergne-Rhône-Alpes'
    
    return None


def make_rss(channel_title, channel_link, channel_desc, items):
    rss = ET.Element('rss', version='2.0')
    channel = ET.SubElement(rss, 'channel')
    ET.SubElement(channel, 'title').text = channel_title
    ET.SubElement(channel, 'link').text = channel_link
    ET.SubElement(channel, 'description').text = channel_desc
    ET.SubElement(channel, 'lastBuildDate').text = email.utils.formatdate(time.time(), usegmt=True)

    for it in items:
        item = ET.SubElement(channel, 'item')
        ET.SubElement(item, 'title').text = it.get('title')
        ET.SubElement(item, 'link').text = it.get('link')
        ET.SubElement(item, 'description').text = it.get('description')
        if it.get('pubDate'):
            ET.SubElement(item, 'pubDate').text = it.get('pubDate')
        if it.get('category'):
            ET.SubElement(item, 'category').text = it.get('category')
        if it.get('author'):
            ET.SubElement(item, 'author').text = it.get('author')
        if it.get('guid'):
            ET.SubElement(item, 'guid').text = it.get('guid')

    # serialiser
    return ET.tostring(rss, encoding='utf-8', xml_declaration=True)


def safe_filename(name):
    # retire caractères invalides pour nom de fichier
    name = name.strip()
    # remplacer espaces et slash par underscore
    name = re.sub(r'[\\/:*?"<>|\s]+', '_', name)
    if not name.lower().endswith('.xml'):
        name = name + '.xml'
    return name


def process_single(url, outname=None):
    if not url:
        return False, 'URL vide'
    if not urlparse(url).scheme:
        url = 'http://' + url
    try:
        page = fetch(url)
    except urllib.error.HTTPError as e:
        return False, f'HTTP {e.code} {e.reason}'
    except urllib.error.URLError as e:
        return False, f'Network {e}'
    except Exception as e:
        return False, str(e)

    title = extract_title(page) or url
    desc = extract_description(page) or title
    
    # Extraire la date de publication (ou utiliser la date actuelle si non trouvée)
    pubDate = extract_pub_date(page, url)
    if not pubDate:
        pubDate = email.utils.formatdate(time.time(), usegmt=True)
    
    # Extraire des infos supplémentaires
    category = extract_category(page, url)
    author = extract_author(page, url)
    
    # Générer un GUID unique basé sur l'URL
    guid = md5(url.encode('utf-8')).hexdigest()

    items = [{
        'title': title, 
        'link': url, 
        'description': desc, 
        'pubDate': pubDate,
        'category': category,
        'author': author,
        'guid': guid
    }]

    if not outname:
        # construire un nom de fichier depuis le domaine
        parsed = urlparse(url)
        dom = parsed.netloc or 'feed'
        outname = dom
    # créer le dossier de sortie `liste_des_flux` à côté du script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    outdir = os.path.join(base_dir, 'liste_des_flux')
    try:
        os.makedirs(outdir, exist_ok=True)
    except Exception:
        # si impossible de créer le dossier, on continue et écrira dans le dossier courant
        outdir = os.getcwd()

    outname = safe_filename(outname)
    outname = os.path.join(outdir, outname)

    rss_bytes = make_rss(title, url, desc, items)
    try:
        with open(outname, 'wb') as f:
            f.write(rss_bytes)
    except Exception as e:
        return False, f'Impossible d\'ecrire {outname}: {e}'

    return True, outname


def read_csv(path):
    rows = []
    with open(path, newline='', encoding='utf-8') as fh:
        rdr = csv.reader(fh)
        for r in rdr:
            if not r:
                continue
            url = r[0].strip() if len(r) > 0 else ''
            name = r[1].strip() if len(r) > 1 else ''
            rows.append((url, name))
    return rows


def read_xlsx(path):
    if not _HAS_OPENPYXL:
        raise RuntimeError('openpyxl non installé - installez avec: pip install openpyxl')
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = []
    for row in ws.iter_rows(min_row=1, values_only=True):
        if not row:
            continue
        url = (row[0] or '').strip() if len(row) > 0 else ''
        name = (row[1] or '').strip() if len(row) > 1 else ''
        rows.append((url, name))
    return rows


def main():
    # Accept an optional command-line argument: path to .xlsx/.csv list file.
    listpath = None
    if len(sys.argv) > 1:
        listpath = sys.argv[1]
    else:
        try:
            listpath = input("Chemin vers fichier .xlsx/.csv (laisser vide pour URL unique) : ").strip()
        except (EOFError, KeyboardInterrupt):
            print('\nAbandon.')
            sys.exit(1)

    tasks = []
    if listpath:
        listpath = os.path.expanduser(listpath)
        if not os.path.exists(listpath):
            print('Le fichier fourni n\'existe pas:', listpath)
            sys.exit(1)
        ext = os.path.splitext(listpath)[1].lower()
        try:
            if ext == '.csv':
                tasks = read_csv(listpath)
            elif ext in ('.xlsx',):
                tasks = read_xlsx(listpath)
            else:
                print('Extension non supportée. Utilisez .xlsx ou .csv')
                sys.exit(1)
        except Exception as e:
            print('Impossible de lire le fichier:', e)
            sys.exit(1)
    else:
        try:
            url = input("Entrez l'URL de la page à inclure dans le flux RSS: ").strip()
        except (EOFError, KeyboardInterrupt):
            print('\nAbandon.')
            sys.exit(1)
        if not url:
            print('Aucune URL fournie. Fin.')
            sys.exit(1)
        outname = input("Nom du fichier de sortie (par défaut 'feed.xml'): ").strip() or 'feed.xml'
        tasks = [(url, outname)]

    summary = {'ok': [], 'failed': []}
    for i, (url, name) in enumerate(tasks, start=1):
        if not url:
            summary['failed'].append((i, url, 'URL vide'))
            continue
        try:
            ok, info = process_single(url, name)
            if ok:
                summary['ok'].append((i, url, info))
                print(f'[{i}] OK -> {info}')
            else:
                summary['failed'].append((i, url, info))
                print(f'[{i}] ERREUR -> {info}')
        except Exception:
            summary['failed'].append((i, url, 'Exception'))
            print(f'[{i}] Exception lors du traitement de {url}:')
            traceback.print_exc()

    print('\nRésumé:')
    print(f"  Traités : {len(summary['ok'])}")
    print(f"  Échecs  : {len(summary['failed'])}")
    if summary['failed']:
        print('Détails des échecs:')
        for f in summary['failed']:
            print(' ', f)


if __name__ == '__main__':
    main()
