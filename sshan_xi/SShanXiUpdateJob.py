# coding=utf-8
import PackageTool
from gs.GsSrcCousumer import GsSrcCousumer
from SShanXiSearcher import SShanXiSearcher


class  SShanXiUpdateJob(GsSrcCousumer):

    def __init__(self):
        super( SShanXiUpdateJob, self).__init__()

    def set_config(self):
        self.searcher =  SShanXiSearcher()

if __name__ == '__main__':
    job = SShanXiUpdateJob()
    job.run()
