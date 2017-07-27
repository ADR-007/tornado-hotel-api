import datetime

from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker

from database import Base, FirstName, LastName, Client, Rent, HotelNumber


def insert_sample_data_to_database():
    engine = create_engine('sqlite:///hotel.db', echo=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    # connection = engine.connect()
    Session = sessionmaker(bind=engine)
    session = Session()

    clients = [
        Client(first_name_id=1, last_name_id=1, age=18, passport_serial='FB', passport_number='12345678'),
        Client(first_name_id=2, last_name_id=2, age=20, passport_serial='FB', passport_number='31313131'),
        Client(first_name_id=3, last_name_id=2, age=22, passport_serial='FF', passport_number='23232323'),
        Client(first_name_id=2, last_name_id=3, age=22, passport_serial='FE', passport_number='12121212'),
    ]

    rents = [
        Rent(
            hotel_number=1,
            total_price=2000,
            from_date=datetime.date(2017, 1, 1),
            to_date=datetime.date(2017, 1, 3),
            clients=[clients[1], clients[2]]
        ),
        Rent(
            hotel_number=2,
            total_price=10 * 10 * (datetime.date(2017, 10, 27) - datetime.date(2017, 10, 1)).days,
            from_date=datetime.date(2017, 10, 1),
            to_date=datetime.date(2017, 10, 27),
            clients=[clients[0]]
        ),
        Rent(
            hotel_number=2,
            total_price=10 * (datetime.date(2017, 8, 3) - datetime.date(2017, 7, 27)).days,
            from_date=datetime.date(2017, 7, 27),
            to_date=datetime.date(2017, 8, 3),
            clients=[clients[3]]
        )
    ]

    session.add_all([
        FirstName(first_name='Ivan'),
        FirstName(first_name='Stepan'),
        FirstName(first_name='Olga'),
        LastName(last_name='Ivanov'),
        LastName(last_name='Stepanov'),
        LastName(last_name='Petrov'),
        HotelNumber(number=1, price_per_night=1000.0, description='VIP'),
        HotelNumber(number=2, price_per_night=10.0, description='Cheap'),
        HotelNumber(number=3, price_per_night=10.0, description='Cheap'),
        *clients,
        *rents
    ])

    session.commit()
    session.close()


if __name__ == '__main__':
    insert_sample_data_to_database()
