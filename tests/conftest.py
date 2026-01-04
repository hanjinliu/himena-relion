from pytest import fixture

@fixture(autouse=True, scope="session")
def import_all():
    """This is needed to initialize everything."""
    from himena_relion import relion5, relion5_tomo, external, io  # noqa: F401
