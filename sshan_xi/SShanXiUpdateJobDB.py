# coding=utf-8
import PackageTool
from gs.UpdateFromTable import UpdateFromTable
from SShanXiSearcher import SShanXiSearcher


class SShanXiUpdateJobDB(UpdateFromTable):

    def __init__(self):
        super(SShanXiUpdateJobDB, self).__init__()

    def set_config(self):
        self.searcher = SShanXiSearcher()

if __name__ == '__main__':
    job = SShanXiUpdateJobDB()
    job.run()
