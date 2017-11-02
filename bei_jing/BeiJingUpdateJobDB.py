# coding=utf-8
import PackageTool
from gs.UpdateFromTable import UpdateFromTable
from BeiJing import BeiJing


class BeiJingUpdateJobDB(UpdateFromTable):

    def __init__(self):
        super(BeiJingUpdateJobDB, self).__init__()

    def set_config(self):
        self.searcher = BeiJing()
        # print u'*****'
        # self.init_kafka('GsSrc11')    #在searcher进行初始化，此处不再进行初始化

if __name__ == '__main__':
    job = BeiJingUpdateJobDB()
    job.run()
