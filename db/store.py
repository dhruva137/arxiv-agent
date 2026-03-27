from datetime import datetime
from db.models import SessionLocal, WatchedPaper, GeneratedChangelog

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def add_watched_paper(arxiv_id: str, webhook_url: str = None, title: str = None, last_known_version: int = 1):
    db = SessionLocal()
    try:
        paper = db.query(WatchedPaper).filter(WatchedPaper.arxiv_id == arxiv_id).first()
        if not paper:
            paper = WatchedPaper(
                arxiv_id=arxiv_id,
                title=title,
                webhook_url=webhook_url,
                last_known_version=last_known_version
            )
            db.add(paper)
            db.commit()
            return True
        return False
    finally:
        db.close()

def remove_watched_paper(arxiv_id: str):
    db = SessionLocal()
    try:
        paper = db.query(WatchedPaper).filter(WatchedPaper.arxiv_id == arxiv_id).first()
        if paper:
            db.delete(paper)
            db.commit()
            return True
        return False
    finally:
        db.close()

def get_watched_papers() -> list:
    db = SessionLocal()
    try:
        return db.query(WatchedPaper).all()
    finally:
        db.close()

def update_last_checked(arxiv_id: str, version: int):
    db = SessionLocal()
    try:
        paper = db.query(WatchedPaper).filter(WatchedPaper.arxiv_id == arxiv_id).first()
        if paper:
            paper.last_known_version = version
            paper.last_checked = datetime.utcnow()
            db.commit()
    finally:
        db.close()

def save_changelog(changelog_data: dict):
    db = SessionLocal()
    try:
        # Avoid duplicates
        existing = db.query(GeneratedChangelog).filter(
            GeneratedChangelog.arxiv_id == changelog_data["arxiv_id"],
            GeneratedChangelog.version_from == changelog_data["version_from"],
            GeneratedChangelog.version_to == changelog_data["version_to"]
        ).first()
        
        if not existing:
            log = GeneratedChangelog(**changelog_data)
            db.add(log)
            db.commit()
            return True
        return False
    finally:
        db.close()

def get_changelog(arxiv_id: str, v_from: int, v_to: int) -> dict | None:
    db = SessionLocal()
    try:
        log = db.query(GeneratedChangelog).filter(
            GeneratedChangelog.arxiv_id == arxiv_id,
            GeneratedChangelog.version_from == v_from,
            GeneratedChangelog.version_to == v_to
        ).first()
        if log:
            return {
                "arxiv_id": log.arxiv_id,
                "version_from": log.version_from,
                "version_to": log.version_to,
                "severity": log.severity,
                "tldr": log.tldr,
                "changelog_markdown": log.changelog_markdown,
                "changelog_json": log.changelog_json,
                "created_at": log.created_at.isoformat()
            }
        return None
    finally:
        db.close()

def get_all_changelogs(arxiv_id: str) -> list[dict]:
    db = SessionLocal()
    try:
        logs = db.query(GeneratedChangelog).filter(
            GeneratedChangelog.arxiv_id == arxiv_id
        ).order_by(GeneratedChangelog.created_at.desc()).all()
        
        return [{
            "arxiv_id": l.arxiv_id,
            "version_from": l.version_from,
            "version_to": l.version_to,
            "severity": l.severity,
            "tldr": l.tldr,
            "created_at": l.created_at.isoformat()
        } for l in logs]
    finally:
        db.close()
