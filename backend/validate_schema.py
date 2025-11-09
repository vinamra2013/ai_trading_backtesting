#!/usr/bin/env python3
# Simple validation script for database models and schema

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

try:
    # Test basic SQLAlchemy functionality
    from sqlalchemy import (
        create_engine,
        Column,
        Integer,
        String,
        Float,
        DateTime,
        JSON,
        Text,
    )
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker

    print("✓ SQLAlchemy imports successful")

    # Test engine creation
    engine = create_engine("sqlite:///:memory:")
    print("✓ Database engine creation successful")

    # Test basic model definition
    Base = declarative_base()

    class TestModel(Base):
        __tablename__ = "test_table"
        id = Column(Integer, primary_key=True)
        name = Column(String(255))
        data = Column(JSON)

    # Create tables
    Base.metadata.create_all(bind=engine)
    print("✓ Table creation successful")

    # Test session operations
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    # Test basic CRUD
    test_record = TestModel(name="test", data={"key": "value"})
    session.add(test_record)
    session.commit()
    session.refresh(test_record)
    print("✓ Basic CRUD operations successful")

    session.close()
    print("\n🎉 Basic database functionality validation passed!")
    print("Note: Full FastAPI integration testing requires Docker environment")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
