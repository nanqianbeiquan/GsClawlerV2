# coding=utf-8

import requests
import os
from bs4 import BeautifulSoup
import json
import re
import datetime
from requests.exceptions import RequestException
import sys
import time
import random
from lxml import html
from GuangdongConfig import *
import subprocess
from gs.ProxyConf import ProxyConf
from gs.ProxyConf import key1 as app_key
from gs.TimeUtils import get_cur_time
# from lxml import XMLSyntaxError
import traceback
from gs.Searcher import Searcher, save_dead_company

def parse_detail_shenzhen(tag_a):
    pass
