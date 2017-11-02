# coding=utf-8
import PackageTool
from gs.GsSrcCousumer import GsSrcCousumer
from ZheJiangSearcher import ZheJiangSearcher


class ZhejiangUpdateJob(GsSrcCousumer):

    def __init__(self):
        super(ZhejiangUpdateJob, self).__init__()

    def set_config(self):
        self.searcher = ZheJiangSearcher()

if __name__ == '__main__':
    job = ZhejiangUpdateJob()
    job.run()
