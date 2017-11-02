# coding=utf-8

import requests
import os
from bs4 import BeautifulSoup
import json
import re
import datetime
from requests.exceptions import RequestException
import sys
from lxml import html
from GuangdongConfig import *
from gs.ProxyConf import ProxyConf
from gs.ProxyConf import key1 as app_key
from gs.TimeUtils import get_cur_time
from gs.Searcher import Searcher, save_dead_company
import uuid


def parse_detail_guangzhou(tag_a):
    pass


