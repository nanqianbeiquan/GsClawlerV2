# coding=utf-8
import PackageTool
from gs.GsSrcCousumer import GsSrcCousumer
from FuJianSearcher import FuJianSearcher


class FuJianUpdateJob(GsSrcCousumer):

    def __init__(self):
        super(FuJianUpdateJob, self).__init__()

    def set_config(self):
        self.searcher = FuJianSearcher()

if __name__ == '__main__':
    job = FuJianUpdateJob()
    job.run()
