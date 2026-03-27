import os
from datetime import datetime
from sqlalchemy import create_engine, Integer, String, Column, DateTime, Text, Boolean, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class WatchedPaper(Base):
    __tablename__ = 'watched_papers'
    
    id = Column(Integer, primary_key=True)
    arxiv_id = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=True)
    last_known_version = Column(Integer, default=1)
    webhook_url = Column(String, nullable=True)
    last_checked = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

class GeneratedChangelog(Base):
    __tablename__ = 'generated_changelogs'
    
    id = Column(Integer, primary_key=True)
    arxiv_id = Column(String, index=True, nullable=False)
    version_from = Column(Integer, nullable=False)
    version_to = Column(Integer, nullable=False)
    severity = Column(String, nullable=True)
    tldr = Column(String, nullable=True)
    changelog_markdown = Column(Text, nullable=False)
    changelog_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('arxiv_id', 'version_from', 'version_to', name='_paper_version_uc'),
    )

DB_PATH = os.path.expanduser("~/.arxiv-diff")
os.makedirs(DB_PATH, exist_ok=True)
engine = create_engine(f"sqlite:///{DB_PATH}/arxiv_diff.db")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

init_db()
