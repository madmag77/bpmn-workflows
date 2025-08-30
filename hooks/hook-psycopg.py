#!/usr/bin/env python3

from PyInstaller.utils.hooks import collect_all

# Collect all psycopg modules and data
datas, binaries, hiddenimports = collect_all('psycopg')

# Add specific psycopg modules that might be missed
hiddenimports += [
    'psycopg.pq',
    'psycopg._pq',
    'psycopg.pq.pq',
    'psycopg_c',
    'psycopg_binary',
    'psycopg_pool',
]

# Ensure we include the pq module variants
hiddenimports += [
    'psycopg.pq._pq_ctypes',
    'psycopg.pq.misc',
]
