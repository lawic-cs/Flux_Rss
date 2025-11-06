#!/usr/bin/env python3
"""test_installation.py
Vérifie que toutes les dépendances sont installées correctement.
"""

import sys

def check_module(module_name, import_name=None):
    """Vérifie qu'un module peut être importé."""
    if import_name is None:
        import_name = module_name
    
    try:
        __import__(import_name)
        print(f"✅ {module_name:<20} installé")
        return True
    except ImportError:
        print(f"❌ {module_name:<20} MANQUANT")
        return False

def main():
    """Test d'installation des dépendances."""
    print("=" * 60)
    print("  🔍 Vérification des Dépendances")
    print("=" * 60)
    print()
    
    modules = [
        ('beautifulsoup4', 'bs4'),
        ('requests', 'requests'),
        ('lxml', 'lxml'),
        ('openpyxl', 'openpyxl'),
    ]
    
    results = []
    for module_name, import_name in modules:
        results.append(check_module(module_name, import_name))
    
    print()
    print("=" * 60)
    
    if all(results):
        print("✅ Toutes les dépendances sont installées !")
        print()
        print("Vous pouvez maintenant utiliser :")
        print("  python create_rss_robust.py")
        return 0
    else:
        print("❌ Des dépendances sont manquantes")
        print()
        print("Pour les installer, exécutez :")
        print("  pip install -r requirements.txt")
        print()
        print("Ou individuellement :")
        for i, (module_name, _) in enumerate(modules):
            if not results[i]:
                print(f"  pip install {module_name}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
