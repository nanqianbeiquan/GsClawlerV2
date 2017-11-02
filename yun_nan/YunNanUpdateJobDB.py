# coding=utf-8
import PackageTool
from gs.UpdateFromTable import UpdateFromTable
from YunNanSearcher import YunNanSearcher


class YunNanUpdateJobDB(UpdateFromTable):

    def __init__(self):
        super(YunNanUpdateJobDB, self).__init__()
        print '***'

    def set_config(self):
        self.searcher = YunNanSearcher()

if __name__ == '__main__':
    job = YunNanUpdateJobDB()
    job.run()
