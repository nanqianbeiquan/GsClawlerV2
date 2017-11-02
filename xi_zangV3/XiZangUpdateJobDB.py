# coding=utf-8
import PackageTool
from gs.UpdateFromTable import UpdateFromTable
from XiZang import XiZang


class XiZangUpdateJobDB(UpdateFromTable):

    def __init__(self):
        super(XiZangUpdateJobDB, self).__init__()

    def set_config(self):
        self.searcher = XiZang()
        # self.init_kafka('GsSrc54')    #在searcher进行初始化，此处不再进行初始化

if __name__ == '__main__':
    job = XiZangUpdateJobDB()
    job.run()
