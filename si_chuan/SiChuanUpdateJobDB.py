# coding=gbk
import PackageTool
import sys
from gs.UpdateFromTable import UpdateFromTable
from SiChuan import SiChuanSearcher


class SiChuanUpdateJobDB(UpdateFromTable):

    def __init__(self):
        super(SiChuanUpdateJobDB, self).__init__()
    
    def set_config(self):
        self.searcher = SiChuanSearcher()

if __name__ == "__main__":
    job = SiChuanUpdateJobDB()
    job.run()


