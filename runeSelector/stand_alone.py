"""
If you dont' wish to run the sever to select custom runes for champions, you can 
run this stand-alone script file to do the same but not as effective as running the server
NOTE: You will need to have the League of Legends Client Signed in to do this.

Steps:
    1: Login to your LoL client
    2: Go to your collections and create a custom rune and give it the champion's name.
        NOTE: when naming the rune, do not include spaces or none alphabet characters like the single quote (') for champions that uses it, just use camelCase
        Ex: Kai'Sa --> KaiSa | Kog'Maw --> KogMaw
    3: Run this script (stand_alone.py) and the script will save the rune to the runes.yaml file and delete the newly created rune for you to restart the process.
    4: Repeat until you have created all the custom runes per champion you want. You do not have to create it for all champions, just for the ones you want the auto runes to work on.
"""