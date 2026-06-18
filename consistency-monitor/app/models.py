import datetime
from sqlalchemy import Column, Integer, DateTime, String, Text, Float
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ConsistencyLog(Base):
    __tablename__ = "consistency_log"

    id = Column(Integer, primary_key=True, index=True)
    execution_date = Column(DateTime, default=datetime.datetime.now)
    initiated_by = Column(String, default="System (Cron)")  # System or Username
    status = Column(String)  # SUCCESS, FAILED
    details = Column(Text)  # JSON representation of results
    duration_seconds = Column(Float)
