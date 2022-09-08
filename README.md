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
lol.send_invite("where is waldo") #of course in real example you'd wait a few seconds/minutes for the person to respond before starting.
lol.find_match()
```