# coding=utf-8
import PackageTool
from gs.UpdateFromTable import UpdateFromTable
from ZheJiangSearcher import ZheJiangSearcher


class ZhejiangUpdateJobDB(UpdateFromTable):

    def __init__(self):
        super(ZhejiangUpdateJobDB, self).__init__()

    def set_config(self):
        self.searcher = ZheJiangSearcher()

if __name__ == '__main__':
    job = ZhejiangUpdateJobDB()
    job.run()
