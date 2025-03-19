from src.prueba import funcionPrueba


def test_funcionPrueba():
    assert funcionPrueba(5, 5) == 10

def test_funcionPrueba2():
    assert funcionPrueba(10, 5) == 15