# coding=utf-8
import PackageTool
from gs.UpdateFromTable import UpdateFromTable
from GuiZhouSearcher import GuiZhouSearcher


class GuiZhouUpdateJobDB(UpdateFromTable):

    def __init__(self):
        super(GuiZhouUpdateJobDB, self).__init__()

    def set_config(self):
        self.searcher = GuiZhouSearcher()

if __name__ == '__main__':
    job = GuiZhouUpdateJobDB()
    job.run()
