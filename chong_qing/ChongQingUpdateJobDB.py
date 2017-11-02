# coding=utf-8
import PackageTool
from gs.UpdateFromTable import UpdateFromTable
from ChongQingSearcher import ChongQingSearcher


class ChongQingUpdateJobDB(UpdateFromTable):

    def __init__(self):
        super(ChongQingUpdateJobDB, self).__init__()

    def set_config(self):
        self.searcher = ChongQingSearcher()

if __name__ == '__main__':
    job = ChongQingUpdateJobDB()
    job.run()
