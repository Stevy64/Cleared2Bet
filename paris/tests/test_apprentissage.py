"""Tests justification tips + apprentissage calibration."""

from types import SimpleNamespace

import pytest

from paris.justification import justifier_option
from paris.management.commands.apprendre_calibration import (
    MIN_FAMILLE,
    apprendre_depuis_options,
)
from paris.moteur import CALIBRATION_DEFAUT, corriger, invalider_calibration_cache


def test_justifier_option_priorise_faits_terrain():
    option = SimpleNamespace(
        libelle='Moins de 4 buts',
        niveau='prudente',
        famille='Total buts',
        probabilite=0.75,
        origine='calcul',
        cote_juste=1.33,
    )
    analyse = SimpleNamespace(
        profil='moyen',
        score_probable='1-1',
        buts_dom_attendus=1.35,
        buts_ext_attendus=1.10,
        p1=0.42,
        pn=0.28,
        p2=0.30,
        residu=0.01,
    )
    contexte = SimpleNamespace(
        forme_dom='Sevilla : V–N–V–D–N — 8ᵉ au classement.',
        forme_ext='Valencia : N–D–D–V–N — série compliquée.',
        confrontations=(
            'Sur 6 confrontations récentes : Sevilla 2, 3 nuls, Valencia 1 '
            '— beaucoup de matchs serrés.'
        ),
        absents_dom='Joueur A (blessé)',
        absents_ext='',
        tendance_buts='Rythme plutôt contenu sur les derniers matchs des deux équipes.',
        a_savoir='Conditions annoncées : 14 °C, pluie fine.',
    )
    j = justifier_option(
        option=option,
        analyse=analyse,
        contexte=contexte,
        domicile='Sevilla',
        exterieur='Valencia',
    )
    assert 'Prudent' in j['titre']
    assert '75 %' in j['accroche']
    assert 'faits' in j['accroche'].lower() or 'formes' in j['accroche'].lower()
    assert 'vestiaire' not in j['accroche'].lower()
    assert 'λ' not in j['accroche']
    assert 'Poisson' not in ' '.join(j['points'])
    assert 2 <= len(j['arguments']) <= 3
    cles = {a['cle'] for a in j['arguments']}
    assert 'forme' in cles or 'forme_dom' in cles
    assert 'h2h' in cles or 'lecture' in cles or 'absents' in cles
    blob = ' '.join(j['points']).lower()
    assert 'blessé' in blob or 'pluie' in blob or 'confrontations' in blob or 'serré' in blob or 'forme' in blob
    assert 'café' not in blob
    assert all(a['texte'][-1] in '.!?…' for a in j['arguments'])
    assert len(j['accroche']) < 160


def test_justifier_filet_mentionne_plan_b():
    option = SimpleNamespace(
        libelle='Au moins 1 but',
        niveau='filet',
        famille='Total buts',
        probabilite=0.91,
        origine='calcul',
        cote_juste=1.10,
    )
    j = justifier_option(option=option)
    blob = (j['accroche'] + ' ' + ' '.join(j['points'])).lower()
    assert 'filet' in blob or 'repli' in blob or 'sécurité' in blob


def test_apprendre_ne_modifie_pas_si_echantillon_faible():
    options = [
        SimpleNamespace(code='OV_1.5', origine='calcul', probabilite=0.75, resultat='gagne'),
        SimpleNamespace(code='OV_1.5', origine='calcul', probabilite=0.72, resultat='perdu'),
    ]
    tables, echantillons = apprendre_depuis_options(options, min_famille=MIN_FAMILLE)
    assert echantillons['+1.5'] == 2
    assert tables['+1.5'] == CALIBRATION_DEFAUT['+1.5']


def test_apprendre_affine_avec_assez_d_obs(tmp_path, settings):
    settings.BASE_DIR = tmp_path
    invalider_calibration_cache()
    options = []
    for i in range(40):
        options.append(SimpleNamespace(
            code='OV_1.5',
            origine='calcul',
            probabilite=0.74 + (i % 5) * 0.01,
            resultat='gagne' if i % 3 else 'perdu',
        ))
    tables, echantillons = apprendre_depuis_options(options, min_famille=20)
    assert echantillons['+1.5'] == 40
    assert tables['+1.5'] != CALIBRATION_DEFAUT['+1.5']
    ys = [y for _, y in tables['+1.5']]
    assert ys == sorted(ys)


def test_corriger_utilise_cache_apres_invalider():
    invalider_calibration_cache()
    p = corriger(0.7434, '+1.5')
    assert 0.005 <= p <= 0.995
