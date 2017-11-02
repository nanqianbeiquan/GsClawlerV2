# coding=gbk
import PackageTool
import sys
from gs.GsSrcCousumer import GsSrcCousumer
from SiChuan import SiChuanSearcher


class SiChuanUpdateJob(GsSrcCousumer):

    def __init__(self):
        super(SiChuanUpdateJob, self).__init__()
    
    def set_config(self):
        self.searcher = SiChuanSearcher()

if __name__ == "__main__":
    job = SiChuanUpdateJob()
    job.run()


