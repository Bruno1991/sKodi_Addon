import re
import sys
sys.path.insert(0, 'addons/script.module.saile.epg/lib')
from saile_epg.providers.claro import CLARO_OFFICIAL_CHANNELS
from saile_epg.normalizer import clean_channel_title, get_canonical_channel_name, normalize_channel_name
from saile_epg.repository import EpgRepository
from saile_epg.database import EpgDatabase
from saile_epg.models import EpgChannel, EpgSnapshot

import tempfile
from pathlib import Path

tmp_dir = tempfile.TemporaryDirectory()
db = EpgDatabase(Path(tmp_dir.name) / 'epg.db')
db.initialize()
repo = EpgRepository(db)

channels_list = []
for ch in CLARO_OFFICIAL_CHANNELS:
    cid = str(ch['id'])
    name = ch['name']
    norm = normalize_channel_name(name)
    disp = clean_channel_title(name)
    channels_list.append(EpgChannel('claro', f'claro_{cid}', cid, disp, norm))

snapshot = EpgSnapshot('claro', tuple(channels_list), (), 1000)
repo.replace_snapshot(snapshot)

claro_channels = {ch.normalized_name: ch for ch in snapshot.channels}

lines = open('scratch/xtream_tv_channels_detailed.txt', encoding='utf-8').readlines()
channels = []
for line in lines:
    m = re.search(r"Nome na API: '([^']+)' \| Normalizado: '([^']*)' \| EPG ID da lista: '([^']*)'", line)
    if m:
        channels.append({'name': m.group(1), 'norm': m.group(2), 'epg_id': m.group(3)})

matched = []
unmatched = []

for ch in channels:
    res = repo.resolve_channel('claro', ch['epg_id'], ch['name'])
    if res:
        matched.append((ch, res))
    else:
        unmatched.append(ch)

print(f"Total de canais analisados: {len(channels)}")
print(f"Canais casados com EPG Claro: {len(matched)} ({len(matched)/len(channels)*100:.1f}%)")
print(f"Canais não casados: {len(unmatched)} ({len(unmatched)/len(channels)*100:.1f}%)")

seen = set()
distinct_unmatched = []
for ch in unmatched:
    if ch['norm'] not in seen:
        seen.add(ch['norm'])
        distinct_unmatched.append(ch)

print(f"\n--- TOTAL DE NOMES DISTINTOS NÃO CASADOS: {len(distinct_unmatched)} ---")
for ch in sorted(distinct_unmatched, key=lambda x: x['norm']):
    print(f"Nome: '{ch['name']}' | Norm: '{ch['norm']}' | EPG ID: '{ch['epg_id']}'")
