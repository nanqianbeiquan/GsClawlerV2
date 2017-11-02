# coding=utf-8
import PackageTool
from gs.UpdateFromTable import UpdateFromTable
from ShanmXi import ShanmXi


class ShanmXiUpdateJobDB(UpdateFromTable):

    def __init__(self):
        super(ShanmXiUpdateJobDB, self).__init__()

    def set_config(self):
        self.searcher = ShanmXi()
        # self.init_kafka('GsSrc23')    #在searcher进行初始化，此处不再进行初始化

if __name__ == '__main__':
    job = ShanmXiUpdateJobDB()
    job.run()
