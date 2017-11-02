# coding=utf-8
import PackageTool
from gs.GsSrcCousumer import GsSrcCousumer
from ZheJiangSearcherQW import ZheJiangSearcherQW


class ZhejiangUpdateJobQW(GsSrcCousumer):

    def __init__(self):
        super(ZhejiangUpdateJobQW, self).__init__()

    def set_config(self):
        self.searcher = ZheJiangSearcherQW()

if __name__ == '__main__':
    job = ZhejiangUpdateJobQW()
    job.run()
