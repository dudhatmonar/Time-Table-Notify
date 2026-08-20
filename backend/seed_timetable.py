import sys
from database import SessionLocal, engine
import models

def seed():
    db = SessionLocal()
    try:
        # Clear existing lectures
        db.query(models.Lecture).delete()
        db.commit()
        print("Successfully cleared existing database lectures.")

        # Exact lectures from the image
        lectures_data = [
            # Monday
            {
                "subject_code": "HM443",
                "subject_name": "Art of Influence",
                "type": "LEC",
                "day_of_week": "Monday",
                "start_time": "08:00",
                "end_time": "08:50",
                "room": "CEP-205",
                "teacher": "SK1",
                "color_scheme": "red"
            },
            {
                "subject_code": "IT643",
                "subject_name": "SW design & testing",
                "type": "LAB",
                "day_of_week": "Monday",
                "start_time": "09:00",
                "end_time": "11:00",
                "room": "LAB004/005",
                "teacher": "AC",
                "color_scheme": "green"
            },
            {
                "subject_code": "IT645",
                "subject_name": "Web & mobile dev",
                "type": "LEC",
                "day_of_week": "Monday",
                "start_time": "11:00",
                "end_time": "11:50",
                "room": "CEP-209",
                "teacher": "SD",
                "color_scheme": "green"
            },
            {
                "subject_code": "IT462",
                "subject_name": "Exploratory data analysis",
                "type": "LEC",
                "day_of_week": "Monday",
                "start_time": "15:00",
                "end_time": "15:50",
                "room": "CEP-209",
                "teacher": "GP",
                "color_scheme": "blue"
            },
            {
                "subject_code": "HM409",
                "subject_name": "Mgmt skills",
                "type": "LEC",
                "day_of_week": "Monday",
                "start_time": "16:00",
                "end_time": "16:50",
                "room": "CEP-212",
                "teacher": "ATS",
                "color_scheme": "red"
            },
            {
                "subject_code": "IT627",
                "subject_name": "Cloud computing",
                "type": "LEC",
                "day_of_week": "Monday",
                "start_time": "17:00",
                "end_time": "17:50",
                "room": "CEP-209",
                "teacher": "AM1",
                "color_scheme": "blue"
            },

            # Tuesday
            {
                "subject_code": "IT644",
                "subject_name": "Web services & SOA",
                "type": "LAB",
                "day_of_week": "Tuesday",
                "start_time": "09:00",
                "end_time": "11:00",
                "room": "LAB004/005",
                "teacher": "JL",
                "color_scheme": "green"
            },
            {
                "subject_code": "IT627",
                "subject_name": "Cloud computing",
                "type": "LEC",
                "day_of_week": "Tuesday",
                "start_time": "11:00",
                "end_time": "11:50",
                "room": "CEP-209",
                "teacher": "AM1",
                "color_scheme": "blue"
            },
            {
                "subject_code": "IT643",
                "subject_name": "SW design & testing",
                "type": "LEC",
                "day_of_week": "Tuesday",
                "start_time": "12:00",
                "end_time": "12:50",
                "room": "CEP-209",
                "teacher": "AC",
                "color_scheme": "green"
            },
            {
                "subject_code": "IT644",
                "subject_name": "Web services & SOA",
                "type": "LEC",
                "day_of_week": "Tuesday",
                "start_time": "15:00",
                "end_time": "15:50",
                "room": "CEP-209",
                "teacher": "JL",
                "color_scheme": "green"
            },

            # Wednesday
            {
                "subject_code": "IT645",
                "subject_name": "Web & mobile dev",
                "type": "LAB",
                "day_of_week": "Wednesday",
                "start_time": "09:00",
                "end_time": "11:00",
                "room": "LAB004/005",
                "teacher": "SD",
                "color_scheme": "green"
            },
            {
                "subject_code": "IT645",
                "subject_name": "Web & mobile dev",
                "type": "LEC",
                "day_of_week": "Wednesday",
                "start_time": "12:00",
                "end_time": "12:50",
                "room": "CEP-209",
                "teacher": "SD",
                "color_scheme": "green"
            },
            {
                "subject_code": "IT462",
                "subject_name": "Exploratory data analysis",
                "type": "LEC",
                "day_of_week": "Wednesday",
                "start_time": "14:00",
                "end_time": "14:50",
                "room": "CEP-209",
                "teacher": "GP",
                "color_scheme": "blue"
            },
            {
                "subject_code": "HM409",
                "subject_name": "Mgmt skills",
                "type": "LEC",
                "day_of_week": "Wednesday",
                "start_time": "16:00",
                "end_time": "16:50",
                "room": "CEP-212",
                "teacher": "ATS",
                "color_scheme": "red"
            },
            {
                "subject_code": "IT462",
                "subject_name": "Exploratory data analysis",
                "type": "LAB",
                "day_of_week": "Wednesday",
                "start_time": "17:00",
                "end_time": "19:00",
                "room": "CEP202",
                "teacher": "GP",
                "color_scheme": "blue"
            },

            # Thursday
            {
                "subject_code": "IT627",
                "subject_name": "Cloud computing",
                "type": "LAB",
                "day_of_week": "Thursday",
                "start_time": "09:00",
                "end_time": "11:00",
                "room": "LAB002",
                "teacher": "AM1",
                "color_scheme": "blue"
            },
            {
                "subject_code": "HM443",
                "subject_name": "Art of influence",
                "type": "LEC",
                "day_of_week": "Thursday",
                "start_time": "11:00",
                "end_time": "11:50",
                "room": "CEP-205",
                "teacher": "SK1",
                "color_scheme": "red"
            },
            {
                "subject_code": "IT643",
                "subject_name": "SW design & testing",
                "type": "LEC",
                "day_of_week": "Thursday",
                "start_time": "12:00",
                "end_time": "12:50",
                "room": "CEP-209",
                "teacher": "AC",
                "color_scheme": "green"
            },
            {
                "subject_code": "IT644",
                "subject_name": "Web services & SOA",
                "type": "LEC",
                "day_of_week": "Thursday",
                "start_time": "14:00",
                "end_time": "14:50",
                "room": "CEP-209",
                "teacher": "JL",
                "color_scheme": "green"
            },
            {
                "subject_code": "IT462",
                "subject_name": "Exploratory data analysis",
                "type": "LEC",
                "day_of_week": "Thursday",
                "start_time": "16:00",
                "end_time": "16:50",
                "room": "CEP-209",
                "teacher": "GP",
                "color_scheme": "blue"
            },

            # Friday
            {
                "subject_code": "IT643",
                "subject_name": "SW design & testing",
                "type": "LEC",
                "day_of_week": "Friday",
                "start_time": "08:00",
                "end_time": "08:50",
                "room": "CEP-209",
                "teacher": "AC",
                "color_scheme": "green"
            },
            {
                "subject_code": "HM443",
                "subject_name": "Art of influence",
                "type": "LEC",
                "day_of_week": "Friday",
                "start_time": "11:00",
                "end_time": "11:50",
                "room": "CEP-205",
                "teacher": "SK1",
                "color_scheme": "red"
            },
            {
                "subject_code": "IT645",
                "subject_name": "Web & mobile dev",
                "type": "LEC",
                "day_of_week": "Friday",
                "start_time": "12:00",
                "end_time": "12:50",
                "room": "CEP-209",
                "teacher": "SD",
                "color_scheme": "green"
            },
            {
                "subject_code": "IT644",
                "subject_name": "Web services & SOA",
                "type": "LEC",
                "day_of_week": "Friday",
                "start_time": "16:00",
                "end_time": "16:50",
                "room": "CEP-209",
                "teacher": "JL",
                "color_scheme": "green"
            },
            {
                "subject_code": "IT627",
                "subject_name": "Cloud computing",
                "type": "LEC",
                "day_of_week": "Friday",
                "start_time": "17:00",
                "end_time": "17:50",
                "room": "CEP-209",
                "teacher": "AM1",
                "color_scheme": "blue"
            }
        ]

        for item in lectures_data:
            lec = models.Lecture(**item)
            db.add(lec)
        
        db.commit()
        print(f"Successfully seeded {len(lectures_data)} lectures into the database!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    seed()
