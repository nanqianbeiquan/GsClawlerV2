# coding=utf-8
import PackageTool
from gs.UpdateFromTable1 import UpdateFromTable1
from BeiJing import BeiJing


class BeiJingUpdateJobDB1(UpdateFromTable1):

    def __init__(self):
        super(BeiJingUpdateJobDB1, self).__init__()

    def set_config(self):
        self.searcher = BeiJing()
        # print u'*****'
        # self.init_kafka('GsSrc11')    #在searcher进行初始化，此处不再进行初始化

if __name__ == '__main__':
    job = BeiJingUpdateJobDB1()
    job.run()
