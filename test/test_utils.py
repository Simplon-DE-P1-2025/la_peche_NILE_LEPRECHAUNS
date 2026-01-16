from src.helpers import addition, est_pair

def test_addition_nombres_positifs():
    # ARRANGE
    x = 5
    y = 3

    # ACT
    resultat = addition(x, y)

    # ASSERT
    assert resultat == 8

def test_est_pair_avec_nombre_pair():
    # ARRANGE
    nombre = 4

    # ACT
    resultat = est_pair(nombre)

    # ASSERT
    assert resultat is True

def test_est_pair_avec_nombre_impair():
    # ARRANGE
    nombre = 5

    # ACT
    resultat = est_pair(nombre)

    # ASSERT
    assert resultat is False