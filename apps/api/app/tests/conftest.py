import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.infrastructure.db.session import get_db
from fastapi.testclient import TestClient

@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    yield engine
    engine.dispose()

@pytest.fixture
def db_session(db_engine):
    """Provides a transactional database session that rolls back after each test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    
    SessionLocal = sessionmaker(
        bind=connection, 
        autoflush=False, 
        autocommit=False, 
        expire_on_commit=False
    )
    session = SessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    """Provides a TestClient with overridden get_db dependency to use the transactional session."""
    from app.main import app
    
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
