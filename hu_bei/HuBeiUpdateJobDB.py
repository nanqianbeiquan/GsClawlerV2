# coding=gbk
import PackageTool
import sys
from gs.UpdateFromTable import UpdateFromTable
from HuBei import HuBeiSearcher


class HuBeiUpdateJobDB(UpdateFromTable):

    def __init__(self):
        super(HuBeiUpdateJobDB, self).__init__()
    
    def set_config(self):
        self.searcher = HuBeiSearcher()

if __name__ == "__main__":
    job = HuBeiUpdateJobDB()
    job.run()


