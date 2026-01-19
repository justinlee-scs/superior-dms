from app.db.session import engine, Base

# Force model registration
from app.db.models import Document, DocumentVersion


def init_db():
    #print("Registered tables:", list(Base.metadata.tables.keys()))
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
