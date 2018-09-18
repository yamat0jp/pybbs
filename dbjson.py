# -*- coding: utf-8 -*-
import os


class static():
    base = os.path.dirname(__file__)
    json = os.path.join(base,'static/db/db.json')
    bak = os.path.join(base,'static/db/bak.json')
