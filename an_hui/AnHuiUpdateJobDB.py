# coding=utf-8
import PackageTool
from gs.UpdateFromTable import UpdateFromTable
from AnHui import AnHui


class AnHuiUpdateJobDB(UpdateFromTable):

    def __init__(self):
        super(AnHuiUpdateJobDB, self).__init__()

    def set_config(self):
        self.searcher = AnHui()
        # self.init_kafka('GsSrc34')    #在searcher进行初始化，此处不再进行初始化

if __name__ == '__main__':
    job = AnHuiUpdateJobDB()
    job.run()
