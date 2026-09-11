"""Client du microservice moteur (fallback local si C2B_MOTEUR_URL vide)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from django.conf import settings

from paris.moteur import AnalyseInvalide, analyser, classer_journee


def _moteur_url() -> str:
    return (getattr(settings, 'C2B_MOTEUR_URL', None) or '').rstrip('/')


def moteur_disponible() -> bool:
    base = _moteur_url()
    if not base:
        return False
    try:
        req = urllib.request.Request(f'{base}/health', method='GET')
        with urllib.request.urlopen(req, timeout=3) as resp:
            return getattr(resp, 'status', 200) == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def analyser_et_classer_journee(
    matchs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    matchs : dicts avec clés c1,cn,c2, o25?, u25?, nom_dom, nom_ext, ref?
    Retourne la liste des payloads analysés + classés (niveaux posés).
    """
    base = _moteur_url()
    if base:
        return _via_http(base, matchs)
    return _via_local(matchs)


def _via_local(matchs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    analyses: list[dict[str, Any]] = []
    for m in matchs:
        ou = None
        if m.get('o25') is not None and m.get('u25') is not None:
            ou = (float(m['o25']), float(m['u25']))
        try:
            payload = analyser(
                (float(m['c1']), float(m['cn']), float(m['c2'])),
                ou,
                m.get('nom_dom') or 'Domicile',
                m.get('nom_ext') or 'Extérieur',
            )
        except AnalyseInvalide:
            continue
        if m.get('ref') is not None:
            payload['ref'] = m['ref']
        analyses.append(payload)
    if not analyses:
        raise AnalyseInvalide('aucune analyse valide')
    classer_journee(analyses)
    return analyses


def _via_http(base: str, matchs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    body = json.dumps({'matchs': matchs}).encode('utf-8')
    req = urllib.request.Request(
        f'{base}/v1/analyser',
        data=body,
        headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        detail = e.read().decode('utf-8', errors='replace')
        raise AnalyseInvalide(f'Moteur HTTP {e.code}: {detail}') from e
    except urllib.error.URLError as e:
        raise AnalyseInvalide(f'Moteur injoignable ({base}): {e.reason}') from e
    return list(data.get('analyses') or [])
