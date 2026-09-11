"""
Microservice moteur Cleared2Bet (stateless).

Expose l’analyse / classement de journée sans Django ni base.
Le worker et le web appellent ce service via C2B_MOTEUR_URL.
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from paris.moteur import (
    VERSION_MOTEUR,
    AnalyseInvalide,
    analyser,
    classer_journee,
)

app = FastAPI(
    title='Cleared2Bet Moteur',
    version=VERSION_MOTEUR,
    docs_url='/docs',
)


class MatchCotes(BaseModel):
    c1: float = Field(..., ge=1.01, le=100)
    cn: float = Field(..., ge=1.01, le=100)
    c2: float = Field(..., ge=1.01, le=100)
    o25: float | None = Field(None, ge=1.01, le=100)
    u25: float | None = Field(None, ge=1.01, le=100)
    nom_dom: str = 'Domicile'
    nom_ext: str = 'Extérieur'
    ref: str | None = None


class AnalyserRequest(BaseModel):
    matchs: list[MatchCotes]


class AnalyserResponse(BaseModel):
    version_moteur: str
    analyses: list[dict[str, Any]]


@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok', 'service': 'cleared2bet-moteur', 'version': VERSION_MOTEUR}


@app.post('/v1/analyser', response_model=AnalyserResponse)
def post_analyser(body: AnalyserRequest) -> AnalyserResponse:
    """Analyse chaque match puis classe la journée (plafond formes, routage)."""
    if not body.matchs:
        raise HTTPException(400, 'matchs vide')
    analyses: list[dict[str, Any]] = []
    for m in body.matchs:
        ou = None
        if m.o25 is not None and m.u25 is not None:
            ou = (m.o25, m.u25)
        try:
            payload = analyser((m.c1, m.cn, m.c2), ou, m.nom_dom, m.nom_ext)
        except AnalyseInvalide:
            continue
        if m.ref:
            payload['ref'] = m.ref
        analyses.append(payload)
    if not analyses:
        raise HTTPException(422, 'aucune analyse valide')
    classer_journee(analyses)
    return AnalyserResponse(version_moteur=VERSION_MOTEUR, analyses=analyses)


@app.post('/v1/analyser-un')
def post_analyser_un(m: MatchCotes) -> dict[str, Any]:
    ou = None
    if m.o25 is not None and m.u25 is not None:
        ou = (m.o25, m.u25)
    try:
        payload = analyser((m.c1, m.cn, m.c2), ou, m.nom_dom, m.nom_ext)
    except AnalyseInvalide as e:
        raise HTTPException(422, str(e)) from e
    if m.ref:
        payload['ref'] = m.ref
    return payload
