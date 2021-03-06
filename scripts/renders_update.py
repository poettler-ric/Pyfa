#!/usr/bin/env python3

"""
This script updates ship renders and removes unused ones.
"""


import argparse
import os
import re
import sqlite3

from PIL import Image


parser = argparse.ArgumentParser(description='This script updates ship renders for pyfa')
parser.add_argument('-r', '--renders', required=True, type=str, help='path to unpacked Renders folder from CCP\'s image export')
args = parser.parse_args()


script_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.abspath(os.path.join(script_dir, '..', 'staticdata', 'eve.db'))
icons_dir = os.path.abspath(os.path.join(script_dir, '..', 'staticdata', 'icons', 'ships'))
export_dir = os.path.abspath(os.path.expanduser(args.renders))


db = sqlite3.connect(db_path)
cursor = db.cursor()

RENDER_SIZE = (32, 32)


query_ships = 'select it.typeID from invtypes as it inner join invgroups as ig on it.groupID = ig.groupID where ig.categoryID = 6'


needed = set()
existing = set()
export = set()


for row in cursor.execute(query_ships):
    needed.add(row[0])

for container, filedir in (
    (existing, icons_dir),
    (export, export_dir)
):
    for fname in os.listdir(filedir):
        if not os.path.isfile(os.path.join(filedir, fname)):
            continue
        m = re.match(r'^(?P<typeid>\d+)\.png', fname)
        if not m:
            continue
        container.add(int(m.group('typeid')))

toremove = existing.difference(needed)
toupdate = existing.intersection(needed)
toadd = needed.difference(existing)


def get_render(type_id):
    fname = '{}.png'.format(type_id)
    fullpath = os.path.join(export_dir, fname)
    img = Image.open(fullpath)
    if img.size != RENDER_SIZE:
        img.thumbnail(RENDER_SIZE, Image.ANTIALIAS)
    return img


if toremove:
    print('Some renders are not used and will be removed:')
    for type_id in sorted(toremove):
        fullname = '{}.png'.format(type_id)
        print('  {}'.format(fullname))
        fullpath = os.path.join(icons_dir, fullname)
        os.remove(fullpath)

if toupdate:
    print('Updating {} renders...'.format(len(toupdate)))
    missing = toupdate.difference(export)
    toupdate.intersection_update(export)
    for type_id in sorted(toupdate):
        render = get_render(type_id)
        fname = '{}.png'.format(type_id)
        fullpath = os.path.join(icons_dir, fname)
        render.save(fullpath, 'PNG')
    if missing:
        print('  {} renders are missing in export:'.format(len(missing)))
        for type_id in sorted(missing):
            print('    {}.png'.format(type_id))

if toadd:
    print('Adding {} renders...'.format(len(toadd)))
    missing = toadd.difference(export)
    toadd.intersection_update(export)
    for type_id in sorted(toadd):
        render = get_render(type_id)
        fname = '{}.png'.format(type_id)
        fullpath = os.path.join(icons_dir, fname)
        render.save(fullpath, 'PNG')
    if missing:
        print('  {} renders are missing in export:'.format(len(missing)))
        for type_id in sorted(missing):
            print('    {}.png'.format(type_id))
