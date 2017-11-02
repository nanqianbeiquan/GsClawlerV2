# coding=utf-8
import PackageTool
from gs.GsSrcCousumer import GsSrcCousumer
from GuiZhouSearcher import GuiZhouSearcher


class GuiZhouUpdateJob(GsSrcCousumer):

    def __init__(self):
        super(GuiZhouUpdateJob, self).__init__()

    def set_config(self):
        self.searcher = GuiZhouSearcher()

if __name__ == '__main__':
    job = GuiZhouUpdateJob()
    job.run()
