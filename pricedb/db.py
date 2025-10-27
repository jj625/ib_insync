from sqlalchemy import (
    create_engine, Column, String, Float, Integer, DateTime, PrimaryKeyConstraint, Boolean
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class OHLCV(Base):
    __tablename__ = "ohlcv"
    time = Column(DateTime, nullable=False)
    ticker = Column(String, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)
    __table_args__ = (PrimaryKeyConstraint("time", "ticker"),)

class Coverage(Base):
    __tablename__ = "coverage"
    ticker = Column(String, primary_key=True)
    start = Column(DateTime, nullable=False)
    end = Column(DateTime, nullable=False)
    is_backfill = Column(Boolean, default=False)

engine = create_engine("sqlite:///ohlcv.db")
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)