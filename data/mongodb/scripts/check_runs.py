# -*- coding: utf-8 -*-
"""Checagem rápida do agent_runs no MongoDB (somente leitura)."""
import json
from typing import Any

import pymongo
from pymongo.collection import Collection


Document = dict[str, Any]

c: pymongo.MongoClient[Document] = pymongo.MongoClient(
    "mongodb://localhost:27017/",
    serverSelectionTimeoutMS=3000,
)
col: Collection[Document] = c["cline_agent"]["agent_runs"]

try:
    print("total docs:", col.count_documents({}))
    for d in col.find().sort("_id", -1).limit(3):
        d["_id"] = str(d["_id"])
        d["timeline"] = (d.get("timeline") or [])[-3:]
        print(json.dumps(d, ensure_ascii=False, default=str)[:900])
        print("-" * 40)
finally:
    c.close()
