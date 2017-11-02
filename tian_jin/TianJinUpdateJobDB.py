# coding=gbk
import PackageTool
import sys
from gs.UpdateFromTable import UpdateFromTable
from TianJin import TianJinSearcher


class TianJinUpdateJobDB(UpdateFromTable):

    def __init__(self):
        super(TianJinUpdateJobDB, self).__init__()
    
    def set_config(self):
        self.searcher = TianJinSearcher()

if __name__ == "__main__":
    job = TianJinUpdateJobDB()
    job.run()


