"""Apprentissage des tables de calibration à partir des tips réglés."""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy

import numpy as np
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date

from paris.calibration_store import charger_tables, sauver_tables
from paris.models import Option
from paris.moteur import CALIBRATION_DEFAUT
from paris.views import _fenetre_jour

NIVEAUX_APPRIS = ('prudente', 'filet', 'equilibree', 'audacieuse')
MIN_FAMILLE = 12
MIN_BIN = 4
BINS = (
    (0.20, 0.40),
    (0.40, 0.55),
    (0.55, 0.70),
    (0.70, 0.82),
    (0.82, 0.95),
)
POIDS_PRIOR = 18.0  # équivalent « faux » échantillons du défaut


def _monotone(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Force une courbe non décroissante en p (isotonic grossier)."""
    pts = sorted(points, key=lambda t: t[0])
    out = []
    last_y = 0.0
    for x, y in pts:
        y = max(float(y), last_y)
        y = float(np.clip(y, 0.01, 0.99))
        out.append((float(x), y))
        last_y = y
    return out


def apprendre_depuis_options(options, min_famille: int = MIN_FAMILLE) -> tuple[dict, dict[str, int]]:
    """Retourne (tables, echantillons_par_famille)."""
    by_fam: dict[str, list[tuple[float, int]]] = defaultdict(list)
    for o in options:
        if o.famille not in CALIBRATION_DEFAUT:
            continue
        by_fam[o.famille].append((float(o.probabilite), 1 if o.resultat == 'gagne' else 0))

    base = charger_tables()
    learned = deepcopy(base)
    echantillons: dict[str, int] = {}

    for fam, rows in by_fam.items():
        n = len(rows)
        echantillons[fam] = n
        if n < min_famille:
            continue
        empiriques: list[tuple[float, float, int]] = []
        for lo, hi in BINS:
            bucket = [(p, y) for p, y in rows if lo <= p < hi]
            if len(bucket) < MIN_BIN:
                continue
            mx = sum(p for p, _ in bucket) / len(bucket)
            my = sum(y for _, y in bucket) / len(bucket)
            empiriques.append((mx, my, len(bucket)))

        if not empiriques:
            continue

        prior = CALIBRATION_DEFAUT.get(fam) or base.get(fam) or []
        merged: list[tuple[float, float]] = []
        for x, y in prior:
            merged.append((x, y))
        for mx, my, nb in empiriques:
            xs = [a for a, _ in prior] or [mx]
            ys = [b for _, b in prior] or [my]
            y0 = float(np.interp(mx, xs, ys))
            w = nb / (nb + POIDS_PRIOR)
            yb = (1 - w) * y0 + w * my
            merged.append((mx, yb))

        learned[fam] = _monotone(merged)

    return learned, echantillons


class Command(BaseCommand):
    help = (
        'Affine les tables de calibration (data/calibration.json) à partir des '
        'tips Prudente / Filet (et autres niveaux) déjà réglés.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--depuis', default='', help='AAAA-MM-JJ')
        parser.add_argument('--jusqu_a', default='', help='AAAA-MM-JJ')
        parser.add_argument(
            '--min-famille', type=int, default=MIN_FAMILLE,
            help='Minimum d’observations par famille pour mettre à jour',
        )

    def handle(self, *args, **opts):
        min_famille = opts['min_famille']

        qs = (
            Option.objects
            .filter(
                resultat__in=('gagne', 'perdu'),
                niveau__in=NIVEAUX_APPRIS,
            )
            .select_related('analyse__match')
        )
        if opts['depuis']:
            d = parse_date(opts['depuis'])
            if d:
                debut, _ = _fenetre_jour(d)
                qs = qs.filter(analyse__match__coup_denvoi__gte=debut)
        if opts['jusqu_a']:
            d = parse_date(opts['jusqu_a'])
            if d:
                _, fin = _fenetre_jour(d)
                qs = qs.filter(analyse__match__coup_denvoi__lte=fin)

        options = list(qs)
        if not options:
            self.stdout.write(self.style.WARNING('Aucun tip réglé : rien à apprendre.'))
            return

        tables, echantillons = apprendre_depuis_options(options, min_famille=min_famille)
        maj = [f for f, n in echantillons.items() if n >= min_famille]
        self.stdout.write(
            f'{len(options)} tips analysés. Familles mises à jour : '
            + (', '.join(maj) if maj else '(aucune, échantillon insuffisant)')
        )
        for fam, n in sorted(echantillons.items()):
            self.stdout.write(f'  · {fam}: {n} obs.')

        if opts['dry_run']:
            self.stdout.write(self.style.WARNING('Dry-run : fichier non écrit.'))
            return

        path = sauver_tables(tables, echantillons=echantillons)
        self.stdout.write(self.style.SUCCESS(f'Calibration enregistrée → {path}'))
