import sys


def test_python_version():
    assert sys.version_info >= (3, 14)


def test_core_dependencies_import():
    import playwright
    import pydantic
    import dotenv

    assert playwright
    assert pydantic
    assert dotenv