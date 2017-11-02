# coding=utf-8
import PackageTool
from gs.GsSrcCousumer import GsSrcCousumer
from JiLinSearcher import JiLinSearcher


class JiLinUpdateJob(GsSrcCousumer):

    def __init__(self):
        super(JiLinUpdateJob, self).__init__()

    def set_config(self):
        self.searcher = JiLinSearcher()

if __name__ == '__main__':
    job = JiLinUpdateJob()
    job.run()
