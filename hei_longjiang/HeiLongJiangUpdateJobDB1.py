# coding=utf-8
import PackageTool
from gs.UpdateFromTable1 import UpdateFromTable1
from HeiLongJiang import HeiLongJiang


class HeiLongJiangUpdateJobDB1(UpdateFromTable1):

    def __init__(self):
        super(HeiLongJiangUpdateJobDB1, self).__init__()

    def set_config(self):
        self.searcher = HeiLongJiang()
        # self.init_kafka('GsSrc23')    #在searcher进行初始化，此处不再进行初始化

if __name__ == '__main__':
    job = HeiLongJiangUpdateJobDB1()
    job.run()
