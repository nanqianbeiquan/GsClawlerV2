# coding=gbk
import PackageTool
import sys
from gs.GsSrcCousumer import GsSrcCousumer
from GanSu import GanSuSearcher


class GanSuUpdateJob(GsSrcCousumer):

    def __init__(self):
        super(GanSuUpdateJob, self).__init__()
    
    def set_config(self):
        self.searcher = GanSuSearcher()

if __name__ == "__main__":
    job = GanSuUpdateJob()
    job.run()


