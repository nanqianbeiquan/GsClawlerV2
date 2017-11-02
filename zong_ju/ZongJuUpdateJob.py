# coding=utf-8
import PackageTool
from gs.GsSrcCousumer import GsSrcCousumer
from ZongJu import ZongJu


class ZongJuUpdateJob(GsSrcCousumer):

    def __init__(self):
        super(ZongJuUpdateJob, self).__init__()

    def set_config(self):
        self.searcher = ZongJu()

if __name__ == '__main__':
    job = ZongJuUpdateJob()
    job.run()
