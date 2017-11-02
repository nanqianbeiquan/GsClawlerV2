# coding=gbk
import PackageTool
import sys
from gs.GsSrcCousumer import GsSrcCousumer
from TianJin import TianJinSearcher


class TianJinUpdateJob(GsSrcCousumer):

    def __init__(self):
        super(TianJinUpdateJob, self).__init__()
    
    def set_config(self):
        self.searcher = TianJinSearcher()

if __name__ == "__main__":
    job = TianJinUpdateJob()
    job.run()


