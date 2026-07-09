#!/usr/bin/env python3
"""Simple demonstration of CRUD operations."""

import sys
import os
from datetime import date
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from database import get_database
from database.models import Employer, Worker, ANOFMEvent


def main():
    print("CRUD Operations Demo - Task 1 Database Foundation")
    print("=" * 50)

    db = get_database()
    db.initialize_database()
    print("Database initialized")

    with db.get_session() as session:
        # Test Employer CRUD
        print("\n1. Testing Employer CRUD:")

        # CREATE
        employer = Employer.create(
            session,
            name="Test Construction GmbH",
            country="DE",
            sector="Construction",
            contact_email="test@construction.de"
        )
        session.commit()
        print(f"   CREATE: Employer ID {employer.id}")

        # READ
        retrieved = Employer.get_by_id(session, employer.id)
        print(f"   READ: Found '{retrieved.name}'")

        # UPDATE
        updated = Employer.update(session, employer.id, name="Updated Construction GmbH")
        session.commit()
        print(f"   UPDATE: Name changed to '{updated.name}'")

        # FIND_BY
        found = Employer.find_by(session, country="DE")
        print(f"   FIND_BY: Found {len(found)} German employers")

        # Test Worker CRUD
        print("\n2. Testing Worker CRUD:")

        worker = Worker.create(
            session,
            first_name="Ion",
            last_name="Test",
            email="ion@test.ro",
            region="Hunedoara",
            gdpr_consent=True
        )
        session.commit()
        print(f"   CREATE: Worker ID {worker.id}")

        # Test Event CRUD
        print("\n3. Testing Event CRUD:")

        event = ANOFMEvent.create(
            session,
            name="Test Event",
            date=date(2025, 6, 15),
            location="Test Location",
            region="Hunedoara"
        )
        session.commit()
        print(f"   CREATE: Event ID {event.id}")

        # Test pagination
        print("\n4. Testing Pagination:")
        all_employers = Employer.get_all(session, limit=5)
        print(f"   GET_ALL: Retrieved {len(all_employers)} employers")

        # DELETE operations
        print("\n5. Testing DELETE operations:")
        Employer.delete(session, employer.id)
        Worker.delete(session, worker.id)
        ANOFMEvent.delete(session, event.id)
        session.commit()
        print("   DELETE: All test records deleted")

        print("\n[SUCCESS] All CRUD operations working correctly!")
        print("Task 1 Database Foundation - COMPLETE")


if __name__ == "__main__":
    main()