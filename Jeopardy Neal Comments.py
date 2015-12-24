#!/usr/bin/python

'''
Program: Jeopardy.py
Authors: Norm Oza, Nick Oza, Neal Oza
Started: Dec 16, 2012
Revised: Dec 23, 2013
'''
import gdata.docs
import gdata.docs.service
import gdata.spreadsheet.service
import re, os
import time
import datetime as dt
import serial
import math as m

import wx
import wx.lib.wordwrap as wwrap
import textwrap
import random
import Image
#APP_EXIT = 1

usbport = '/dev/ttyACM0'
ser = serial.Serial(usbport, 9600, timeout = .10)
ID_TIMER = 2000
ID_TIMER2 = 2001
serDelay = 50
countdownDelay = 1000   # in ms?
print ser

class ozaPardyBox(object):
    def __init__(self, clue=None, response=None, value=None, isClicked=False,
        isDailyDouble=False, isAnswered=False, miceAns=0, menAns=0):
        self.clue = clue
        self.response = response
        self.value = value
        self.isClicked = isClicked
        self.isDailyDouble = isDailyDouble
        self.isAnswered = isAnswered
        self.miceAns = miceAns
        self.menAns = menAns

    def clicked(self):
        self.isClicked = True

#    def answered(team, isCorrect):
#        if team == 'men':
#            self.menAns = isCorrect
#            self.isAnswered=True
#        elif team == 'mice':
#            self.miceAns = isCorrect
#            self.isAnswered=True
#        else:
#            print("Team isn't valid: No score changed")
#

class team(object):
    def __init__(self, name="Men", score=0):
        self.name = name
        self.score = score

    def updateScore(self, points):
        self.score += points


class mainWin(wx.Frame):
    def __init__(self, *args, **kwargs):
        super (mainWin, self).__init__(*args, **kwargs)

        self.serialTimer=wx.Timer(self, ID_TIMER)
        self.Bind(wx.EVT_TIMER, self.timerFunc, self.serialTimer)
        self.serialTimer.Start(serDelay)
        self.serialTimer.Stop()

        self.teams = [team('Mice', 0), team('Men', 0)]
        self.currTeam = 0

        self.boxId = [''] * 30

        # Make empty gameplay boxes for (s)ingle jeopardy
        sBoxes = [""] * 6
        for ii in range(30): 
            sBoxes.append(ozaPardyBox())

        # Make empty gameplay boxes for (d)ouble jeopardy
        dBoxes = [""] * 6
        for ii in range(30): 
            dBoxes.append(ozaPardyBox())

        # Make empty gameplay boxes for (f)inal jeopardy
        #fBoxes = [""] * 6
        #for ii in range(30): 
        #    fBoxes.append(ozaPardyBox())
        #self.boxes = [sBoxes, dBoxes, fBoxes] 
        self.boxes = [sBoxes, dBoxes] 
        
        # Make empty gameplay box for Final jeopardy
        self.FinalBox = ['', ozaPardyBox()]

        # Establish the modes the screen can display
        # Single, Double, Final are for the main gameplay screen
        # Clue is for displaying the clue
        # Klok is for displaying a clock during which time a clue can be
        # answered
        # Response is for displaying the response
        # Daily is for daily double
        self.modes = ['Single', 'Double', 'Final', 'Clue', 'Klok', 
                      'Response', 'Daily']

        # gameMode tells us whether we are in Single, Double or Final
        self.gameMode = 'Single'

        # currMode tells us which of the prev. "modes" we're in
        # Can be Single, Double, Final, Clue, Klok, Response, or Daily
        self.currMode = 'Single'
        
        # Create wagers variable to use for Daily double & final jeopardy
        self.wagers = [0, 0]
        
        # Determines which box we're looking at
        self.currBox = -1
        self.currClueButton = wx.Button(self)

        # Sets the timer to 15 seconds
        self.timeCounter = 15

        # Draws the header
        # micePanel shows mice name, score, and wager window
        # bPanel shows the title, and button panel (correct or wrong)
        # menPanel shows men name, score, and wager window
        [self.micePanel, self.bPanel, self.menPanel] = self.updateHeader()

        # Initilize the gameplay boxes
        # stPanel = (s)ingle jeopardy (t)itle boxes
        # sgPanel = (s)ingle jeopardy (g)ame boxes
        # dtPanel = (d)ouble jeopardy (t)itle boxes
        # dgPanel = (d)ouble jeopardy (g)ame boxes
        [self.stPanel, self.sgPanel] = self.initGameBoxes('Single')
        [self.dtPanel, self.dgPanel] = self.initGameBoxes('Double')
        self.initFinalBox()

        self.makeDailyDoubles()

        # Hide the double jeopardy panels (i.e. start in single jeopardy)
        self.dtPanel.Hide()
        self.dgPanel.Hide()

        # Create a clue panel
        self.cPanel = self.newClue()

        # Create timer for countdown of events
        self.timer = wx.Timer(self, ID_TIMER2)
        self.Bind(wx.EVT_TIMER, self.timerFunc, self.timer)

        # Initialize the UI to the screen
        self.InitUI()
        self.Center()
        self.ShowFullScreen(False)
        self.Show(True)

    def timerUpdate(self, e):
        self.currClueButton.SetLabel("Time Remaining: " + str(self.timeCounter))

        self.timeCounter -= 1
        if self.timeCounter <= 0:
            self.timer.Stop()
            self.currClueButton.SetLabel("Time's Up!!")

    def readSerial(self, e):
        self.serialTimer.Stop()
        msg = ser.readline();
        if (msg):
            #print "Serial Input: " + msg
            self.setCurrTeam(msg.strip())
            #print "Current Team #: ", self.currTeam
            self.OnClueClickerClicked()
            #ser.write('W')
            #self.queue.put(msg)
        #else:
        #   print "No Serial input" 
        #   pass
        #self.serialTimer.Start(serDelay)
        self.serialTimer.Start()

    def timerFunc(self, e):
        timerId = e.GetId()
        if timerId == ID_TIMER:
            #print "Serial Timer Time: ", dt.datetime.now()
            #print "Serial Read Timer Event"
            self.readSerial(e)
        elif timerId == ID_TIMER2:
            #print "Countdown Timer Time: ", dt.datetime.now()
            #print "Countdown Timer Event"
            self.timerUpdate(e)

    def mode(self, modeType='Single'):
        if modeType in self.modes:
            return self.modes.index(modeType)
        else: return 0

    def areWeDoneYet(self):
        mNum = self.mode(self.gameMode)
        done = True
        for ii in range(30):
            done = (self.boxes[mNum][ii+6].isClicked and done)
        #print 'gameMode/mNum/done', self.gameMode, mNum, done
        return done

    # gameType variable tells you what round of the game you are in.
    # gameType = 0: Single Jeopardy
    # gameType = 1: Double Jeopardy
    # gameType = 2: Final Jeopardy
    def getJeopardyData(self, gameType=0):
        username        = 'cmozafam@gmail.com'
        passwd          = 'Jeopardy4us'
        doc_name        = 'OzaPardy'
        
        print "Start getJeopardyData"
        # Connect to Google
        gd_client = gdata.spreadsheet.service.SpreadsheetsService()
        gd_client.email = username
        gd_client.password = passwd
        gd_client.source = 'payne.org-example-1'
        gd_client.ProgrammaticLogin()

        q = gdata.spreadsheet.service.DocumentQuery()
        q['title'] = doc_name
        q['title-exact'] = 'true'
        feed = gd_client.GetSpreadsheetsFeed(query=q)
        spreadsheet_id = feed.entry[0].id.text.rsplit('/',1)[1]
        feed = gd_client.GetWorksheetsFeed(spreadsheet_id)
        worksheet_id = feed.entry[gameType].id.text.rsplit('/',1)[1]

        rows = gd_client.GetListFeed(spreadsheet_id, worksheet_id).entry

        for rowNum, row in enumerate(rows):
            for colNum, key in enumerate(row.custom):
                boxNum = int((ceil(rowNum/2.)*6) + (colNum-1))
                if colNum != 0:
                    if rowNum == 0:     # Fill in category Names
                        self.boxes[gameType][boxNum] = row.custom[key].text
                    else:               # Fill in Clue/Response boxes
                        self.parseOzaPardyBox(self.boxes[gameType][boxNum], 
                                              key, row.custom)

    def getFinalJeopardy(self):
        username        = 'cmozafam@gmail.com'
        passwd          = 'Jeopardy4us'
        doc_name        = 'OzaPardy'

        print "Start getFinalJeopardy"
        gd_client = gdata.spreadsheet.service.SpreadsheetsService()
        gd_client.email = username
        gd_client.password = passwd
        gd_client.source = 'payne.org-example-1'
        gd_client.ProgrammaticLogin()

        q = gdata.spreadsheet.service.DocumentQuery()
        q['title'] = doc_name
        q['title-exact'] = 'true'
        feed = gd_client.GetSpreadsheetsFeed(query=q)
        spreadsheet_id = feed.entry[0].id.text.rsplit('/',1)[1]
        feed = gd_client.GetWorksheetsFeed(spreadsheet_id)
        worksheet_id = feed.entry[2].id.text.rsplit('/',1)[1]

        rows = gd_client.GetListFeed(spreadsheet_id, worksheet_id).entry

        for rowNum, row in enumerate(rows):
            for colNum, key in enumerate(row.custom):
                boxNum = int(ceil(rowNum/2.) + (colNum-1))
                self.FinalBox[0] = row.custom['tiles'].text
                self.FinalBox[1].value = 1
                if rowNum == 1:
                    self.FinalBox[1].clue = self.myWrap(row.custom['cat1'].text)
                if rowNum == 2:
                    self.FinalBox[1].response = self.myWrap(row.custom['cat1'].text)


    def parseOzaPardyBox(self, opBox, key, gDict):
        [cellType, cellVal] = gDict['tiles'].text.split()
        opBox.value = cellVal
        if cellType=="Clue":
            opBox.clue = self.myWrap(gDict[key].text)
        else:
            opBox.response = self.myWrap(gDict[key].text)

    def makeDailyDoubles(self):
        r1 = random.randrange(30)
        r2 = random.randrange(30)
        r3 = random.randrange(30)
        while r2 == r3:
            r3 = random.randrange(30)
        
        self.boxes[0][r1+6].isDailyDouble = True
        self.boxes[1][r2+6].isDailyDouble = True
        self.boxes[1][r3+6].isDailyDouble = True

        print 'DD', r1, r2, r3


    def screenDraw(self, modeType):
        #self.micePanel.Hide()
        #self.bPanel.Hide()
        #self.menPanel.Hide()
        self.serialTimer.Stop()
        self.stPanel.Hide()
        self.sgPanel.Hide()
        self.dtPanel.Hide()
        self.dgPanel.Hide()
        self.cPanel.Hide()
        self.Show()

        vbox = wx.BoxSizer(wx.VERTICAL)
        hSizer = wx.BoxSizer(wx.HORIZONTAL)

        [self.micePanel, self.bPanel, self.menPanel] = self.updateHeader()

        hSizer.AddMany([(self.micePanel, 1, wx.EXPAND),
                        (self.bPanel,    1, wx.EXPAND),
                        (self.menPanel,  1, wx.EXPAND)])

        vbox.Add(hSizer, proportion=6, flag=wx.EXPAND)

        if modeType == 'Single':
            if not self.areWeDoneYet():
                self.stPanel.Show()
                self.sgPanel.Show()
                vbox.Add(self.stPanel, proportion=1, flag=wx.EXPAND)
                vbox.Add(self.sgPanel, proportion=20, flag=wx.EXPAND)
            else:
                self.gameMode = 'Double'
                modeType = 'Double'
                
        if modeType == 'Double':
            if not self.areWeDoneYet():
                self.dtPanel.Show()
                self.dgPanel.Show()
                vbox.Add(self.dtPanel, proportion=1, flag=wx.EXPAND)
                vbox.Add(self.dgPanel, proportion=20, flag=wx.EXPAND)
            else:
                self.gameMode = 'Final'
                modeType == 'Final'
                self.cPanel = self.newClue('Final Jeopardy')
        if not (modeType == 'Single' or modeType == 'Double'):
            self.cPanel.Show()
            vbox.Add(self.cPanel, proportion=21, flag=wx.EXPAND)

        self.SetSizer(vbox)
        self.Layout()
    
    def InitUI(self):
        menubar = wx.MenuBar()  # Create Menubar object
        fileMenu = wx.Menu()    # Create Menu opject
        #qmi = wx.MenuItem(fileMenu, APP_EXIT, '&Quit\tCtrl+Q')
        #qmi.SetBitmap(wx.Bitmap('exit.png'))
        #fileMenu.AppendItem(qmi)

        fitem = fileMenu.Append(wx.ID_EXIT, '&Quit', 'Quit Jeopardy')
        self.Bind(wx.EVT_MENU, self.OnQuit, fitem)
        
        menubar.Append(fileMenu, '&File')
        self.SetMenuBar(menubar)

        self.screenDraw('Single')
        
    def initFinalBox(self):
        mNum = self.mode('Final')
        self.getFinalJeopardy()

    def initGameBoxes(self, modeType):
        mNum = self.mode(modeType)
        self.getJeopardyData(mNum)
        
        tSizer = wx.GridSizer(1, 6, 2, 2)
        tPanel = wx.Panel(self)
        tPanel.SetSizer(tSizer)

        gSizer = wx.GridSizer(5, 6, 2, 2)
        gPanel = wx.Panel(self)
        gPanel.SetSizer(gSizer)

        for x in range(1,37):
            if x < 7:
                title = wx.Button(tPanel, label=self.boxes[mNum][x-1]) 
                title.SetFont(wx.Font(15, wx.MODERN, wx.NORMAL, wx.BOLD))
                title.SetForegroundColour('white')
                title.SetBackgroundColour('darkblue')
                tSizer.AddMany( [(title, 1, wx.EXPAND)] )
            else:
                self.boxId[x-7] = x-7
                boxButton = wx.Button(gPanel, label=self.boxes[mNum][x-1].value,
                                      name=str(self.boxId[x-7]))
                boxButton.SetFont(wx.Font(40, wx.MODERN, wx.NORMAL, wx.BOLD))
                boxButton.SetForegroundColour('white')
                boxButton.SetBackgroundColour('blue')
                boxButton.Bind(wx.EVT_BUTTON, self.OnGameButtonClicked)
                gSizer.AddMany( [(boxButton, 1, wx.EXPAND)] )
                
        return [tPanel, gPanel]
    
    def myWrap(self, inStr):
        tmp = textwrap.wrap(inStr, 30)
        print tmp
        tmp = '\n'.join(tmp) 
        return tmp

    def newClue(self, cString='Text'):
        cSizer = wx.BoxSizer() 
        cPanel = wx.Panel(self)
        cPanel.SetSizer(cSizer)
        
        if cString.split()[0] == 'Image:':
            imgName = cString.split()[1]
            image = wx.Image(imgName, wx.BITMAP_TYPE_ANY).ConvertToBitmap()
            cButton = wx.BitmapButton(cPanel, bitmap = image)
        else:
            cButton = wx.Button(cPanel, label=cString)
        #tmpString = self.myWrap(cString)
        #cButton.SetLabel(tmpString)
        cButton.SetFont(wx.Font(50, wx.MODERN, wx.NORMAL, wx.BOLD))
        cButton.SetForegroundColour('white')
        cButton.SetBackgroundColour('blue')
        cButton.Bind(wx.EVT_BUTTON, self.OnClueButtonClicked)
        cSizer.Add(cButton, 1, wx.EXPAND)
        self.currClueButton = cButton
        return cPanel

    
    def OnGameButtonClicked(self, e):
        mNum = self.mode(self.gameMode)
        bName = int(e.GetEventObject().GetName())
        
        self.timeCounter = 15
        e.GetEventObject().SetLabel('')
        self.currBox = bName+6
        if self.boxes[mNum][bName+6].isClicked == False:
            self.boxes[mNum][bName+6].clicked()
            e.GetEventObject().Disable()
            self.cPanel = self.newClue(self.boxes[mNum][bName+6].clue)
            if self.boxes[mNum][bName+6].isDailyDouble:
                print 'Daily Double Selected', self.currMode
                self.currMode = 'Daily'
                self.cPanel = self.newClue('Daily Double')
                self.screenDraw('Clue')
            else: 
                self.screenDraw('Clue')
                ser.write('L')  # Unlock Arduino controller
                #print 'Serial Write: L'
                #self.serialTimer.Start(serDelay)
                self.serialTimer.Start()
            print self.boxes[mNum][bName+6].clue
            print self.boxes[mNum][bName+6].response
        
    def OnClueButtonClicked(self, e):
        tic = dt.datetime.now()
        mNum = self.mode(self.gameMode)
        clueText = self.boxes[mNum][self.currBox].clue
        self.serialTimer.Stop()
        if self.currMode == 'Response':
            self.currMode = self.gameMode
            self.screenDraw(self.currMode)
        else:
            btnLabel = e.GetEventObject().GetLabel()
            if btnLabel == clueText:
                self.currMode = 'Klok'
                self.screenDraw('Klok')
                self.timer.Start(countdownDelay)
                self.currClueButton = e.GetEventObject()
                e.GetEventObject().SetLabel("Time Remaining: " + str(self.timeCounter))
            elif btnLabel == 'Daily Double':
                self.currMode = 'Daily'
                self.screenDraw('Daily')
                self.timer.Stop()
                self.timeCounter = 15
                e.GetEventObject().SetLabel(clueText)
            else:
                self.currMode = 'Clue'
                self.screenDraw('Clue')
                self.timer.Stop()
                if self.timeCounter < 10:
                    self.timeCounter = 10
                e.GetEventObject().SetLabel(clueText)
        self.Layout()
        toc = dt.datetime.now()
#        print "button: ", toc-tic

    def OnClueClickerClicked(self):
        tic = dt.datetime.now()
        mNum = self.mode(self.gameMode)
        clueText = self.boxes[mNum][self.currBox].clue
        self.serialTimer.Stop()
        #print "In On Clue Clicker"
        if self.currMode == 'Response':
            self.currMode = self.gameMode
            self.screenDraw(self.currMode)
        else:
            btnLabel = self.currClueButton.GetLabel()
            print btnLabel
            if btnLabel == clueText:
                self.currMode = 'Klok'
                self.screenDraw('Klok')
                self.timer.Start(countdownDelay)
                self.currClueButton.SetLabel("Time Remaining: " + str(self.timeCounter))
            elif btnLabel == 'Daily Double':
                self.currMode = 'Daily'
                self.screenDraw('Daily')
                self.timer.Stop()
                self.timeCounter = 15
                self.currClueButton.SetLabel(clueText)
            else:
                self.currMode = 'Clue'
                self.screenDraw('Clue')
                self.timer.Stop()
                if self.timeCounter < 10:
                    self.timeCounter = 10
                self.currClueButton.SetLabel(clueText)
        self.Layout()
        toc = dt.datetime.now()
#        print "Clicker: ", toc-tic

    def OnOzaPardyButtonClicked(self, e):
        mNum = self.mode(self.gameMode)
        self.boxes[mNum][self.currBox].isAnswered = True
        self.timer.Stop()
        self.serialTimer.Stop()
        self.currMode = 'Response'
        self.cPanel = self.newClue(self.boxes[mNum][self.currBox].response)
        self.screenDraw('Response')
        
    def OnCorrectButtonClicked(self, e):
        mNum = self.mode(self.gameMode)
        self.boxes[mNum][self.currBox].isAnswered = True
        self.timer.Stop()
        self.serialTimer.Stop()
        ser.write('C')
        points = int(self.boxes[mNum][self.currBox].value)
        #print "Current team: ", self.currTeam, points
        self.teams[self.currTeam].updateScore(points)
        self.currMode = 'Response'
        self.cPanel = self.newClue(self.boxes[mNum][self.currBox].response)
        self.screenDraw('Response')

    def OnWrongButtonClicked(self, e):
        mNum = self.mode(self.gameMode)
        self.boxes[mNum][self.currBox].isAnswered = True
        self.timer.Stop()
        self.serialTimer.Stop()
        ser.write('W')
        points = int(self.boxes[mNum][self.currBox].value)
        print "Current team: ", self.currTeam, -1*points
        self.teams[self.currTeam].updateScore(-1*points)
        self.currMode = 'Clue'
        self.cPanel = self.newClue(self.boxes[mNum][self.currBox].clue)
        self.screenDraw('Clue')
        #self.serialTimer.Start(serDelay)
        self.serialTimer.Start()

    def OnQuit(self, e):
        self.Close()
        
    def updateHeader(self):
        smallNormal = wx.Font(15, wx.MODERN, wx.NORMAL, wx.BOLD)
        bigNormal = wx.Font(30, wx.MODERN, wx.NORMAL, wx.BOLD)
        biggerNormal = wx.Font(50, wx.MODERN, wx.NORMAL, wx.BOLD)
        smallItalic = wx.Font(15, wx.MODERN, wx.ITALIC, wx.BOLD)
        bigItalic = wx.Font(30, wx.MODERN, wx.ITALIC, wx.BOLD)
        biggerItalic = wx.Font(50, wx.MODERN, wx.ITALIC, wx.BOLD)

        micePanel = wx.Panel(self)
        miceTitle = wx.StaticBox(micePanel, label=self.teams[0].name, 
                                 pos=(5,5), size=(550,210))
        miceTitle.SetFont(bigItalic)
        miceTitle.SetForegroundColour('darkblue')
        miceScoreDisp = wx.StaticText(micePanel, 1, pos=(20,80))
        miceScoreDisp.SetLabel('$' + str(self.teams[0].score))
        miceScoreDisp.SetFont(bigNormal)
        miceScoreDisp.SetForegroundColour('blue')
        miceWagerLabel = wx.StaticText(micePanel, 1, pos=(320,60))
        miceWagerLabel.SetLabel('Wager')
        miceWagerLabel.SetFont(smallNormal)
        miceWager = wx.TextCtrl(micePanel, 1, pos=(220,90), size=(200,50))
        miceWager.Bind(wx.EVT_TEXT, self.updateMiceWager)
        miceWager.SetFont(bigNormal)
        
        bPanel = wx.Panel(self)
        midButton = wx.Button(bPanel, pos=(5,25), size=(550, 70), 
                              label='OzaPardy')
        midButton.SetFont(bigNormal)
        midButton.SetForegroundColour('darkblue')
        midButton.Bind(wx.EVT_BUTTON, self.OnOzaPardyButtonClicked)
        if self.currMode == 'Klok':
            corButton = wx.Button(bPanel, pos=(5,104), size=(550, 50), 
                                  label='Correct')
            wrgButton = wx.Button(bPanel, pos=(5,163), size=(550, 50), 
                                  label='Wrong')
            corButton.SetFont(smallNormal)
            wrgButton.SetFont(smallNormal)
            corButton.SetForegroundColour('darkgreen')
            wrgButton.SetForegroundColour('red')
            corButton.Bind(wx.EVT_BUTTON, self.OnCorrectButtonClicked)
            wrgButton.Bind(wx.EVT_BUTTON, self.OnWrongButtonClicked)

        menPanel = wx.Panel(self)
        menTitle = wx.StaticBox(menPanel, label=self.teams[1].name, 
                                pos=(5,5), size=(550,210))
        menTitle.SetFont(bigItalic)
        menTitle.SetForegroundColour('darkblue')
        menScoreDisp = wx.StaticText(menPanel, 1, pos=(20,80))
        menScoreDisp.SetLabel('$' + str(self.teams[1].score))
        menScoreDisp.SetFont(bigNormal)
        menScoreDisp.SetForegroundColour('blue')
        menWagerLabel = wx.StaticText(menPanel, 1, pos=(320,60))
        menWagerLabel.SetLabel('Wager')
        menWagerLabel.SetFont(smallNormal)
        menWager = wx.TextCtrl(menPanel, 1, pos=(220,90), size=(200,50))
        menWager.Bind(wx.EVT_TEXT, self.updateMenWager)
        menWager.SetFont(bigNormal)

        return [micePanel, bPanel, menPanel]

    def updateMiceWager(self, e):
        wager = e.GetEventObject().GetValue()
        mNum = self.mode(self.gameMode)
        self.currTeam = 0
        self.wagers[self.currTeam] = wager
        self.boxes[mNum][self.currBox].value = wager

    def updateMenWager(self, e):
        wager = e.GetEventObject().GetValue()
        mNum = self.mode(self.gameMode)
        self.currTeam = 1
        self.wagers[self.currTeam] = wager
        self.boxes[mNum][self.currBox].value = wager

    def setCurrTeam(self, serRead):
        #        print 'Serial Read:', serRead, serRead == 'Mice'

        if serRead == 'Mice':
            self.currTeam = 0
            print "currTeam now Mice", self.currTeam
        else:
            self.currTeam = 1
            print "currTeam now Men", self.currTeam

def main():
    app = wx.App()
    mainWin(None)
    app.MainLoop()

if __name__ == '__main__':
    main()

'''
mainWindow= wx.Frame(None, -1, 'Jeopardy', style =  wx.MINIMIZE_BOX | wx.MAXIMIZE_BOX | wx.RESIZE_BORDER 
    | wx.SYSTEM_MENU | wx.CAPTION |     wx.CLOSE_BOX)
mainWindow.Centre()
mainWindow.Show(True)

app.MainLoop()
'''

