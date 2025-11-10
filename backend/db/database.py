from sqlmodel import create_engine, Session
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

# Prefer DB_CONNECTION_STRING if provided; otherwise build Postgres URL if all parts exist; else fallback to local SQLite
connection_string = os.getenv('DB_CONNECTION_STRING')
if not connection_string:
    db_user = os.getenv('DB_USERNAME')
    db_pass = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST')
    db_port = os.getenv('DB_PORT')
    db_name = os.getenv('DB_DATABASE')
    if all([db_user, db_pass, db_host, db_port, db_name]):
        connection_string = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    else:
        # Local developer-friendly fallback
        connection_string = 'sqlite:///./neuralagent.db'

engine = create_engine(connection_string, echo=True)

SessionLocal = sessionmaker(class_=Session, bind=engine, autocommit=False, autoflush=False)


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
