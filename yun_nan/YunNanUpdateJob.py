# coding=utf-8
import PackageTool
from gs.GsSrcCousumer import GsSrcCousumer
from YunNanSearcher import YunNanSearcher


class YunNanUpdateJob(GsSrcCousumer):

    def __init__(self):
        super(YunNanUpdateJob, self).__init__()

    def set_config(self):
        self.searcher = YunNanSearcher()

if __name__ == '__main__':
    job = YunNanUpdateJob()
    job.run()
