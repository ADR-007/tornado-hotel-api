import os
from http import HTTPStatus

import datetime
import tornado.web
import tornado.options
import tornado.httpserver
import tornado.ioloop
import tornado.escape
from sqlalchemy import create_engine, or_, and_
from sqlalchemy.orm import sessionmaker
from passlib.hash import pbkdf2_sha256

from database import Client, FirstName, LastName, Rent, HotelNumber, User
from tools import get_first_name_id, get_last_name_id, serialize

DATE_FORMAT = "%Y-%m-%d"

tornado.options.define('port', default=8888, help='Run on the given port', type=int)
tornado.options.define('database_connection_string', default='sqlite:///hotel.db', help='Select database', type=str)


class Application(tornado.web.Application):
    def __init__(self, *args, **kwargs):
        handlers = [
            # (r"/", RootHandler),
            (r"/login", LoginHandler),
            (r"/logout", LogoutHandler),
            (r"/client", ClientHandler),
            (r"/client/(\d+)", ClientHandler),
            (r"/rent", RentHandler),
            (r"/rent/(\d+)", RentHandler),
            (r"/number", NumbersHandler),
            (r"/number/(\d+)", NumbersHandler),
        ]
        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            # xsrf_cookies=True,
            cookie_secret="7Lslp9eZT;-B2D6/L6=mGppMJZj=<_Giw#;$CCTD6m8sp=-9f|",
            login_url="/login",
        )
        tornado.web.Application.__init__(self, handlers, *args, **{**kwargs, **settings})

        self.db_engine = create_engine(tornado.options.options.database_connection_string)
        self.db_session_maker = sessionmaker(bind=self.db_engine)
        self.db_session = self.db_session_maker()


class BaseHandler(tornado.web.RequestHandler):
    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        self.db_session = self.application.db_session

    def data_received(self, chunk):
        return super().data_received(chunk)

    def get_current_user(self):
        return self.get_secure_cookie("user")


class LoginHandler(BaseHandler):
    def get(self):
        if self.current_user:
            self.write(f'You already login as {self.current_user.decode()}')
        else:
            raise tornado.web.HTTPError(HTTPStatus.UNAUTHORIZED)

    def post(self):
        username = self.get_argument('username', '')
        password = self.get_argument('password', '')
        auth = self.check_permission(password, username)
        if auth:
            self.set_current_user(username)
        else:
            raise tornado.web.HTTPError(HTTPStatus.UNAUTHORIZED)

    def check_permission(self, username, password):
        rows = self.db_session.query(User.password_hash).filter(User.name == username).first()
        if rows:
            return pbkdf2_sha256.verify(password, rows[0])
        else:
            return False

    def set_current_user(self, user):
        if user:
            self.set_secure_cookie("user", tornado.escape.json_encode(user))
        else:
            self.clear_cookie("user")


class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie('user')
        self.redirect(self.get_argument('next', '/'))


class ClientHandler(BaseHandler):
    @tornado.web.authenticated
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

    @tornado.web.authenticated
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

    @tornado.web.authenticated
    def delete(self, client_id=None):
        if client_id is None:
            tornado.web.HTTPError(HTTPStatus.BAD_REQUEST)
        else:
            self.db_session.query(Client).filter(Client.id == client_id).delete()
            self.db_session.commit()

    @tornado.web.authenticated
    def put(self, client_id=None):
        if client_id is None:
            tornado.web.HTTPError(HTTPStatus.BAD_REQUEST)

        self.db_session.query(Client).filter(Client.id == client_id).update({
            Client.first_name_id: get_first_name_id(self.db_session, self.get_argument('first_name')),
            Client.last_name_id: get_last_name_id(self.db_session, self.get_argument('last_name')),
            Client.age: self.get_argument('age'),
            Client.passport_serial: self.get_argument('passport_serial'),
            Client.passport_number: self.get_argument('passport_number'),
        })
        self.db_session.commit()


class RentHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, rent_id=None):
        keys = (Rent.id, Rent.hotel_number, Rent.from_date, Rent.to_date, Rent.total_price, Client.id)
        query = self.db_session.query(*keys).join((Client, Rent.clients))
        if rent_id:
            query = query.filter(Rent.id == int(rent_id))

        self.write(serialize(keys, query.all()))

    @tornado.web.authenticated
    def post(self):
        price_per_day = self.db_session.query(HotelNumber.price_per_night) \
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
        self.set_status(HTTPStatus.CREATED)

    @tornado.web.authenticated
    def delete(self, rent_id=None):
        if rent_id is None:
            tornado.web.HTTPError(400)

        self.db_session.query(Rent).filter(Rent.id == rent_id).delete()
        self.db_session.commit()
        self.write('Deleted.')

    @tornado.web.authenticated
    def put(self, rent_id=None):
        if rent_id is None:
            tornado.web.HTTPError(400)

        self.db_session.query(Rent).filter(Rent.id == rent_id).update({
        })
        self.db_session.commit()
        self.write('Updated.')


class NumbersHandler(BaseHandler):
    def get(self, number=None):
        keys = HotelNumber.number, HotelNumber.price_per_night, HotelNumber.description
        query = self.db_session.query(*keys).join(Rent)
        if number:
            query = query.filter(Rent.hotel_number == int(number))
        else:
            state = self.get_argument('with_state', None)
            at_date_str = self.get_argument('at_date', None)
            if at_date_str:
                at_date = datetime.datetime.strptime(at_date_str, DATE_FORMAT).date()
            else:
                at_date = datetime.datetime.now()

            if state == 'free':
                query = query.filter(or_(Rent.from_date > at_date,
                                         Rent.to_date < at_date))
            elif state == 'rented':
                query = query.filter(and_(Rent.from_date < at_date,
                                          Rent.to_date > at_date))
        self.write(serialize(keys, query.all()))


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
