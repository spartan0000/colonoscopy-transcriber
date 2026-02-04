from app.database.models import PolypLocationLookup
from app.database.connection import SessionLocal

def seed_polyp_locations():

    db = SessionLocal()
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


if __name__ == "__main__":
    seed_polyp_locations()