# coding=gbk
import PackageTool
import sys
from gs.UpdateFromTable import UpdateFromTable
from GanSu import GanSuSearcher


class GanSuUpdateJobDB(UpdateFromTable):

    def __init__(self):
        super(GanSuUpdateJobDB, self).__init__()
    
    def set_config(self):
        self.searcher = GanSuSearcher()

if __name__ == "__main__":
    job = GanSuUpdateJobDB()
    job.run()


