#!/usr/bin/env python3

"""
This script updates only market/item icons.
"""


import argparse
import os
import re
import sqlite3

from PIL import Image


parser = argparse.ArgumentParser(description='This script updates module icons for pyfa')
parser.add_argument('-i', '--icons', required=True, type=str, help='path to unpacked Icons folder from CCP\'s image export')
args = parser.parse_args()


script_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.abspath(os.path.join(script_dir, '..', 'staticdata', 'eve.db'))
icons_dir = os.path.abspath(os.path.join(script_dir, '..', 'staticdata', 'icons'))
export_dir = os.path.abspath(os.path.expanduser(os.path.join(args.icons, 'items')))


db = sqlite3.connect(db_path)
cursor = db.cursor()

ICON_SIZE = (16, 16)

ITEM_CATEGORIES = (
    6,  # Ship
    7,  # Module
    8,  # Charge
    16,  # Skill
    18,  # Drone
    20,  # Implant
    32  # Subsystem
)
MARKET_ROOTS = {
    9,  # Modules
    1111,  # Rigs
    157,  # Drones
    11,  # Ammo
    1112,  # Subsystems
    24,  # Implants & Boosters
    404  # Deployables
}

# Add children to market group list
# {parent: {children}}
mkt_tree = {}
for row in cursor.execute('select marketGroupID, parentGroupID from invmarketgroups'):
    parent = row[1]
    # We have all the root groups in the set we need anyway
    if not parent:
        continue
    child = row[0]
    children = mkt_tree.setdefault(parent, set())
    children.add(child)

# Traverse the tree we just composed to add all children for all needed roots
def get_children(parent):
    children = set()
    for child in mkt_tree.get(parent, ()):
        children.add(child)
        children.update(get_children(child))
    return children


market_groups = set()
for root in MARKET_ROOTS:
    market_groups.add(root)
    market_groups.update(get_children(root))


query_items = 'select distinct i.iconFile from icons as i inner join invtypes as it on it.iconID = i.iconID inner join invgroups as ig on it.groupID = ig.groupID where ig.categoryID in ({})'.format(', '.join(str(i) for i in ITEM_CATEGORIES))
query_groups = 'select distinct i.iconFile from icons as i inner join invgroups as ig on ig.iconID = i.iconID where ig.categoryID in ({})'.format(', '.join(str(i) for i in ITEM_CATEGORIES))
query_cats = 'select distinct i.iconFile from icons as i inner join invcategories as ic on ic.iconID = i.iconID where ic.categoryID in ({})'.format(', '.join(str(i) for i in ITEM_CATEGORIES))
query_market = 'select distinct i.iconFile from icons as i inner join invmarketgroups as img on img.iconID = i.iconID where img.marketGroupID in ({})'.format(', '.join(str(i) for i in market_groups))
query_attrib = 'select distinct i.iconFile from icons as i inner join dgmattribs as da on da.iconID = i.iconID'


needed = set()
existing = set()
export = {}


def strip_path(fname):
    """
    Here we extract 'core' of icon name. Path and
    extension are sometimes specified in database
    but we don't need them.
    """
    # Path before the icon file name
    fname = fname.split('/')[-1]
    # Extension
    fname = fname.rsplit('.', 1)[0]
    return fname


def unzero(fname):
    """
    Get rid of leading zeros in triplet. They are often specified in DB
    but almost never in actual files.
    """
    m = re.match(r'^(?P<prefix>[^_\.]+)_((?P<size>\d+)_)?(?P<suffix>[^_\.]+)(?P<tail>\..*)?$', fname)
    if m:
        prefix = m.group('prefix')
        size = m.group('size')
        suffix = m.group('suffix')
        tail = m.group('tail')
        try:
            prefix = int(prefix)
        except (TypeError, ValueError):
            pass
        try:
            size = int(size)
        except (TypeError, ValueError):
            pass
        try:
            suffix = int(suffix)
        except (TypeError, ValueError):
            pass
        if size is None:
            fname = '{}_{}{}'.format(prefix, suffix, tail)
        else:
            fname = '{}_{}_{}{}'.format(prefix, size, suffix, tail)
        return fname
    else:
        return fname

for query in (query_items, query_groups, query_cats, query_market, query_attrib):
    for row in cursor.execute(query):
        fname = row[0]
        if not fname:
            continue
        fname = strip_path(fname)
        needed.add(fname)

for fname in os.listdir(icons_dir):
    if not os.path.isfile(os.path.join(icons_dir, fname)):
        continue
    if not fname.startswith('icon') or not fname.endswith('.png'):
        continue
    fname = strip_path(fname)
    # Get rid of "icon" prefix as well
    fname = re.sub('^icon', '', fname)
    existing.add(fname)


for fname in os.listdir(export_dir):
    if not os.path.isfile(os.path.join(export_dir, fname)):
        continue
    stripped = strip_path(fname)
    stripped = unzero(stripped)
    # Icons in export often specify size in their name, but references often use
    # convention without size specification
    sizeless = re.sub('^(?P<prefix>[^_]+)_(?P<size>\d+)_(?P<suffix>[^_]+)$', r'\1_\3', stripped)
    # Often items referred to with 01_01 format,
    fnames = export.setdefault(stripped, set())
    fnames.add(fname)
    fnames = export.setdefault(sizeless, set())
    fnames.add(fname)


def get_icon_file(request):
    """
    Get the iconFile field value and find proper
    icon for it. Return as PIL image object down-
    scaled for use in pyfa.
    """
    rq = strip_path(request)
    rq = unzero(rq)
    try:
        fnames = export[rq]
    except KeyError:
        return None
    # {(h, w): source full path}
    sizes = {}
    for fname in fnames:
        fullpath = os.path.join(export_dir, fname)
        img = Image.open(fullpath)
        sizes[img.size] = fullpath
    # Try to return image which is already in necessary format
    try:
        fullpath = sizes[ICON_SIZE]
    # Otherwise, convert biggest image
    except KeyError:
        fullpath = sizes[max(sizes)]
        img = Image.open(fullpath)
        img.thumbnail(ICON_SIZE, Image.ANTIALIAS)
    else:
        img = Image.open(fullpath)
    return img


toremove = existing.difference(needed)
toupdate = existing.intersection(needed)
toadd = needed.difference(existing)


if toremove:
    print('Some icons are not used and will be removed:')
    for fname in sorted(toremove):
        fullname = 'icon{}.png'.format(fname)
        print('  {}'.format(fullname))
        fullpath = os.path.join(icons_dir, fullname)
        os.remove(fullpath)

if toupdate:
    print('Updating {} icons...'.format(len(toupdate)))
    missing = set()
    for fname in sorted(toupdate):
        icon = get_icon_file(fname)
        if icon is None:
            missing.add(fname)
            continue
        fullname = 'icon{}.png'.format(fname)
        fullpath = os.path.join(icons_dir, fullname)
        icon.save(fullpath, 'PNG')
    if missing:
        print('  {} icons are missing in export:'.format(len(missing)))
        for fname in sorted(missing):
            print('    {}'.format(fname))

if toadd:
    print('Adding {} icons...'.format(len(toadd)))
    missing = set()
    for fname in sorted(toadd):
        icon = get_icon_file(fname)
        if icon is None:
            missing.add(fname)
            continue
        fullname = 'icon{}.png'.format(fname)
        fullpath = os.path.join(icons_dir, fullname)
        icon.save(fullpath, 'PNG')
    if missing:
        print('  {} icons are missing in export:'.format(len(missing)))
        for fname in sorted(missing):
            print('    {}'.format(fname))
