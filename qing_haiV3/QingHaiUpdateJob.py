# coding=utf-8
import PackageTool
from gs.GsSrcCousumer import GsSrcCousumer
from QingHai_un import QingHai


class QingHaiUpdateJob(GsSrcCousumer):

    def __init__(self):
        super(QingHaiUpdateJob, self).__init__()

    def set_config(self):
        self.searcher = QingHai()
        # self.init_kafka('GsSrc63')    #在searcher进行初始化，此处不再进行初始化

if __name__ == '__main__':
    job = QingHaiUpdateJob()
    job.run()
