from PyQt4 import QtGui # Import the PyQt4 module we'll need
import sys # We need sys so that we can pass argv to QApplication

import gui_layout # This file holds our MainWindow and all design related things
              # it also keeps events etc that we defined in Qt Designer

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

    def showDialog(self):

        fname = QtGui.QFileDialog.getOpenFileName(self, 'Open file', 
                '/home')
        
        f = open(fname, 'r')
        
        with f:        
            data = f.read()
            self.textBrowser.setText(data) 

        from parse import parse as f_parse
        alg_ast, invoke_info = f_parse(str(fname), api="dynamo0.3")
        self.textBrowser_2.setText(str(alg_ast))

        from psyGen import PSyFactory
        psy = PSyFactory("dynamo0.3").create(invoke_info)
        from algGen import Alg
        alg_ast_trans = Alg(alg_ast, psy)
        self.textBrowser_3.setText(str(alg_ast_trans.gen))

def main():
    app = QtGui.QApplication(sys.argv)  # A new instance of QApplication
    form = ExampleApp()                 # We set the form to be our ExampleApp (design)
    form.show()                         # Show the form
    app.exec_()                         # and execute the app


if __name__ == '__main__':              # if we're running file directly and not importing it
    main()                              # run the main function


