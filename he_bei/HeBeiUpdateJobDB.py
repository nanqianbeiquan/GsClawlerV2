# coding=utf-8
import PackageTool
from gs.UpdateFromTable import UpdateFromTable
from HeBei import HeBei


class HeBeiUpdateJobDB(UpdateFromTable):

    def __init__(self):
        super(HeBeiUpdateJobDB, self).__init__()

    def set_config(self):
        self.searcher = HeBei()

if __name__ == '__main__':
    job = HeBeiUpdateJobDB()
    job.run()
