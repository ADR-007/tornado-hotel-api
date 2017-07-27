from typing import Any

from sqlalchemy import create_engine, Table, Column, Integer, ForeignKey, String, UniqueConstraint, Float, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import Insert

Base = declarative_base()


def uni_repr(self: Any):
    return '{}({})'.format(
        self.__class__.__name__,
        ', '.join(['{}={}'.format(k, repr(v)) for k, v in self.__dict__.items() if not k.startswith('_')])
    )

rent_operations = Table(
    'rent_operations',
    Base.metadata,
    Column('client_id', Integer, ForeignKey('clients.id')),
    Column('rent_id', Integer, ForeignKey('rents.id')),
)


class FirstName(Base):
    __tablename__ = 'first_names'

    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String(50), unique=True, nullable=False)

    def __repr__(self):
        return uni_repr(self)


class LastName(Base):
    __tablename__ = 'last_names'

    id = Column(Integer, primary_key=True, autoincrement=True)
    last_name = Column(String(50), unique=True, nullable=False)

    def __repr__(self):
        return uni_repr(self)


class Client(Base):
    __tablename__ = 'clients'

    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name_id = Column(Integer, ForeignKey('first_names.id'))
    last_name_id = Column(Integer, ForeignKey('last_names.id'))
    age = Column(Integer, nullable=False)
    passport_serial = Column(String(2), nullable=False)
    passport_number = Column(String(20), nullable=False)

    __table_args__ = (
        UniqueConstraint('passport_serial', 'passport_number', name='passport_info'),
    )

    def __repr__(self):
        return uni_repr(self)


class Rent(Base):
    __tablename__ = 'rents'

    id = Column(Integer, primary_key=True, autoincrement=True)
    clients = relationship("Client", secondary=rent_operations)
    hotel_number = Column(Integer, ForeignKey('hotel_numbers.number'))
    total_price = Column(Float, nullable=False)

    from_date = Column(Date, nullable=False)
    to_date = Column(Date, nullable=False)

    def __repr__(self):
        return uni_repr(self)


class HotelNumber(Base):
    __tablename__ = 'hotel_numbers'

    number = Column(Integer, primary_key=True)
    price_per_night = Column(Float, nullable=False)
    description = Column(String(1000))

    def __repr__(self):
        return uni_repr(self)


