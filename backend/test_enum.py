import sqlalchemy

def test_sqlalchemy_enum_imports():
    assert sqlalchemy.__version__ is not None

