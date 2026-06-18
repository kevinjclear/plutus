import plutus


def test_package_exposes_version():
    assert isinstance(plutus.__version__, str)
    assert plutus.__version__
