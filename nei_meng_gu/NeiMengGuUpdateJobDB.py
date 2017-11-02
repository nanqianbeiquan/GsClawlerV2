# coding=utf-8
import PackageTool
from gs.UpdateFromTable import UpdateFromTable
from NeiMengGuSearcher import NeiMengGuSearcher


class NeiMengGuUpdateJobDB(UpdateFromTable):

    def __init__(self):
        super(NeiMengGuUpdateJobDB, self).__init__()

    def set_config(self):
        self.searcher = NeiMengGuSearcher()

if __name__ == '__main__':
    job =  NeiMengGuUpdateJobDB()
    job.run()
