# coding=utf-8
import PackageTool
from gs.GsSrcCousumer import GsSrcCousumer
from GuangXiSearcher import GuangXiSearcher


class GuangXiUpdateJob(GsSrcCousumer):

    def __init__(self):
        super(GuangXiUpdateJob, self).__init__()

    def set_config(self):
        self.searcher = GuangXiSearcher()

if __name__ == '__main__':
    job = GuangXiUpdateJob()
    job.run()
