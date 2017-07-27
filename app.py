import os
import json

import datetime
import tornado.web
import tornado.options
import tornado.httpserver
import tornado.ioloop
from sqlalchemy import create_engine, or_, and_
from sqlalchemy.orm import sessionmaker

from database import Client, FirstName, LastName, Rent, HotelNumber
from tools import get_first_name_id, get_last_name_id, serialize

DATE_FORMAT = "%Y-%m-%d"

tornado.options.define("port", default=8888, help="run on the given port", type=int)


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", RootHandler),
            (r"/client", ClientHandler),
            (r"/client/(\d+)", ClientHandler),
            (r"/rent", RentHandler),
            (r"/rent/(\d+)", RentHandler),
            (r"/numbers/free", FreeNumbersHandler),
            (r"/numbers/free/([^/]+)", FreeNumbersHandler),
            (r"/numbers/rented", RentedNumbersHandler),
            (r"/numbers/rented/([^/]+)", RentedNumbersHandler),
        ]
        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            # xsrf_cookies=True,
            # cookie_secret="11oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
        )
        tornado.web.Application.__init__(self, handlers, **settings)

        self.db_engine = create_engine('sqlite:///hotel.db', echo=True)
        self.db_session_maker = sessionmaker(bind=self.db_engine)
        self.db_session = self.db_session_maker()


class BaseHandler(tornado.web.RequestHandler):
    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        self.db_session = self.application.db_session

    def data_received(self, chunk):
        return super().data_received(chunk)


class RootHandler(BaseHandler):
    def get(self, *args, **kwargs):
        self.write('<info will be here>')


class ClientHandler(BaseHandler):
    def get(self, client_id=None):
        keys = Client.id, FirstName.first_name, LastName.last_name, Client.age, \
               Client.passport_serial, Client.passport_number
        query = self.db_session \
            .query(*keys) \
            .join(FirstName) \
            .join(LastName)
        if client_id:
            query = query.filter(Client.id == int(client_id))

        self.write(serialize(keys, query.all()))

    def post(self):
        self.db_session.add(
            Client(
                first_name_id=get_first_name_id(self.db_session, self.get_argument('first_name')),
                last_name_id=get_last_name_id(self.db_session, self.get_argument('last_name')),
                age=self.get_argument('age'),
                passport_serial=self.get_argument('passport_serial'),
                passport_number=self.get_argument('passport_number'),
            )
        )
        self.db_session.commit()
        self.write('Added.')

    def delete(self, client_id=None):
        if client_id is None:
            tornado.web.HTTPError(400)

        self.db_session.query(Client).filter(Client.id == client_id).delete()
        self.db_session.commit()
        self.write('Deleted.')

    def put(self, client_id=None):
        if client_id is None:
            tornado.web.HTTPError(400)

        self.db_session.query(Client).filter(Client.id == client_id).update({
            Client.first_name_id: get_first_name_id(self.db_session, self.get_argument('first_name')),
            Client.last_name_id: get_last_name_id(self.db_session, self.get_argument('last_name')),
            Client.age: self.get_argument('age'),
            Client.passport_serial: self.get_argument('passport_serial'),
            Client.passport_number: self.get_argument('passport_number'),
        })
        self.db_session.commit()
        self.write('Updated.')


class RentHandler(BaseHandler):
    def get(self, rent_id=None):
        keys = (Rent.id, Rent.hotel_number, Rent.from_date, Rent.to_date, Rent.total_price, Client.id)
        query = self.db_session.query(*keys).join((Client, Rent.clients))
        if rent_id:
            query = query.filter(Rent.id == int(rent_id))

        self.write(serialize(keys, query.all()))

    def post(self):
        price_per_day = self.db_session.query(HotelNumber.price_per_night)\
            .filter(HotelNumber.number == int(self.get_argument('hotel_number'))).one()[0]

        from_date = datetime.datetime.strptime(self.get_argument('from_date'), DATE_FORMAT).date()
        to_date = datetime.datetime.strptime(self.get_argument('to_date'), DATE_FORMAT).date()
        self.db_session.add(Rent(
            hotel_number=int(self.get_argument('hotel_number')),
            total_price=(to_date - from_date).days * price_per_day,
            from_date=from_date,
            to_date=to_date,
            clients=self.db_session.query(Client).filter(
                Client.id.in_(list(map(int, self.get_arguments('client_id'))))).all()
        ))

        self.db_session.commit()
        self.write('Added.')

    def delete(self, rent_id=None):
        if rent_id is None:
            tornado.web.HTTPError(400)

        self.db_session.query(Rent).filter(Rent.id == rent_id).delete()
        self.db_session.commit()
        self.write('Deleted.')

    def put(self, rent_id=None):
        if rent_id is None:
            tornado.web.HTTPError(400)

        self.db_session.query(Rent).filter(Rent.id == rent_id).update({
        })
        self.db_session.commit()
        self.write('Updated.')


class FreeNumbersHandler(BaseHandler):
    def get(self, date=None):
        if date:
            target_date = datetime.datetime.strptime(date, DATE_FORMAT).date()
        else:
            target_date = datetime.datetime.now()

        keys = HotelNumber.number, HotelNumber.price_per_night, HotelNumber.description
        self.write(serialize(
            keys,
            self.db_session.query(*keys)
                .join(Rent)
                .filter(or_(Rent.from_date > target_date,
                            Rent.to_date < target_date))
                .all()
        ))


class RentedNumbersHandler(BaseHandler):
    def get(self, date=None):
        if date:
            target_date = datetime.datetime.strptime(date, DATE_FORMAT).date()
        else:
            target_date = datetime.datetime.now()

        keys = HotelNumber.number, HotelNumber.price_per_night, HotelNumber.description
        self.write(serialize(
            keys,
            self.db_session.query(*keys)
                .join(Rent)
                .filter(and_(Rent.from_date < target_date,
                            Rent.to_date > target_date))
                .all()
        ))

if __name__ == '__main__':
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(tornado.options.options.port)
    tornado.ioloop.IOLoop.instance().start()
