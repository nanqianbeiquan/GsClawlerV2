# coding=utf-8
import PackageTool
from gs.GsSrcCousumer import GsSrcCousumer
from HaiNanSearcher import HaiNanSearcher


class HaiNanUpdateJob(GsSrcCousumer):

    def __init__(self):
        super(HaiNanUpdateJob, self).__init__()

    def set_config(self):
        self.searcher = HaiNanSearcher()

if __name__ == '__main__':
    job = HaiNanUpdateJob()
    job.run()
