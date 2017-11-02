# coding=utf-8
import PackageTool
from gs.UpdateFromTable import UpdateFromTable
from GuangdongShenzhen import GuangdongShenzhen
from GongShang import Guangdong
import time
import traceback


class GuangdongUpdateJobDB(UpdateFromTable):

    def __init__(self):
        super(GuangdongUpdateJobDB, self).__init__()

    def set_config(self):
        self.searcher = Guangdong()

if __name__ == '__main__':
    job = GuangdongUpdateJobDB()
    job.run()


