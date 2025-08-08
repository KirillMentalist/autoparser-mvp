from packages.persistence.db import SessionLocal, engine
from packages.persistence.models import Base, Measure

def main():
    Base.metadata.create_all(bind=engine)
    print("DB initialized")

if __name__ == "__main__":
    main()
