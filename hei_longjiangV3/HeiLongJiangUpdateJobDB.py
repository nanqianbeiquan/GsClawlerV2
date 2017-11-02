# coding=utf-8
import PackageTool
from gs.UpdateFromTable import UpdateFromTable
from HeiLongJiang import HeiLongJiang


class HeiLongJiangUpdateJobDB(UpdateFromTable):

    def __init__(self):
        super(HeiLongJiangUpdateJobDB, self).__init__()

    def set_config(self):
        self.searcher = HeiLongJiang()
        # print u'*****'
        # self.init_kafka('GsSrc11')    #在searcher进行初始化，此处不再进行初始化

if __name__ == '__main__':
    job = HeiLongJiangUpdateJobDB()
    job.run()