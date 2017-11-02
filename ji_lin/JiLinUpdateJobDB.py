# coding=utf-8
import PackageTool
from gs.UpdateFromTable import UpdateFromTable
from JiLinSearcher import JiLinSearcher


class JiLinUpdateJobDB(UpdateFromTable):

    def __init__(self):
        super(JiLinUpdateJobDB, self).__init__()

    def set_config(self):
        self.searcher = JiLinSearcher()

if __name__ == '__main__':
    job = JiLinUpdateJobDB()
    job.run()
