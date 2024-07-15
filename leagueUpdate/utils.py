import os
import typing
import yaml
import asyncio
from lcu_driver.connection import Connection
import aiohttp


def verify_session(session:Connection):
    if session.closed:
        session = aiohttp.ClientSession(auth=aiohttp.BasicAuth('riot', session.auth_key), headers=session._headers)
    return session

def include_constructor(_,node):
    file_dir = os.path.dirname(__file__)
    main_dir = os.path.dirname(file_dir)
    if not os.path.exists(f'{main_dir}/config/{node.value}'):
        return yaml.load("""""",Loader=yaml.FullLoader)
    with open(f'{main_dir}/config/{node.value}','r') as file:
        return yaml.load(file,Loader=yaml.FullLoader)




async def verify_data(session:Connection,check:typing.Callable[[typing.Any,typing.Any],bool],uri,iteration=10,method='GET'):
    session = verify_session(session)
    resp = session.request(method,uri)
    data = await resp.json()
    result = check(data,resp)
    while not result and iteration > 0:
        await asyncio.sleep(1)
        resp = session.request(method,uri)
        data = await resp.json()
        iteration -= 1
        result = check(data,resp)
    return check(data,resp)
