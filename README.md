# LeagueCU
 A LCU python lib

This project ist still in working progress, if you want something to test with then use the python file.



## EXample:
```python

#create lobby and find match
import time
from lcu_client import LCU

lol = LCU()
lol.create_lobby('ranked','bottom','middle')
#you should wait at least 1 second for the client to create the lobby before doing other tasks or it might fail
time.sleep(1)
lol.send_invite("where is waldo")
def start_match():
    # wait for lobby to be ready to start
    if lol.ready_to_start:
        return lol.find_match()
    time.sleep(1)
    return start_match()

start_match()
# You can also run the auto accept match method from `Auto` class
auto = AutoFunctions()
auto.auto_accept_game(picks=['Jinx','Vayne'],bans=['Amumu','Pyke']) 
# This will start match, auto accept match and select/ban champions for you
```