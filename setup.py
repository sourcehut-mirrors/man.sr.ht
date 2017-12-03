#!/usr/bin/env python3
from distutils.core import setup
import subprocess
import glob
import os

subprocess.call(["make"])

ver = os.environ.get("PKGVER") or subprocess.run(['git', 'describe', '--tags'],
      stdout=subprocess.PIPE).stdout.decode().strip()

setup(
  name = 'mansrht',
  packages = [
      'mansrht',
      'mansrht.types',
      'mansrht.blueprints',
      'mansrht.alembic',
      'mansrht.alembic.versions'
  ],
  version = ver,
  description = 'man.sr.ht website',
  author = 'Drew DeVault',
  author_email = 'sir@cmpwn.com',
  url = 'https://git.sr.ht/~sircmpwn/man.sr.ht',
  install_requires = ['srht', 'flask-login', 'alembic'],
  license = 'AGPL-3.0',
  package_data={
      'mansrht': [
          'templates/*.html',
          'static/*'
      ]
  }
)
