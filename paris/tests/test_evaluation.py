import pytest

from paris.evaluation import evaluer


class TestHandicapEuropeen:
    """Le >= 0 est le piège : perdre d'exactement h buts reste gagnant."""

    def test_hcp_h_plus_1_gagne_si_perd_d_un_but(self):
        assert evaluer("HCP_H_+1", 0, 1) is True

    def test_hcp_h_plus_1_perdu_si_perd_de_deux_buts(self):
        assert evaluer("HCP_H_+1", 0, 2) is False

    def test_hcp_a_plus_1_gagne_si_perd_d_un_but(self):
        assert evaluer("HCP_A_+1", 1, 0) is True

    def test_hcp_a_plus_1_perdu_si_perd_de_deux_buts(self):
        assert evaluer("HCP_A_+1", 2, 0) is False


class TestMarge:
    def test_mrg_h_2_gagne_sur_ecart_de_deux(self):
        assert evaluer("MRG_H_2", 3, 1) is True

    def test_mrg_h_2_perdu_sur_ecart_d_un(self):
        assert evaluer("MRG_H_2", 2, 1) is False


class TestTotalButs:
    def test_un_25_gagne_sur_1_1(self):
        assert evaluer("UN_2.5", 1, 1) is True

    def test_un_25_perdu_sur_2_1(self):
        assert evaluer("UN_2.5", 2, 1) is False


class TestMiTempsSansScore:
    @pytest.mark.parametrize(
        "code",
        ["HT_1", "HT_N", "HT_2", "HT_OV_0.5", "HT_OV_1.5", "HT_UN_0.5"],
    )
    def test_ht_sans_mi_temps_renvoie_none(self, code):
        assert evaluer(code, 2, 1) is None
        assert evaluer(code, 2, 1, hh=None, ha=None) is None


class TestCodeInconnu:
    def test_code_inconnu_leve_value_error(self):
        with pytest.raises(ValueError, match="code inconnu"):
            evaluer("FOO_BAR", 1, 0)


class TestScoreFinalAbsent:
    def test_sans_score_final_renvoie_none(self):
        assert evaluer("1X2_1", None, None) is None
        assert evaluer("1X2_1", 1, None) is None
        assert evaluer("1X2_1", None, 0) is None


class Test1X2EtDoubleChance:
    def test_1x2(self):
        assert evaluer("1X2_1", 2, 1) is True
        assert evaluer("1X2_N", 1, 1) is True
        assert evaluer("1X2_2", 0, 2) is True
        assert evaluer("1X2_1", 1, 1) is False

    def test_double_chance(self):
        assert evaluer("DC_1X", 1, 1) is True
        assert evaluer("DC_1X", 0, 1) is False
        assert evaluer("DC_X2", 0, 1) is True
        assert evaluer("DC_12", 1, 0) is True
        assert evaluer("DC_12", 0, 0) is False


class TestOverUnderEtBtts:
    def test_over(self):
        assert evaluer("OV_2.5", 2, 1) is True
        assert evaluer("OV_2.5", 1, 1) is False

    def test_btts(self):
        assert evaluer("BTTS_O", 1, 1) is True
        assert evaluer("BTTS_O", 2, 0) is False
        assert evaluer("BTTS_N", 2, 0) is True
        assert evaluer("BTTS_N", 0, 0) is True


class TestMiTempsAvecScore:
    def test_ht_avec_score(self):
        assert evaluer("HT_1", 2, 1, 1, 0) is True
        assert evaluer("HT_N", 2, 2, 1, 1) is True
        assert evaluer("HT_2", 1, 2, 0, 1) is True
        assert evaluer("HT_OV_0.5", 2, 1, 1, 0) is True
        assert evaluer("HT_OV_0.5", 0, 0, 0, 0) is False
