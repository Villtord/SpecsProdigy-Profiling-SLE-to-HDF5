#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jul 23 20:02:12 2017

@author: villtord
"""
from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication, QWidget,QFileDialog
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QIcon
from UI_SQL_converter import Ui_SQL_Dialog
from SQL_converter import SQL_converter_function
import sys

# This file holds our MainWindow and all design related things
# it also keeps events etc that we defined in Qt Designer

    
        

class process_file(QThread):
    
    trigger = pyqtSignal('QString')
    f_trigger = pyqtSignal()
    bar_trigger = pyqtSignal()
    
    def __init__(self, file_list):
        """
        Make a new thread instance with the specified
        file list as the first argument. The file list argument
        will be stored in an instance variable called file_list
        which then can be accessed by all other class instance functions
        """
        super(process_file,self).__init__()
        self.file_list = file_list
    
    def __del__(self):
        self.wait()
   
    def start(self):

        """ This function will convert the files and emit signals to update History and ProgressBar in main app """
        for i in self.file_list[:-1:]:               
            self.trigger.emit(i)
            SQL_converter_function(i)
            self.bar_trigger.emit()
#        self.sleep(1)
        self.f_trigger.emit()
        pass



class ExampleApp(QWidget, Ui_SQL_Dialog):
    

    def __init__(self):

        super(self.__class__, self).__init__()
        self.setupUi(self)  # This is defined in design.py file automatical
        self.setWindowIcon(QIcon('Converter_icon.ico'))

        self.btnBrowse.clicked.connect(self.browse_folder)  # When the button is pressed
        self.Convert.clicked.connect(self.convert_files)
    
        
        """ Here the signals emitted in the thread process_file are translated to functions in the main app"""
        
    def browse_folder(self):
        self.Filename.clear() # In case there are any existing elements in the list
        files_list   =     QFileDialog.getOpenFileNames(self, 'Open file', '','*.sle')
        files=files_list[0]
        string_files=''
        
        for i in files:
        
            string_files = string_files+str(i)+', '
        
        self.Filename.setText(string_files)
        message="Number of files chosen: "+str(len(files))
        self.History.setHtml (self.History.toHtml() + message + '\n')
        self.History.moveCursor(QtGui.QTextCursor.End)
        
        if string_files!='':
            self.Convert.setEnabled(True)

        
    def convert_files(self):
        
        if str(self.Filename.text())!='':
            
            self.History.setHtml (self.History.toHtml() + 'Converter is running...\n')
            self.History.moveCursor(QtGui.QTextCursor.End)
            self.History.repaint()
            filenames=str(self.Filename.text())
            filenames_list=filenames.split(', ')
            del filenames_list[-1]
            self.progressBar.setMaximum(len(filenames_list))
            self.progressBar.setProperty("value", 0)
            
#            if self.Rename.isChecked():
#                flag=True
#            else:
#                flag=False
            flag=False               
            filenames_list.append(flag)

            
            self.get_thread = process_file(filenames_list)
            self.get_thread.trigger.connect(self.update_history)
            self.get_thread.f_trigger.connect(self.done) 
            self.get_thread.bar_trigger.connect(self.update_bar)

            """ Here we start a separate thread which makes all the job and doesn't freeze the main app"""
            """ We can start the thread"""
            self.get_thread.start()
       
    def update_bar(self):
        self.progressBar.setProperty("value", self.progressBar.value()+1)
        pass        
                 
    def update_history(self, file):
        self.History.setHtml (self.History.toHtml() + 'Done with ' + file.split('/')[-1] + '\n')
        self.History.moveCursor(QtGui.QTextCursor.End)
        pass
    
    def done(self):
        self.History.setHtml (self.History.toHtml() + 'Done !!!')
        self.History.moveCursor(QtGui.QTextCursor.End)
        pass

def main():
    app = QApplication(sys.argv)  # A new instance of QApplication
    form = ExampleApp()                 # We set the form to be our ExampleApp (design)
    form.show()                         # Show the form
    app.exec_()                         # and execute the app


if __name__ == '__main__':              # if we're running file directly and not importing it
    main()                              # run the main function