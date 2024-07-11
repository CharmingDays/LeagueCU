import os
import yaml


def include_constructor(_,node):
    file_dir = os.path.dirname(__file__)
    main_dir = os.path.dirname(file_dir)
    if not os.path.exists(f'{main_dir}/config/{node.value}'):
        return yaml.load("""""",Loader=yaml.FullLoader)
    with open(f'{main_dir}/config/{node.value}','r') as file:
        return yaml.load(file,Loader=yaml.FullLoader)
    