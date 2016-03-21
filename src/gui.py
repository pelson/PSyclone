from PyQt4 import QtGui # Import the PyQt4 module we'll need
import sys # We need sys so that we can pass argv to QApplication

import gui_layout # This file holds our MainWindow and all design related things
              # it also keeps events etc that we defined in Qt Designer

from cStringIO import StringIO


class Capturing(list):
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self
    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        sys.stdout = self._stdout


class ExampleApp(QtGui.QMainWindow, gui_layout.Ui_MainWindow):
    def __init__(self):
        # Explaining super is out of the scope of this article
        # So please google it if you're not familar with it
        # Simple reason why we use it here is that it allows us to
        # access variables, methods etc in the design.py file
        super(self.__class__, self).__init__()
        self.setupUi(self)  # This is defined in design.py file automatically
                            # It sets up layout and widgets that are defined
        self.menubar.setNativeMenuBar(False)
        self.actionExit.triggered.connect(QtGui.qApp.quit)
        self.actionOpen.triggered.connect(self.showDialog)

        self.textBrowser_2.setOpenLinks(False)
        self.textBrowser_2.anchorClicked.connect(self.psy_output)

        self._psy = None

    def psy_output(self, uri):

        from cStringIO import StringIO
        import sys

        old_stdout = sys.stdout
        sys.stdout = mystdout = StringIO()

        self._psy.invokes.get(str(uri.path())).schedule.view()

        sys.stdout = old_stdout

        self.textBrowser_4.setText(mystdout.getvalue())

    def showDialog(self):

        fname = QtGui.QFileDialog.getOpenFileName(self, 'Open file', 
                '/home')
        
        f = open(fname, 'r')
        
        with f:        
            data = f.read()
            self.textBrowser.setText(data) 

        self.textBrowser_2.clear()
        self.textBrowser_4.clear()

        from parse import parse as f_parse
        alg_ast, invoke_info = f_parse(str(fname), api="dynamo0.3")
        from fparser import api
        from psyGen import PSyFactory
        self._psy = PSyFactory("dynamo0.3").create(invoke_info)
        self.textBrowser_5.setText(str(self._psy.gen))

        index = 0
        for stmt, depth in api.walk(alg_ast):
            index += 1
            import fparser
            if isinstance(stmt, fparser.base_classes.BeginStatement):
                tmp_content = stmt.content
                stmt.content = ""
                self.textBrowser_2.append(str(index) + str(stmt))
                stmt.content = tmp_content
            else:
                if stmt in self._psy.invokes.statements:
                    invoke_name = self._psy.invokes.statement_map[stmt].name
                    self.textBrowser_2.append(str(index) + "<a href='" + invoke_name + "'>" + str(stmt) + "</a>")
                else:
                    self.textBrowser_2.append(str(index) + str(stmt))

        from algGen import Alg
        alg_ast_trans = Alg(alg_ast, self._psy)
        self.textBrowser_3.setText(str(alg_ast_trans.gen))

def main():
    app = QtGui.QApplication(sys.argv)  # A new instance of QApplication
    form = ExampleApp()                 # We set the form to be our ExampleApp (design)
    form.show()                         # Show the form
    app.exec_()                         # and execute the app


if __name__ == '__main__':              # if we're running file directly and not importing it
    main()                              # run the main function


