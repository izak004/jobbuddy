"""Shared loader for sources/companies.json, used by every ATS-type connector
(Greenhouse/Lever have their own inline copies predating this; new connectors use this)."""
import json
import os

COMPANIES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "companies.json")


def load_companies(key):
    with open(COMPANIES_PATH) as f:
        return json.load(f).get(key, [])
