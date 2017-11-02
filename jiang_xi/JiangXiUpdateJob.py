# coding=utf-8
import PackageTool
from gs.GsSrcCousumer import GsSrcCousumer
from JiangXiSearcher import JiangXiSearcher


class JiangXiUpdateJob(GsSrcCousumer):

    def __init__(self):
        super(JiangXiUpdateJob, self).__init__()

    def set_config(self):
        self.searcher = JiangXiSearcher()

if __name__ == '__main__':
    job = JiangXiUpdateJob()
    job.run()
