# coding=utf-8
import PackageTool
from gs.GsSrcCousumer import GsSrcCousumer
from GuangdongShenzhen import GuangdongShenzhen
from Guangdong import Guangdong
import time
import traceback


class GuangdongUpdateJob(GsSrcCousumer):

    def __init__(self):
        super(GuangdongUpdateJob, self).__init__()

    def set_config(self):
        self.searcher = Guangdong()

if __name__ == '__main__':
    job = GuangdongUpdateJob()
    job.run()


