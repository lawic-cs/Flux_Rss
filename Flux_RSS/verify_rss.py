#!/usr/bin/env python3
"""Vérifie le contenu d'un flux RSS"""
import xml.etree.ElementTree as ET
import sys

filename = sys.argv[1] if len(sys.argv) > 1 else 'liste_des_flux/Viticulture_Auvergne_2025.xml'

tree = ET.parse(filename)
root = tree.getroot()

# Infos du channel
channel = root.find('.//channel')
print("=" * 70)
print(f"📰 Flux RSS: {channel.find('title').text}")
print(f"🔗 Lien: {channel.find('link').text}")
print(f"📝 Description: {channel.find('description').text}")
print(f"🕐 Dernière MAJ: {channel.find('lastBuildDate').text}")
print("=" * 70)

# Liste des items
items = root.findall('.//item')
print(f"\n✅ Nombre total de bulletins: {len(items)}\n")

for i, item in enumerate(items, 1):
    title = item.find('title').text
    link = item.find('link').text
    pub_date = item.find('pubDate').text
    category = item.find('category')
    author = item.find('author')
    
    print(f"{i}. {title}")
    print(f"   📅 Date: {pub_date}")
    print(f"   🔗 URL: {link[:80]}...")
    if category is not None:
        print(f"   🏷️  Catégorie: {category.text}")
    if author is not None:
        print(f"   ✍️  Auteur: {author.text}")
    print()
