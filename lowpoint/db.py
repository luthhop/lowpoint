import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg2://lowpoint:lowpoint_dev@localhost:5432/lowpoint",
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
