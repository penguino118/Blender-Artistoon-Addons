import re
import math, mathutils
from itertools import groupby


def all_equal(iterable):
    g = groupby(iterable)
    return next(g, True) and not next(g, False)

def flip_zy(vector):
    rotation = mathutils.Euler((math.radians(90.0), 0.0, 0.0), 'XYZ')
    vector.rotate(rotation)

def flip_yz(vector):
    rotation = mathutils.Euler((math.radians(-90.0), 0.0, 0.0), 'XYZ')
    vector.rotate(rotation)

# to properly sort children names
# https://stackoverflow.com/questions/58861558/natural-sorting-of-a-list-in-python3

def atoi(text):
    return int(text) if text.isdigit() else text

def natural_keys(text):
    '''
    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    (See Toothy's implementation in the comments)
    '''
    return [ atoi(c) for c in re.split(r'(\d+)', text) ]