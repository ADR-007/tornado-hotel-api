import string
from http import HTTPStatus
import logging

import datetime
import requests
import json
import random
import unittest
from typing import List, Dict, Any

from app import DATE_FORMAT
from sample_data import insert_sample_data_to_database


class TestHotelAPI(unittest.TestCase):
    ROOT_URL = 'http://localhost:8888'

    USERNAME = 'admin'
    PASSWORD = 'admin'

    LOGIN_COMMAND = '/login'
    CLIENT_COMMAND = '/client'
    RENT_COMMAND = '/rent'
    NUMBER_COMMAND = '/number'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__auth_cookie = None

    @property
    def _url(self):
        return self.ROOT_URL

    @staticmethod
    def _get_list_of(rows: List[Dict[str, Any]], parameter_name):
        return [row[parameter_name] for row in rows]

    @property
    def _auth_cookie(self):
        if not self.__auth_cookie:
            self.__auth_cookie = requests.post(self.ROOT_URL + self.LOGIN_COMMAND,
                                               dict(username=self.USERNAME, password=self.PASSWORD)).cookies
        return self.__auth_cookie


class TestHotelLogin(TestHotelAPI):
    def test_login(self):
        self.assertEqual(requests.post(self._url, dict(username=self.USERNAME, password=self.PASSWORD)).status_code,
                         HTTPStatus.OK)

    def test_incorrect_login(self):
        self.assertEqual(requests.post(self._url, dict(username='wrong user', password='wrong password')).status_code,
                         HTTPStatus.UNAUTHORIZED)

    def test_without_login(self):
        self.assertEqual(requests.get(self._url).status_code, HTTPStatus.UNAUTHORIZED)

    @property
    def _url(self):
        return self.ROOT_URL + self.LOGIN_COMMAND


class HotelDataAccessTester(TestHotelAPI):
    @classmethod
    def setUpClass(cls):
        if cls is HotelDataAccessTester:
            insert_sample_data_to_database()
            raise unittest.SkipTest("Skip parent class of tests")
        super().setUpClass()

    def setUp(self):
        pass
        # insert_sample_data_to_database()

    def test_permission(self):
        self.assertEqual(requests.get(self._url).status_code, HTTPStatus.UNAUTHORIZED, msg='on GET request')
        self.assertEqual(requests.post(self._url).status_code, HTTPStatus.FORBIDDEN, msg='on POST request')
        self.assertEqual(requests.put(self._url).status_code, HTTPStatus.FORBIDDEN, msg='on PUT request')
        self.assertEqual(requests.delete(self._url).status_code, HTTPStatus.FORBIDDEN, msg='on DELETE request')

    def test_bad_request(self):
        for method, method_name in (
                (requests.post, 'POST'),
                (requests.put, 'PUT'),
                (requests.delete, 'DELETE'),

        ):
            self.assertEqual(method(self._url, cookies=self._auth_cookie).status_code, HTTPStatus.BAD_REQUEST,
                             msg=f'on {method_name} request')

    def test_get_all(self):
        self.assertGreater(len(self._get_all()), 0)

    def test_get_by_id(self):
        all_rows = self._get_all()
        row_id = random.choice(self._get_list_of(all_rows, self._col_prefix + self._primary_key))

        response = requests.get(self._url, data={self._primary_key: row_id}, cookies=self._auth_cookie)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        row = response.json()
        self.assertEqual(row, [row for row in all_rows if row[self._col_prefix + self._primary_key] == row_id])

    def test_delete(self):
        row_id = random.choice(self._get_list_of(self._get_all(), f'{self._col_prefix}{self._primary_key}'))
        requests.delete(self._url, data={self._primary_key: row_id}, cookies=self._auth_cookie)
        self.assertFalse([row for row in self._get_all() if row[f'{self._col_prefix}{self._primary_key}'] == row_id])

    def _get_all(self) -> List[Dict[str, Any]]:
        response = requests.get(self._url, cookies=self._auth_cookie)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        return response.json()

    @property
    def _col_prefix(self):
        return ''

    @property
    def _primary_key(self):
        return 'id'


class TestHotelClient(HotelDataAccessTester):
    def test_add(self):
        passport_number = self._get_random_passport_number(
            self._get_list_of(self._get_all(), f'{self._col_prefix}passport_number')
        )
        self.assertEqual(
            requests.post(self._url, self._new_client_parameters(passport_number),
                          cookies=self._auth_cookie).status_code,
            HTTPStatus.OK
        )

        self.assertTrue([row for row in self._get_all()
                         if row[f'{self._col_prefix}passport_number'] == passport_number])

    def test_change(self):
        row_id = random.choice(self._get_list_of(self._get_all(), f'{self._col_prefix}id'))
        passport_number = self._get_random_passport_number(self._get_list_of(self._get_all(),
                                                                             f'{self._col_prefix}passport_number'))
        new_client = {self._primary_key: row_id, **self._new_client_parameters(passport_number)}
        self.assertEqual(
            requests.put(self._url,
                         data=new_client,
                         cookies=self._auth_cookie).status_code,
            HTTPStatus.OK
        )

        self.assertTrue([row for row in self._get_all()
                         if row[f'{self._col_prefix}passport_number'] == passport_number])

    @staticmethod
    def _new_client_parameters(passport_number):
        return dict(
            first_name=random.choice('Firstname' + ''.join(random.choice(string.ascii_lowercase)
                                                           for _ in range(random.randint(3, 5)))),
            last_name=random.choice('Lastname' + ''.join(random.choice(string.ascii_lowercase)
                                                         for _ in range(random.randint(3, 5)))),
            age=random.randint(18, 99),
            passport_serial=''.join(random.choice(string.ascii_uppercase) for _ in range(2)),
            passport_number=passport_number
        )

    @staticmethod
    def _get_random_passport_number(black_list: List[str]):
        while True:
            number = ''.join(str(random.randint(0, 9)) for _ in range(9))
            if number not in black_list:
                return number

    @property
    def _url(self):
        return self.ROOT_URL + self.CLIENT_COMMAND

    @property
    def _col_prefix(self):
        return 'Client.'


class TestHotelRent(HotelDataAccessTester):
    def test_add(self):
        new_rent = self._new_rent()
        self.assertEqual(
            requests.post(self._url, new_rent, cookies=self._auth_cookie).status_code,
            HTTPStatus.OK
        )

        self._check_exists(new_rent)

    def test_change(self):
        rent_id = random.choice(self._get_all())[self._col_prefix + self._primary_key]
        new_rent = self._new_rent()
        self.assertEqual(
            requests.put(self._url, {self._primary_key: rent_id, **new_rent}, cookies=self._auth_cookie).status_code,
            HTTPStatus.OK
        )

        self._check_exists(new_rent)

    def _check_exists(self, rent, rent_id=None):
        all_rows = self._get_all()
        self.assertEqual(len([row for row in all_rows
                              if row[f'{self._col_prefix}hotel_number'] == rent['hotel_number']
                              and row[f'{self._col_prefix}from_date'] == str(rent['from_date'])
                              and row[f'{self._col_prefix}to_date'] == str(rent['to_date'])
                              and (row[f'{self._col_prefix}{self._primary_key}'] == rent_id if rent_id else True)]), 2)

    def _new_rent(self):
        today = datetime.date.today()
        from_date = today + datetime.timedelta(days=random.randrange(10))
        to_date = from_date + datetime.timedelta(days=random.randrange(10))
        all_clients_row = requests.get(self.ROOT_URL + self.CLIENT_COMMAND, cookies=self._auth_cookie).json()
        all_numbers_row = requests.get(self.ROOT_URL + self.NUMBER_COMMAND, cookies=self._auth_cookie).json()
        number = random.choice(self._get_list_of(all_numbers_row, f'HotelNumber.number'))
        random.shuffle(all_clients_row)
        client_id_list = [
            all_clients_row[0]['Client.id'],
            all_clients_row[1]['Client.id'],
        ]
        return dict(hotel_number=number, from_date=from_date, to_date=to_date, client_id=client_id_list)

    @property
    def _url(self):
        return self.ROOT_URL + self.RENT_COMMAND

    @property
    def _col_prefix(self):
        return 'Rent.'


class TestHotelNumber(HotelDataAccessTester):
    def test_get_filters(self):
        current_rented = self._make_new_number()
        future_rented = self._make_new_number()
        requests.post(self._url, data=current_rented, cookies=self._auth_cookie)
        requests.post(self._url, data=future_rented, cookies=self._auth_cookie)

        clients_id = [row['Client.id'] for row in requests.get(self.ROOT_URL + self.CLIENT_COMMAND,
                                                               cookies=self._auth_cookie).json()[:2]]

        requests.post(self.ROOT_URL + self.RENT_COMMAND, dict(
            hotel_number=current_rented[self._primary_key],
            from_date=(datetime.datetime.now() + datetime.timedelta(days=-2)).date(),
            to_date=(datetime.datetime.now() + datetime.timedelta(days=2)).date(),
            client_id=clients_id
        ), cookies=self._auth_cookie)

        requests.post(self.ROOT_URL + self.RENT_COMMAND, dict(
            hotel_number=future_rented[self._primary_key],
            from_date=(datetime.datetime.now() + datetime.timedelta(days=2)).date(),
            to_date=(datetime.datetime.now() + datetime.timedelta(days=4)).date(),
            client_id=clients_id
        ), cookies=self._auth_cookie)

        future = (datetime.datetime.now() + datetime.timedelta(days=3)).date()
        for date, state, hotel_number, excepted_list_length in (
                (None, 'free', current_rented, 0),
                (None, 'free', future_rented, 1),
                (None, 'rented', current_rented, 2),  # two clients => two rows of result
                (None, 'rented', future_rented, 0),
                (future, 'free', current_rented, 1),
                (future, 'free', future_rented, 0),
                (future, 'rented', current_rented, 0),
                (future, 'rented', future_rented, 2),
        ):
            parameters = {'state': state}
            if date:
                parameters['date'] = date

            self.assertEqual(len([row for row in requests.get(self._url, parameters, cookies=self._auth_cookie).json()
                                  if row[self._col_prefix + self._primary_key] == hotel_number[self._primary_key]]),
                             excepted_list_length)

    def test_add(self):
        new_number = self._make_new_number()
        self.assertEqual(requests.post(self._url, data=new_number, cookies=self._auth_cookie).status_code,
                         HTTPStatus.OK)

        self.assertTrue(new_number[self._primary_key] in
                        self._get_list_of(self._get_all(), self._col_prefix + self._primary_key))

    def test_change(self):
        new_number = self._make_new_number(random.choice(self._get_list_of(self._get_all(),
                                                                           self._col_prefix + self._primary_key)))

        self.assertEqual(requests.put(self._url, new_number, cookies=self._auth_cookie).status_code,
                         HTTPStatus.OK)

        self.assertEqual(len([row for row in self._get_all() if
                              all(row[self._col_prefix + key] == new_number[key] for key in new_number.keys())]), 1)

    def _make_new_number(self, number=None):
        if number is None:
            all_numbers = self._get_list_of(self._get_all(), self._col_prefix + self._primary_key)
            while True:
                number = random.randint(1, 1000)
                if number not in all_numbers:
                    break
        return dict(number=number,
                    price_per_night=random.randint(10, 10900) / 10,
                    description=''.join(random.choice(string.ascii_letters) for _ in range(random.randint(5, 50))))

    @property
    def _url(self):
        return self.ROOT_URL + self.NUMBER_COMMAND

    @property
    def _col_prefix(self):
        return 'HotelNumber.'

    @property
    def _primary_key(self):
        return 'number'


if __name__ == '__main__':
    insert_sample_data_to_database()
    unittest.main()
