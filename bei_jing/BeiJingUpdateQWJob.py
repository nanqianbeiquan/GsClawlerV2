# coding=utf-8
import PackageTool
from gs.GsSrcCousumer import GsSrcCousumer
from BeiJingQW import BeiJingQW


class BeiJingUpdateQWJob(GsSrcCousumer):

    def __init__(self):
        super(BeiJingUpdateQWJob, self).__init__()

    def set_config(self):
        self.searcher = BeiJingQW()
        # self.init_kafka('GsSrc11')    #在searcher进行初始化，此处不再进行初始化

if __name__ == '__main__':
    job = BeiJingUpdateQWJob()
    job.run()
