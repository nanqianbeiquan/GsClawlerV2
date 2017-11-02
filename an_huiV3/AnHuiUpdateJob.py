# coding=utf-8
import PackageTool
from gs.GsSrcCousumer import GsSrcCousumer
from AnHui import AnHui


class AnHuiUpdateJob(GsSrcCousumer):

    def __init__(self):
        super(AnHuiUpdateJob, self).__init__()

    def set_config(self):
        self.searcher = AnHui()
        # self.init_kafka('GsSrc34')    #在searcher进行初始化，此处不再进行初始化

if __name__ == '__main__':
    job = AnHuiUpdateJob()
    job.run()
