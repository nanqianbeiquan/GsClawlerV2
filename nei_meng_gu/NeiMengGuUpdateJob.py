# coding=utf-8
import PackageTool
from gs.GsSrcCousumer import GsSrcCousumer
from NeiMengGuSearcher import NeiMengGuSearcher


class  NeiMengGuUpdateJob(GsSrcCousumer):

    def __init__(self):
        super( NeiMengGuUpdateJob, self).__init__()

    def set_config(self):
        self.searcher =  NeiMengGuSearcher()

if __name__ == '__main__':
    job =  NeiMengGuUpdateJob()
    job.run()
