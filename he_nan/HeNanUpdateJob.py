# coding=utf-8
import PackageTool
from gs.GsSrcCousumer import GsSrcCousumer
from HeNanSearcher import HeNanSearcher


class HeNanUpdateJob(GsSrcCousumer):

    def __init__(self):
        super(HeNanUpdateJob, self).__init__()

    def set_config(self):
        self.searcher = HeNanSearcher()

if __name__ == '__main__':
    job = HeNanUpdateJob()
    job.run()
