#!/usr/bin/env python3
from setuptools import setup
import subprocess
import os
import sys
import importlib.resources

with importlib.resources.path('srht', 'Makefile') as f:
    srht_path = f.parent.as_posix()

make = os.environ.get("MAKE", "make")
subp = subprocess.run([make, "SRHT_PATH=" + srht_path])
if subp.returncode != 0:
    sys.exit(subp.returncode)

ver = os.environ.get("PKGVER") or subprocess.run(['git', 'describe', '--tags'],
      stdout=subprocess.PIPE).stdout.decode().strip()

setup(
  name = 'mansrht',
  packages = [
      'mansrht',
      'mansrht.alembic',
      'mansrht.alembic.versions',
      'mansrht.blueprints',
      'mansrht.types',
  ],
  version = ver,
  description = 'man.sr.ht website',
  author = 'Drew DeVault',
  author_email = 'sir@cmpwn.com',
  url = 'https://git.sr.ht/~sircmpwn/man.sr.ht',
  install_requires = ['srht'],
  license = 'AGPL-3.0',
  package_data={
      'mansrht': [
          'templates/*.html',
          'static/icons/*',
          'static/*'
      ]
  },
  scripts = [
      'mansrht-initdb',
      'mansrht-migrate',
  ]
)
