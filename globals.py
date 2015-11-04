# -*- coding: utf-8 -*-
"""
Created on Wed Nov  4 16:19:46 2015

@author: mints
"""
from jinja2 import Environment, FileSystemLoader

JINJA = Environment(loader=FileSystemLoader('.'))