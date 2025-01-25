# Utilities/database_setup.py
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, Float, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

# Create the base class for declarative models
Base = declarative_base()

class HubLog(Base):
    __tablename__ = 'hub_logs'
    
    id = Column(Integer, primary_key=True)
    hub_id = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    total_usage = Column(Float, nullable=False)
    
    # Relationship to device logs
    device_logs = relationship("DeviceLog", back_populates="hub_log")
    
    __table_args__ = (
        # Ensure no duplicate entries for same hub and timestamp
        UniqueConstraint('hub_id', 'timestamp', name='uix_hub_timestamp'),
    )

class DeviceLog(Base):
    __tablename__ = 'device_logs'
    
    id = Column(Integer, primary_key=True)
    hub_log_id = Column(Integer, ForeignKey('hub_logs.id'), nullable=False)
    device_id = Column(String, nullable=False)
    active_minutes = Column(Integer, nullable=False)
    power_usage = Column(Float, nullable=False)
    
    # Relationship to hub log
    hub_log = relationship("HubLog", back_populates="device_logs")
    
    __table_args__ = (
        # Ensure one entry per device per hub log
        UniqueConstraint('hub_log_id', 'device_id', name='uix_hublog_device'),
    )

def init_db():
    """Initialize the database, creating tables if they don't exist."""
    # Create SQLite database in the project directory
    engine = create_engine('sqlite:///smart_home.db', echo=True)
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    return engine

if __name__ == "__main__":
    # Create the database and tables
    engine = init_db()
    print("Database initialized successfully!")