import os
import yaml
import asyncio


def include_constructor(_,node):
    file_dir = os.path.dirname(__file__)
    main_dir = os.path.dirname(file_dir)
    if not os.path.exists(f'{main_dir}/config/{node.value}'):
        return yaml.load("""""",Loader=yaml.FullLoader)
    with open(f'{main_dir}/config/{node.value}','r') as file:
        return yaml.load(file,Loader=yaml.FullLoader)
    


async def wait_until(time_left:float,delay:int) -> None:
    """Waits until the time left is >= than the delay

    Args:
        time_left (float): the amount of time left in milliseconds
        delay (int): the amount of time to wait in seconds
    """
    while (time_left -1000) > delay and delay > 1:
        await asyncio.sleep(1)
        delay-=1
        time_left-=1000

