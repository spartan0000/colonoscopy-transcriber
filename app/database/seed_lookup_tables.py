from app.database.models import PolypLocationLookup, EndoscopistLookup
from app.database.connection import TestSessionLocal, SessionLocal



def seed_polyp_locations(db):

    
    polyp_locations = [
        {"location_code": "cecum", "display_name": "Cecum"},
        {"location_code": "ascending_colon", "display_name": "Ascending Colon"},
        {"location_code": "hepatic_flexure", "display_name": "Hepatic Flexure"},
        {"location_code": "transverse_colon", "display_name": "Transverse Colon"},
        {"location_code": "splenic_flexure", "display_name": "Splenic Flexure"},
        {"location_code": "descending_colon", "display_name": "Descending Colon"},
        {"location_code": "sigmoid_colon", "display_name": "Sigmoid Colon"},
        {"location_code": "rectum", "display_name": "Rectum"},
        {"location_code": "anus", "display_name": "Anus"},
        {"location_code": "other", "display_name": "Other"},
    ]

    for loc in polyp_locations:
        existing = db.query(PolypLocationLookup).filter_by(location_code=loc["location_code"]).first()
        if not existing:
            new_location = PolypLocationLookup(
                location_code=loc["location_code"],
                display_name=loc["display_name"],
                is_active=True
            )
            db.add(new_location)
    db.commit() 

def seed_endoscopists(db):

    
    endoscopists = [
        {"endoscopist_id": 1, "endoscopist_name": "Jamie"},
        {"endoscopist_id": 2, "endoscopist_name": "Chuck"},
        {"endoscopist_id": 3, "endoscopist_name": "Louisa"},
        {"endoscopist_id": 4, "endoscopist_name": "David"},
    ]

    for doc in endoscopists:
        existing = db.query(EndoscopistLookup).filter_by(endoscopist_id=doc["endoscopist_id"]).first()
        if not existing:
            new_doc = EndoscopistLookup(
                endoscopist_id=doc["endoscopist_id"],
                endoscopist_name=doc["endoscopist_name"],
                is_active=True
            )
            db.add(new_doc)
    db.commit()

if __name__ == "__main__":
    db = SessionLocal()
    seed_polyp_locations(db)
    seed_endoscopists(db)