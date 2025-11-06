#!/usr/bin/env python3
"""compare_scripts.py
Compare les performances et résultats des différents scripts de génération RSS.
"""

import os
import time
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime

def analyze_rss_file(filepath):
    """Analyse un fichier RSS et retourne des statistiques."""
    if not os.path.exists(filepath):
        return None
    
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        channel = root.find('.//channel')
        items = root.findall('.//item')
        
        # Compter les items avec dates réelles (pas la date du jour)
        today = datetime.now().date()
        items_with_real_dates = 0
        
        for item in items:
            pub_date = item.find('pubDate')
            if pub_date is not None:
                try:
                    from email.utils import parsedate_to_datetime
                    date_obj = parsedate_to_datetime(pub_date.text).date()
                    if date_obj != today:
                        items_with_real_dates += 1
                except Exception:
                    pass
        
        return {
            'title': channel.find('title').text if channel.find('title') is not None else 'N/A',
            'total_items': len(items),
            'items_with_real_dates': items_with_real_dates,
            'has_category': any(item.find('category') is not None for item in items),
            'has_author': any(item.find('author') is not None for item in items),
            'file_size': os.path.getsize(filepath)
        }
    except Exception as e:
        return {'error': str(e)}


def run_script(script_name, url, output_file):
    """Exécute un script et mesure le temps d'exécution."""
    start = time.time()
    try:
        result = subprocess.run(
            ['python', script_name, url, output_file],
            capture_output=True,
            text=True,
            timeout=30
        )
        elapsed = time.time() - start
        return {
            'success': result.returncode == 0,
            'elapsed': elapsed,
            'output': result.stdout,
            'error': result.stderr
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'elapsed': 30,
            'error': 'Timeout (30s)'
        }
    except Exception as e:
        return {
            'success': False,
            'elapsed': time.time() - start,
            'error': str(e)
        }


def main():
    """Compare les trois scripts."""
    print("=" * 70)
    print("  📊 Comparaison des Scripts de Génération RSS")
    print("=" * 70)
    print()
    
    # URL de test
    test_url = "https://draaf.auvergne-rhone-alpes.agriculture.gouv.fr/viticulture-auvergne-2025-r1445.html"
    
    scripts = [
        {
            'name': 'create_rss_from_index.py',
            'output': 'test_regex.xml',
            'label': 'Version Regex',
            'emoji': '🔤'
        },
        {
            'name': 'create_rss_robust.py',
            'output': 'test_robust.xml',
            'label': 'Version Robuste (BeautifulSoup)',
            'emoji': '🛡️'
        }
    ]
    
    results = []
    
    for script in scripts:
        print(f"{script['emoji']} Test : {script['label']}")
        print(f"   Script : {script['name']}")
        
        # Exécuter le script
        exec_result = run_script(script['name'], test_url, script['output'])
        
        if exec_result['success']:
            print(f"   ✅ Succès en {exec_result['elapsed']:.2f}s")
            
            # Analyser le fichier RSS généré
            rss_path = os.path.join('liste_des_flux', script['output'])
            stats = analyze_rss_file(rss_path)
            
            if stats and 'error' not in stats:
                print(f"   📰 {stats['total_items']} bulletin(s) trouvé(s)")
                print(f"   📅 {stats['items_with_real_dates']} avec dates réelles")
                print(f"   🏷️  Catégorie : {'Oui' if stats['has_category'] else 'Non'}")
                print(f"   ✍️  Auteur : {'Oui' if stats['has_author'] else 'Non'}")
                print(f"   💾 Taille : {stats['file_size']:,} octets")
                
                results.append({
                    'script': script['label'],
                    'success': True,
                    'elapsed': exec_result['elapsed'],
                    **stats
                })
            else:
                print(f"   ⚠️  Erreur d'analyse : {stats.get('error', 'Inconnue')}")
                results.append({
                    'script': script['label'],
                    'success': False,
                    'error': stats.get('error', 'Analyse impossible')
                })
        else:
            print(f"   ❌ Échec : {exec_result.get('error', 'Erreur inconnue')}")
            results.append({
                'script': script['label'],
                'success': False,
                'error': exec_result.get('error', 'Erreur inconnue')
            })
        
        print()
    
    # Résumé comparatif
    print("=" * 70)
    print("  📊 Résumé Comparatif")
    print("=" * 70)
    print()
    
    successful_results = [r for r in results if r.get('success')]
    
    if successful_results:
        print(f"{'Script':<40} {'Items':<8} {'Dates':<8} {'Temps':<10}")
        print("-" * 70)
        for r in successful_results:
            print(f"{r['script']:<40} {r.get('total_items', 'N/A'):<8} "
                  f"{r.get('items_with_real_dates', 'N/A'):<8} "
                  f"{r.get('elapsed', 0):.2f}s")
        print()
        
        # Recommandation
        best = max(successful_results, 
                   key=lambda x: (x.get('items_with_real_dates', 0), 
                                  x.get('total_items', 0),
                                  -x.get('elapsed', 999)))
        
        print("🏆 Recommandation :")
        print(f"   {best['script']} offre les meilleurs résultats")
        print(f"   ({best.get('items_with_real_dates', 0)} bulletins avec dates réelles)")
    else:
        print("⚠️  Aucun script n'a réussi à générer un flux valide.")
    
    print()


if __name__ == '__main__':
    main()
