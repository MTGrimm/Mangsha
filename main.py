from asyncio import Future
from genericpath import isfile
from multiprocessing.dummy import Pool
import shutil
from concurrent import futures
from concurrent.futures import ProcessPoolExecutor, process
from logging import exception
from tokenize import group
from turtle import forward
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys 
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import os
import sys
from PyQt5.QtCore import QUrl, Qt, QSize, QDataStream, QByteArray, QIODevice, QThread, pyqtSignal, QObject
from PyQt5.QtWidgets import QStackedWidget, QMainWindow, QApplication, QLabel, QPushButton, QGridLayout, QVBoxLayout, QWidget, QLineEdit, QListWidget, QHBoxLayout, QScrollArea, QToolBar, QAction, QProgressDialog, QListWidgetItem
from PyQt5.QtWebEngineWidgets import *
from PyQt5.QtGui import QKeySequence, QFont, QImage, QPixmap, QGuiApplication, QIcon
from adblockparser import AdblockRules
from PyQt5.QtWebEngineCore import *
from PyQt5.uic import loadUi
import requests
from multiprocessing import Process, Pool
import time
from io import BytesIO
from bs4 import BeautifulSoup
import json

class ImageScrape(QObject):
    finished = pyqtSignal(list)
    message = pyqtSignal(str)
    progress = pyqtSignal(list)
    def __init__(self, selected, chapter_list, driver, main_image):
        super(ImageScrape, self).__init__()
        self.chapter_list = chapter_list
        self.selected = selected
        self.driver = driver
        self.main_image = main_image
    
    def run(self):
        print("HUH")
        self.driver.get(self.chapter_list[self.selected])
        pages = [element.get_attribute("data-lazy-src") for element in self.driver.find_elements(By.XPATH, "//*[@id='readerarea']/p/img")]    
        imgs = []        
        for page in pages:
            print(page)
            image = QImage.fromData(requests.get(page).content)
            imgs.append(QPixmap(image))
            
        self.finished.emit(imgs)
        

class Driver(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal()
    def __init__(self):
        super(Driver, self).__init__()
        
    def run(self):
        option = Options()
        option.headless = False
        self.driver = webdriver.Firefox(options=option, service=Service(abs_path + "\geckodriver.exe"))
        self.driver.install_addon(r"Python/Comic Reader/adblock.xpi", temporary=True)
        self.driver.get("https://mangagenki.com/")
        self.finished.emit()
        
    def getDriver(self):
        return self.driver

class LinkScrape(QObject):
    finished = pyqtSignal()
    message = pyqtSignal(str)
    progress = pyqtSignal()
    def __init__(self, manga, driver):
        super(LinkScrape, self).__init__()
        self.manga = manga
        self.driver = driver
        self.chapter_links = []
    
    def run(self):
        self.driver.get("https://mangagenki.com/?s=" + self.manga.replace(" ", "+"))
        self.message.emit("WebDriver Loaded")
        
        manga_link = self.driver.find_element(By.XPATH, "//*[@class='bsx']/a").get_attribute("href")
        self.driver.get(manga_link)
        self.message.emit("MangaPage Loaded")
        self.manga_name = self.driver.find_element(By.CLASS_NAME, "entry-title").get_attribute("innerHTML")
        self.chapter_links = [element.get_attribute("href") for element in self.driver.find_elements(By.XPATH, "//*[@class='eph-num']/a")]
        self.message.emit("All Links Gathered, getting thumbnail image")
        self.thumbnail = self.driver.find_element(By.XPATH, "//*[@class='thumb']/img").get_attribute("src")
        self.img_data = requests.get(self.thumbnail).content
        with open(f'{abs_path}/Thumbnails/{self.manga_name.replace(" ", "_")}.png', 'wb') as img:
            img.write(self.img_data)
        self.message.emit("Thumbnail downloaded, creating JSON file")
        self.chapter_links.insert(0, 0)
        with open(f'{abs_path}/Library/{self.manga_name.replace(" ", "_")}.json', 'w') as f:
            json.dump(self.chapter_links, f, ensure_ascii=False)
        self.message.emit("JSON file created")
        self.finished.emit()
        
    def update_image(self, pix):
        self.progress.emit(pix)
 

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        loadUi("Python\Mangsha\main.ui", self)
        #self.setWindowFlag(Qt.FramelessWindowHint)
        #self.setAttribute(Qt.WA_TranslucentBackground)
        self.scrapper_button.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.scrapper_page))
        self.library_button.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.library_page))
        self.read_button.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.reading_page))
        self.scrape_submit_button.clicked.connect(self.scrape)
        self.manga_list.itemSelectionChanged.connect(self.loadChapters)
        self.refresh_button.clicked.connect(self.loadLibrary)
        self.start_driver.clicked.connect(self.startDriver)
        self.end_driver.clicked.connect(self.endDriver)
        self.back_button.clicked.connect(self.backPage)
        self.forward_button.clicked.connect(self.nextPage)
        self.next_button.clicked.connect(self.nextChapter)
        self.prev_button.clicked.connect(self.prevChapter)
        self.working = False
        self.driver_started = False
        self.driverThread = QThread()
        self.driverScrape = Driver()   
        self.driverScrape.moveToThread(self.driverThread)
        self.driverThread.started.connect(self.driverScrape.run)
        self.driverScrape.finished.connect(lambda: self.start_driver.setVisible(True))
        #self.driverScrape.finished.connect(self.fixLinkThread)
        self.driverThread.start()
        self.start_driver.setVisible(False)
        #self.main_image.setPixmap(QPixmap(QImage.fromData(requests.get("https://www.freeiconspng.com/img/7952").content))) 
        self.loadLibrary()
        self.showMaximized()  # display the mainWindow
    
    def scrape(self):
        self.thread = QThread()
        self.scrap = LinkScrape(self.lineEdit.text(), self.driverScrape.getDriver())   
        self.scrap.moveToThread(self.thread)
        self.thread.started.connect(self.scrap.run)
        self.scrap.finished.connect(self.fixLinkThread)
        self.scrap.message.connect(self.printMessage)
        self.thread.start()
    
    def startDriver(self):
        self.thread = QThread()
        self.scrap = ImageScrape(self.chapter_list.currentRow(), self.chapters, self.driverScrape.getDriver(), self.main_image)   
        self.scrap.moveToThread(self.thread)
        self.thread.started.connect(self.scrap.run)
        self.scrap.finished.connect(self.fixImageThread)
        self.scrap.message.connect(self.printMessage)
        self.thread.start()
        self.driver_started = True
            
    def fixLinkThread(self):
        self.thread.quit()
        self.scrap.deleteLater()
        while True:
            if not self.thread.isRunning():
                print("deleting thread")
                self.thread.deleteLater()
                break
        
            
    def fixImageThread(self, imgs):
        self.images = imgs
        self.page_num = 0
        self.main_image.setPixmap(self.images[self.page_num].scaled(self.main_image.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)) 
        self.thread.quit()
        self.scrap.deleteLater()
        while True:
            if not self.thread.isRunning():
                print("deleting thread")
                self.thread.deleteLater()
                break
        self.working = False
        
    def printMessage(self, msg):
        self.listWidget.insertItem(0, msg)
        
    def loadLibrary(self):
        self.manga_list.clear()
        self.chapter_list.clear()
        for file in os.listdir(f"{abs_path}/Thumbnails"):
            print(file)
            item = QListWidgetItem(file.replace(".png", "").replace("_", " "))  
            icon = QIcon(f"{abs_path}/Thumbnails/{file}")
            icon.addPixmap(icon.pixmap(64, 64))
            item.setIcon(icon)
            self.manga_list.addItem(item)
    
    def loadChapters(self):
        self.chapter_list.clear()
        manga_name = self.manga_list.currentItem().text()
        with open(f'{abs_path}/Library/{manga_name.replace(" ", "_")}.json', 'r') as file:
            data = json.load(file)
        self.currentChapter = data[0]
        self.chapters = data[1:]
        for chapter in self.chapters:
            self.chapter_list.addItem(f"Chapter {chapter.split('chapter-')[1].replace('-', '.').replace('/', '')}")
        

    def endDriver(self):
        if self.driver_started:
            self.driverScrape.getDriver().quit()
            self.driver_started = False
            
    def backPage(self):
        if self.page_num > 0:
            self.page_num = self.page_num - 1
            self.main_image.setPixmap(self.images[self.page_num].scaled(self.main_image.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else: 
            self.prevChapter()
            self.main_image.setPixmap(self.images[self.page_num].scaled(self.main_image.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
    
    def nextPage(self):
        if self.page_num < len(self.images) - 1:
            self.page_num = self.page_num + 1
            self.main_image.setPixmap(self.images[self.page_num].scaled(self.main_image.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.nextChapter()
            self.main_image.setPixmap(self.images[self.page_num].scaled(self.main_image.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
    
    def nextChapter(self):
        if not self.working:
            self.working = True
            self.chapter_list.setCurrentRow(self.chapter_list.currentRow() - 1)
            self.startDriver()
    
    def prevChapter(self):
        if not self.working:
            self.working = True
            self.chapter_list.setCurrentRow(self.chapter_list.currentRow() + 1)
            self.startDriver()
    
if __name__ == "__main__":
    abs_path = os.path.dirname(__file__)
    # creating the pyqt5 application
    app = QApplication(sys.argv)
    main = MainWindow()
    sys.exit(app.exec_())
    
    