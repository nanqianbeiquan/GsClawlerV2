# coding=utf-8
import PackageTool
from gs.GsSrcCousumer import GsSrcCousumer
from HeiLongJiang import HeiLongJiang


class HeiLongJiangUpdateJob(GsSrcCousumer):

    def __init__(self):
        super(HeiLongJiangUpdateJob, self).__init__()

    def set_config(self):
        self.searcher = HeiLongJiang()
        # self.init_kafka('GsSrc23')    #在searcher进行初始化，此处不再进行初始化

if __name__ == '__main__':
    job = HeiLongJiangUpdateJob()
    job.run()
