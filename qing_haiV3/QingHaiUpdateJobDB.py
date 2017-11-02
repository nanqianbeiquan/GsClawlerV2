# coding=utf-8
import PackageTool
from gs.UpdateFromTable import UpdateFromTable
from QingHai import QingHai


class QingHaiUpdateJobDB(UpdateFromTable):

    def __init__(self):
        super(QingHaiUpdateJobDB, self).__init__()

    def set_config(self):
        self.searcher = QingHai()
        # self.init_kafka('GsSrc63')    #在searcher进行初始化，此处不再进行初始化

if __name__ == '__main__':
    job = QingHaiUpdateJobDB()
    job.run()
