# coding=utf-8
import PackageTool
from gs.UpdateFromTable import UpdateFromTable
from NingXia import NingXia


class NingXiaUpdateJobDB(UpdateFromTable):

    def __init__(self):
        super(NingXiaUpdateJobDB, self).__init__()

    def set_config(self):
        self.searcher = NingXia()
        # self.init_kafka('GsSrc64')    #在searcher进行初始化，此处不再进行初始化

if __name__ == '__main__':
    job = NingXiaUpdateJobDB()
    job.run()
