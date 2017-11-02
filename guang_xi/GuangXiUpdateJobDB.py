# coding=utf-8
import PackageTool
from gs.UpdateFromTable import UpdateFromTable
from GuangXiSearcher import GuangXiSearcher


class GuangXiUpdateJobDB(UpdateFromTable):

    def __init__(self):
        super(GuangXiUpdateJobDB, self).__init__()

    def set_config(self):
        self.searcher = GuangXiSearcher()

if __name__ == '__main__':
    job = GuangXiUpdateJobDB()
    job.run()
