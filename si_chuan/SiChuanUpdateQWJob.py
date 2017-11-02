# coding=gbk
import PackageTool
import sys
from gs.GsSrcCousumer import GsSrcCousumer
from SiChuanQW import SiChuanQW


class SiChuanUpdateJob(GsSrcCousumer):

    def __init__(self):
        super(SiChuanUpdateJob, self).__init__()

    def set_config(self):
        self.searcher = SiChuanQW()

if __name__ == "__main__":
    job = SiChuanUpdateJob()
    job.run()


