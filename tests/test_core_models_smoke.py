from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine

from core.types.sqlalchemy_models import Base, Company


def test_sqlalchemy_metadata_round_trip() -> None:
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()
    copied = Company.__table__.to_metadata(metadata, schema=None)
    metadata.create_all(engine)

    reflected = MetaData()
    reflected.reflect(bind=engine)

    assert copied.name in reflected.tables
    assert reflected.tables[copied.name].columns["bse_code"].type.python_type is str

