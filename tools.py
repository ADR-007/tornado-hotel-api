import json

import datetime

from database import FirstName, LastName


def get_first_name_id(session, name):
    name_id_list = session.query(FirstName.id).filter(FirstName.first_name == name).first()
    if name_id_list:
        return name_id_list[0]

    session.add(FirstName(first_name=name))
    session.commit()
    return get_first_name_id(session, name)


def get_last_name_id(session, name):
    name_id_list = session.query(LastName.id).filter(LastName.last_name == name).first()
    if name_id_list:
        return name_id_list[0]

    session.add(LastName(last_name=name))
    session.commit()
    return get_last_name_id(session, name)


def serialize(keys, values_list):
    return json.dumps(
        [{str(k): str(v) if isinstance(v, datetime.date) else v for k, v in zip(keys, row)} for row in values_list]
    )

