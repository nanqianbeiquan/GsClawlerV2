# coding=utf-8
import PackageTool
from gs.UpdateFromTable import UpdateFromTable
from FuJianSearcher import FuJianSearcher


class FuJianUpdateJobDB(UpdateFromTable):

    def __init__(self):
        super(FuJianUpdateJobDB, self).__init__()

    def set_config(self):
        self.searcher = FuJianSearcher()

if __name__ == '__main__':
    job = FuJianUpdateJobDB()
    job.run()
