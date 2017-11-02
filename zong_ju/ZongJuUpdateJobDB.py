# coding=utf-8
import PackageTool
from gs.UpdateFromTable import UpdateFromTable
from ZongJu import ZongJu


class ZongJuUpdateJobDB(UpdateFromTable):

    def __init__(self):
        super(ZongJuUpdateJobDB, self).__init__()

    def set_config(self):
        self.searcher = ZongJu()

if __name__ == '__main__':
    job = ZongJuUpdateJobDB()
    job.run()
