# coding=utf-8
import PackageTool
from gs.GsSrcCousumer import GsSrcCousumer
from HeBei import HeBei


class HeBeiUpdateJob(GsSrcCousumer):

    def __init__(self):
        super(HeBeiUpdateJob, self).__init__()

    def set_config(self):
        self.searcher = HeBei()

if __name__ == '__main__':
    job = HeBeiUpdateJob()
    job.run()
