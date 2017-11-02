# coding=utf-8
import PackageTool
from gs.GsSrcCousumer import GsSrcCousumer
from ChongQingSearcher import ChongQingSearcher


class ChongQingUpdateJob(GsSrcCousumer):

    def __init__(self):
        super(ChongQingUpdateJob, self).__init__()

    def set_config(self):
        self.searcher = ChongQingSearcher()

if __name__ == '__main__':
    job = ChongQingUpdateJob()
    job.run()
