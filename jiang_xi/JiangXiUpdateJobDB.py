# coding=utf-8
import PackageTool
from gs.UpdateFromTable import UpdateFromTable
from JiangXiSearcher import JiangXiSearcher


class JiangXiUpdateJobDB(UpdateFromTable):

    def __init__(self):
        super(JiangXiUpdateJobDB, self).__init__()

    def set_config(self):
        self.searcher = JiangXiSearcher()

if __name__ == '__main__':
    job = JiangXiUpdateJobDB()
    job.run()
