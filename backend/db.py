from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    connect_args={'check_same_thread': False} if settings.database_url.startswith('sqlite') else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    if 'department' not in {column['name'] for column in inspect(engine).get_columns('classifications')}:
        with engine.begin() as connection:
            connection.exec_driver_sql('ALTER TABLE classifications ADD COLUMN department VARCHAR(50)')


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
