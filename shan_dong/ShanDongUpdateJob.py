# coding=utf-8
import PackageTool
from gs.GsSrcCousumer import GsSrcCousumer
from ShanDongSearcher import ShanDongSearcher


class ShanDongUpdateJob(GsSrcCousumer):

    def __init__(self):
        super(ShanDongUpdateJob, self).__init__()

    def set_config(self):
        self.searcher = ShanDongSearcher()

if __name__ == '__main__':
    job = ShanDongUpdateJob()
    job.run()
