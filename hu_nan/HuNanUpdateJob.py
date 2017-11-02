# coding=gbk
import PackageTool
import sys
from gs.GsSrcCousumer import GsSrcCousumer
from HuNan import HuNanSearcher


class HuNanUpdateJob(GsSrcCousumer):

    def __init__(self):
        super(HuNanUpdateJob, self).__init__()
    
    def set_config(self):
        self.searcher = HuNanSearcher()

if __name__ == "__main__":
    job = HuNanUpdateJob()
    job.run()


