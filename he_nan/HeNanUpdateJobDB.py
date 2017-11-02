# coding=utf-8
import PackageTool
from gs.UpdateFromTable import UpdateFromTable
from HeNanSearcher import HeNanSearcher


class HeNanUpdateJobDB(UpdateFromTable):

    def __init__(self):
        super(HeNanUpdateJobDB, self).__init__()

    def set_config(self):
        self.searcher = HeNanSearcher()

if __name__ == '__main__':
    job = HeNanUpdateJobDB()
    job.run()
