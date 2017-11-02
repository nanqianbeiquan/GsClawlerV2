# coding=utf-8
import PackageTool
from gs.UpdateFromTable import UpdateFromTable
from HaiNanSearcher import HaiNanSearcher


class HaiNanUpdateJobDB(UpdateFromTable):

    def __init__(self):
        super(HaiNanUpdateJobDB, self).__init__()

    def set_config(self):
        self.searcher = HaiNanSearcher()

if __name__ == '__main__':
    job = HaiNanUpdateJobDB()
    job.run()
