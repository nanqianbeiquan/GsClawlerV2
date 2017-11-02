# coding=utf-8
import PackageTool
from gs.UpdateFromTable import UpdateFromTable
from XinJiang import XinJiang


class XinJiangUpdateJobDB(UpdateFromTable):

    def __init__(self):
        super(XinJiangUpdateJobDB, self).__init__()

    def set_config(self):
        self.searcher = XinJiang()
        # self.init_kafka('GsSrc65')    #在searcher进行初始化，此处不再进行初始化

if __name__ == '__main__':
    job = XinJiangUpdateJobDB()
    job.run()
