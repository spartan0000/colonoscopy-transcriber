#script to seed the database with some fake data
import enum
from random import choice, randint
from datetime import datetime, timedelta

from app.database.connection import SessionLocal
from app.database.models import (
    Base,
    Procedure,
    Polyp,
    Histology,
    ResectionMethod,
    PathologyType,
    PolypLocation,
    DysplasiaGrade,
    Morphology,
    PolypLocationLookup,
)


resection_methods = list(ResectionMethod)
pathology_types = list(PathologyType)
dysplasia_grades = list(DysplasiaGrade)
morphologies = list(Morphology)

def seed_database(n_patients:int):
    session = SessionLocal()
    locations = session.query(PolypLocationLookup).filter(PolypLocationLookup.is_active==True).all()

    for i in range(1, n_patients+1):
        proc = Procedure(
            procedure_id = f'{i:-5d}',
            patient_id = f'PAT{i:04d}',
            procedure_date = datetime(2026, 2, i, 10, 0, 0),
            cecum_reached = choice([True, True, True, False]),
            withdrawal_time = round(randint(200, 1000) + randint(0,59)/60, 2),
            endoscopist_id = choice([1,2,3,4]),
            entered_by = 'seeder_script',
            source_system = 'seed_data',
            created_at = datetime.now()

        )
    
        for _ in range(randint(1,5)):
            polyp = Polyp(
                
                size_mm = randint(1,10),
                morphology = choice(morphologies),
                resection_method = choice(resection_methods),
                resection_complete = choice([True, True, True, False]),
                retrieved = choice([True, True, True, False]),
                created_at = datetime.now()

            )
            histology = Histology(
                histology = choice(pathology_types),
                dysplasia = choice(dysplasia_grades),
                entered_by = 'seeder_script',
                source_system = 'seed_data',
                created_at = datetime.now()
            )
            polyp.location_ref = choice(locations)
            polyp.histology = histology
            proc.polyps.append(polyp)
    
        session.add(proc)
    session.commit()
    session.close()

    print(f"Seeded database with {n_patients} patients' procedures.")

if __name__ == "__main__":
    seed_database(10)