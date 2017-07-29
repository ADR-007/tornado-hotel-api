import string
from http import HTTPStatus
import logging

import requests
import json
import random
import unittest
from typing import List, Dict, Any

from sample_data import insert_sample_data_to_database


class TestHotelAPI(unittest.TestCase):
    ROOT_URL = 'http://localhost:8888'

    USERNAME = 'admin'
    PASSWORD = 'admin'

    LOGIN_COMMAND = '/login'
    CLIENT_COMMAND = '/client'
    RENT_COMMAND = '/rent'

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

    def test_get_all(self):
        self.assertGreater(len(self._get_all()), 0)

    def test_get_by_id(self):
        all_rows = self._get_all()
        row_id = random.choice(self._get_list_of(all_rows, f'{self._col_prefix}id'))

        row = requests.get(self._url + f'/{row_id}', cookies=self._auth_cookie).json()
        self.assertEqual(row, [row for row in all_rows if row[f'{self._col_prefix}id'] == row_id])

    def test_delete(self):
        row_id = random.choice(self._get_list_of(self._get_all(), f'{self._col_prefix}id'))
        requests.delete(self._url + f'/{row_id}', cookies=self._auth_cookie)
        self.assertFalse([row for row in self._get_all() if row[f'{self._col_prefix}id'] == row_id])

    def _get_all(self) -> List[Dict[str, Any]]:
        return requests.get(self._url, cookies=self._auth_cookie).json()

    @property
    def _col_prefix(self):
        return ''


class TestHotelClient(HotelDataAccessTester):
    def test_add(self):
        passport_number = self._get_random_passport_number(
            self._get_list_of(self._get_all(), f'{self._col_prefix}passport_number')
        )
        requests.post(self._url, self._new_client_parameters(passport_number), cookies=self._auth_cookie)

        self.assertTrue([row for row in self._get_all()
                         if row[f'{self._col_prefix}passport_number'] == passport_number])

    def test_change(self):
        all_rows = self._get_all()
        row_id = random.choice(self._get_list_of(all_rows, f'{self._col_prefix}id'))
        passport_number = self._get_random_passport_number(self._get_list_of(self._get_all(),
                                                                             f'{self._col_prefix}passport_number'))
        requests.put(self._url + f'/{row_id}', self._new_client_parameters(passport_number), cookies=self._auth_cookie)

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
    @property
    def _url(self):
        return self.ROOT_URL + self.RENT_COMMAND

    @property
    def _col_prefix(self):
        return 'Rent.'


if __name__ == '__main__':
    insert_sample_data_to_database()
    unittest.main()
