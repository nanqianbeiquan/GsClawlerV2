# coding=gbk
import PackageTool
import sys
from gs.GsSrcCousumer import GsSrcCousumer
from HuBeiOld import HuBeiSearcher


class HuBeiUpdateJob(GsSrcCousumer):

    def __init__(self):
        super(HuBeiUpdateJob, self).__init__()
    
    def set_config(self):
        self.searcher = HuBeiSearcher()

if __name__ == "__main__":
    job = HuBeiUpdateJob()
    job.run()


