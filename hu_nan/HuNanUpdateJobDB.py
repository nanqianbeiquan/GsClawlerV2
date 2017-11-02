# coding=gbk
import PackageTool
import sys
from gs.UpdateFromTable import UpdateFromTable
from HuNan import HuNanSearcher


class HuNanUpdateJobDB(UpdateFromTable):

    def __init__(self):
        super(HuNanUpdateJobDB, self).__init__()
    
    def set_config(self):
        self.searcher = HuNanSearcher()

if __name__ == "__main__":
    job = HuNanUpdateJobDB()
    job.run()


