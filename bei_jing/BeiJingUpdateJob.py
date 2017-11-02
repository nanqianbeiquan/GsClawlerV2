# coding=utf-8
import PackageTool
from gs.GsSrcCousumer import GsSrcCousumer
from BeiJing import BeiJing


class BeiJingUpdateJob(GsSrcCousumer):

    def __init__(self):
        super(BeiJingUpdateJob, self).__init__()

    def set_config(self):
        self.searcher = BeiJing()
        # self.init_kafka('GsSrc11')    #在searcher进行初始化，此处不再进行初始化

if __name__ == '__main__':
    job = BeiJingUpdateJob()
    job.run()
