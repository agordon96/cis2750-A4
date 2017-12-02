#!/usr/bin/python3

from ctypes import *
import os
import sys
import mysql.connector as sql
import tkinter as tk
import tkinter.tix as tix
import tkinter.scrolledtext as scroll
import tkinter.font as tfo
import tkinter.filedialog as tfile
import tkinter.messagebox as tmsg
import tkinter.ttk as tkt

class Calendar(Structure):
  _fields_ = [("version", c_float), ("prodID", c_byte * 1000), ("events", c_void_p), ("properties", c_void_p)]

class Application(tk.Frame):
  def __init__(self, master=None):
    if(len(sys.argv) > 2):
      print("Too many arguments. Should be A4main.py with an optional username for database connection.")
      exit()
    elif len(sys.argv) == 2:
      username = sys.argv[1]
      tries = 0
      while True:
        database = input("Please input a database to connect to. ")
        password = input("Please type in your password. ")
        try:
          self.db = sql.connect(host="dursley.socs.uoguelph.ca", user=username, passwd=password, db=database)
          break
        except:
          tries += 1
          if tries == 3:
            print("Too many connection failures. Exiting program...")
            exit()
            
          print("Connection failed. Please try again.")
    else:
      self.db = sql.connect(host="dursley.socs.uoguelph.ca", user="agordo11", passwd="0884023", db="agordo11")
    
    tk.Frame.__init__(self, master)
    self.master.resizable(width=False, height=False)
    self.master.geometry("500x500") 
    self.master.title("iCalGUI")
    self.grid_rowconfigure(0, weight=1)
    self.grid_columnconfigure(0, weight=1)  
    self.cur = self.db.cursor(buffered=True)

    try:
      self.cur.execute("CREATE TABLE ORGANIZER (org_id INT AUTO_INCREMENT, name VARCHAR(60) NOT NULL, contact VARCHAR(60) NOT NULL, PRIMARY KEY (org_id))")
    except:
      pass
      
    try:
      self.cur.execute("CREATE TABLE EVENT (event_id INT AUTO_INCREMENT, summary VARCHAR(60) NOT NULL, start_time DATETIME NOT NULL, location VARCHAR(60), organizer INT, num_alarms INT, PRIMARY KEY (event_id), FOREIGN KEY (organizer) REFERENCES ORGANIZER (org_id) ON DELETE CASCADE)")
    except:
      pass
    
    self.master.protocol("WM_DELETE_WINDOW", self.close)
    self.bind_all("<Control-x>", self.closeWrapper)
    self.bind_all("<Control-o>", self.openWrapper)
    self.bind_all("<Control-s>", self.saveWrapper)
    self.bind_all("<Control-a>", self.saveAsWrapper)
    
    self.parseLib = cdll.LoadLibrary("./bin/libparser.so")
    
    self.printError = self.parseLib.printError
    self.printError.argtypes = [c_int]
    self.printError.restype = c_char_p
    
    self.calOpen = self.parseLib.calOpen
    self.calOpen.argtypes = [c_char_p]
    self.calOpen.restype = POINTER(Calendar)
    
    self.calOpenFail = self.parseLib.calOpenFail
    self.calOpenFail.argtypes = [c_char_p]
    
    self.customCal = self.parseLib.customCal
    self.customCal.argtypes = [(c_char * 1000) * 2]
    self.customCal.restype = POINTER(Calendar)

    self.customEvent = self.parseLib.customEvent
    self.customEvent.argtypes = [POINTER(Calendar), (c_char * 1000) * 4]
    self.customEvent.restype = POINTER(Calendar)
    
    self.customAlarm = self.parseLib.customAlarm
    self.customAlarm.argtypes = [POINTER(Calendar), (c_char * 1000) * 2, c_int]
    self.customAlarm.restype = POINTER(Calendar)
    
    self.getEventNum = self.parseLib.getEventNum
    self.getEventNum.argtypes = [POINTER(Calendar)]
    
    self.getEventArr = self.parseLib.getEventArr
    self.getEventArr.argtypes = [POINTER(Calendar), c_int, POINTER(c_char_p)]
    
    self.writeCalendar = self.parseLib.writeCalendar
    self.writeCalendar.argtypes = [c_char_p, POINTER(Calendar)]
    
    self.validateCalendar = self.parseLib.validateCalendar
    self.validateCalendar.argtypes = [POINTER(Calendar)]
    
    self.deleteEventCal = self.parseLib.deleteEvent
    self.deleteEventCal.argtypes = [POINTER(Calendar), c_int]
        
    self.deleteCalendar = self.parseLib.deleteCalendar
    self.deleteCalendar.argtypes = [POINTER(Calendar)]

    self.printEvent = self.parseLib.printEvent
    self.printEvent.argtypes = [POINTER(Calendar), c_int]
    self.printEvent.restype = c_char_p
    
    self.printError = self.parseLib.printError
    self.printError.argtypes = [c_int]
    self.printError.restype = c_char_p
    
    self.sqlEvent = self.parseLib.sqlEvent
    self.sqlEvent.argtypes = [POINTER(Calendar), c_int, POINTER(c_char_p)]
    
    self.cal = None
    self.selectEvent = None
    self.filename = ""
    self.eventNum = 0
    self.isQuery = False
    
    self.menuFont = tfo.Font(family="Times New Roman", size=12)
    self.topFont = tfo.Font(family="Times New Roman", size=12)
    self.bottomFont = tfo.Font(family="Times New Roman", size=12)
    self.aboutFont = tfo.Font(family="Times New Roman", size=12)
     
    self.createWidgets()
    self.updateScreen()
    
  def closeWrapper(self, event):
    self.close()
    
  def openWrapper(self, event):
    self.openCal()
    
  def saveWrapper(self, event):
    self.saveCal()
    
  def saveAsWrapper(self, event):
    self.saveCalAs()
  
  def updateScreen(self):
    self.tree.delete(*self.tree.get_children())
    if self.eventNum == 0:
      self.createMenu.entryconfig(3, state=tk.DISABLED)
      self.dbMenu.entryconfig(0, state=tk.DISABLED)
      self.tree.insert("", "end", values=("No Event", "", "", "Please add an event before saving."))
      self.selectEvent = None
    else:
      self.createMenu.entryconfig(3, state=tk.NORMAL)
      self.dbMenu.entryconfig(0, state=tk.NORMAL)
      
    for i in range(self.eventNum):
      string_buffers = [create_string_buffer(800) for i in range(3)]
      pointers = (c_char_p * 3)(*map(addressof, string_buffers))
      self.getEventArr(self.cal, i, pointers)
      results = [s.value for s in string_buffers]
      self.tree.insert("", "end", values=(str(i + 1), results[0].decode("utf-8"), results[1].decode("utf-8"), results[2].decode("utf-8")))
    
    self.dbMenu.entryconfig(1, state=tk.DISABLED)
    self.dbMenu.entryconfig(2, state=tk.DISABLED)
    
    if self.selectEvent:
      self.dbMenu.entryconfig(1, state=tk.NORMAL)
    
    try:
      self.cur.execute("SELECT * FROM ORGANIZER")
      if len(self.cur.fetchall()) > 0:
        self.dbMenu.entryconfig(2, state=tk.NORMAL)
    except(sql.Error, sql.Warning) as e:
      self.bottomText.config(state=tk.NORMAL)   
      self.bottomText.insert(tk.INSERT, str(e) + "\n>> ")
      self.bottomText.config(state=tk.DISABLED)
    
    try:
      self.cur.execute("SELECT * FROM EVENT")
      if len(self.cur.fetchall()) > 0:
        self.dbMenu.entryconfig(2, state=tk.NORMAL)
    except(sql.Error, sql.Warning) as e:
      self.bottomText.config(state=tk.NORMAL)   
      self.bottomText.insert(tk.INSERT, str(e) + "\n>> ")
      self.bottomText.config(state=tk.DISABLED)
      
    self.selectEvent = None
    
  def deleteEventWrapper(self):
    self.win.destroy()
    
    self.bottomText.config(state=tk.NORMAL)
    self.deleteEventCal(self.cal, self.eventIndex.get())
    
    self.bottomText.insert(tk.INSERT, "Event deleted.\n>> ")
    self.eventNum -= 1
    self.updateScreen()
    self.bottomText.config(state=tk.DISABLED)
  
  def deleteEvent(self):
    self.eventIndex = tk.IntVar()
    
    self.win = tk.Toplevel(self)
    self.win.wm_title("Delete Event")
    
    self.numStrs = []
    for i in range(self.eventNum):
      self.numStrs.append(str(i))
    
    tk.Label(self.win, text="Event #").grid(row=0)
    tkt.Combobox(self.win, textvariable=self.eventIndex, values=self.numStrs).grid(row=0, column=1)
    tk.Button(self.win, text="OK", command=self.deleteEventWrapper).grid(row=2, column=0, sticky=tk.W, pady=4)
    tk.Button(self.win, text="Cancel", command=self.win.destroy).grid(row=2, column=1, sticky=tk.W, pady=4)
  
  def close(self):
    result = tmsg.askyesno("Quit", "Are you sure you'd like to quit?")
    if result:
      self.cur.close()
      self.db.commit()
      self.db.close()
      if self.cal:
        self.deleteCalendar(self.cal)
      self.quit()

  def showEvent(self, event):
    item = self.tree.identify("item", event.x, event.y)
    eventStr = self.printEvent(self.cal, self.tree.item(self.tree.selection())['values'][0]).decode("utf-8").replace("\t", "")
    
    self.win = tk.Toplevel(self)
    self.win.wm_title("Event Details")
    
    tk.Label(self.win, padx=50, pady=40, font=self.aboutFont, text=eventStr).grid(row=0)
    tk.Button(self.win, text="OK", command=self.win.destroy).grid(row=2, column=0, sticky=tk.S, pady=4)
  
  def selectedEvent(self, event):
    self.dbMenu.entryconfig(1, state=tk.NORMAL)
    self.selectEvent = self.tree.focus()
  
  def about(self):
    self.win = tk.Toplevel(self)
    self.win.wm_title("About")
    
    tk.Label(self.win, padx=50, pady=40, font=self.aboutFont, text="iCalGUI 2017 - Compatible with iCalendar v2.0\nAaron Gordon 2017 - Assignment 3 for CIS*2750").grid(row=0)
    tk.Button(self.win, text="OK", command=self.win.destroy).grid(row=2, column=0, sticky=tk.S, pady=4)
    
  def openCal(self):
    getFile = tfile.askopenfilename(initialdir=os.getcwd(), title="Select .ics file", filetypes = (("iCal files", "*.ics"),))
    if not getFile == "" and getFile:
      self.filename = getFile
      getFile = getFile.split("/")
      self.cal = self.calOpen(self.filename.encode('utf-8'))
      status = 0
      if not self.cal:
        status = self.calOpenFail(self.filename.encode('utf-8'))
      self.bottomText.config(state=tk.NORMAL)
      if not status == 0:
        self.bottomText.insert(tk.INSERT, self.printError(status).decode() + "\n>> ")
      else:
        self.master.title("iCalGUI - " + getFile[-1])
        self.bottomText.insert(tk.INSERT, "File successfully parsed.\n>> ")
        self.fileMenu.entryconfig(1, state=tk.NORMAL)
        self.fileMenu.entryconfig(2, state=tk.NORMAL)
        self.createMenu.entryconfig(1, state=tk.NORMAL)
        self.createMenu.entryconfig(2, state=tk.NORMAL)
        self.eventNum = self.getEventNum(self.cal)
        self.updateScreen()
      self.bottomText.config(state=tk.DISABLED)
    
  def saveCal(self):
    status = self.validateCalendar(self.cal)
    self.bottomText.config(state=tk.NORMAL)
    if self.filename == "" and status == 0:
      self.saveCalAs()
    elif not status == 0:
      self.bottomText.insert(tk.INSERT, self.printError(status).decode() + "\n>> ")
    else:
      self.bottomText.insert(tk.INSERT, "File successfully saved.\n>> ")
      self.writeCalendar(self.filename.encode("utf-8"), self.cal)
    self.bottomText.config(state=tk.DISABLED)

  def saveCalAs(self):
    status = self.validateCalendar(self.cal)
    self.bottomText.config(state=tk.NORMAL)
    if status == 0:
      getFile = tfile.asksaveasfilename(initialdir=os.getcwd(), title="Select .ics file", filetypes=(("iCal files", "*.ics"), ("All files", "*.*")))
      if not getFile == "" and getFile:
        self.filename = getFile
        getFile = getFile.split("/")
        self.master.title("iCalGUI - " + getFile[-1])
        self.bottomText.insert(tk.INSERT, "File successfully saved.\n>> ")
        self.writeCalendar(self.filename.encode("utf-8"), self.cal)
    else:
      self.bottomText.insert(tk.INSERT, self.printError(status).decode() + "\n>> ")    
    self.bottomText.config(state=tk.DISABLED)
    
  def createCalWrapper(self):
    arr = ((c_char * 1000) * 2)()
    self.win.destroy()
    
    self.bottomText.config(state=tk.NORMAL)
    if self.createProd.get() == "":
      self.bottomText.insert(tk.INSERT, "Calendar not created: prodID must not be blank.\n>> ")
    else:
      arr[0].value = b"2.0"
      arr[1].value = self.createProd.get().encode("utf-8")
      self.cal = self.customCal(arr)
      
      self.fileMenu.entryconfig(1, state=tk.NORMAL)
      self.fileMenu.entryconfig(2, state=tk.NORMAL)
      self.createMenu.entryconfig(1, state=tk.NORMAL)
      self.createMenu.entryconfig(2, state=tk.DISABLED)
      
      self.master.title("iCalGUI")
      self.bottomText.insert(tk.INSERT, "New empty calendar created.\n>> ")
      self.eventNum = 0
      self.updateScreen()
    self.bottomText.config(state=tk.DISABLED)
    
  def createCal(self):
    self.createProd = tk.StringVar()
    
    self.win = tk.Toplevel(self)
    self.win.wm_title("Create Calendar")
    
    tk.Label(self.win, text="Product ID").grid(row=0)
    tk.Entry(self.win, textvariable=self.createProd).grid(row=0, column=1)
    tk.Button(self.win, text="OK", command=self.createCalWrapper).grid(row=2, column=0, sticky=tk.W, pady=4)
    tk.Button(self.win, text="Cancel", command=self.win.destroy).grid(row=2, column=1, sticky=tk.W, pady=4)

  def createEventWrapper(self):
    arr = ((c_char * 1000) * 4)()
    self.win.destroy()
    
    self.bottomText.config(state=tk.NORMAL)
    if self.createUID.get() == "":
      self.bottomText.insert(tk.INSERT, "Event not created. UID must not be blank.\n>> ")
    elif not len(self.date.get()) == 8 or not self.date.get().isdigit():
      self.bottomText.insert(tk.INSERT, "Date must be 8 valid numbers.\n>> ")
    elif not len(self.time.get()) == 6 or not self.time.get().isdigit():
      self.bottomText.insert(tk.INSERT, "Time must be 6 valid numbers.\n>> ")
    else:
      arr[0].value = self.createUID.get().encode("utf-8")
      arr[1].value = self.date.get().encode("utf-8")
      arr[2].value = self.time.get().encode("utf-8")
      arr[3].value = str(0).encode("utf-8")

      if self.UTC.get():
        arr[3].value = str(1).encode("utf-8")
      self.cal = self.customEvent(self.cal, arr)  
      
      self.createMenu.entryconfig(2, state=tk.NORMAL)  
      self.bottomText.insert(tk.INSERT, "New event created.\n>> ")
      self.eventNum += 1
      self.updateScreen()
    self.bottomText.config(state=tk.DISABLED)
    
  def createEvent(self):
    self.createUID = tk.StringVar()
    self.date = tk.StringVar()
    self.time = tk.StringVar()
    self.UTC = tk.IntVar()
    
    self.win = tk.Toplevel(self)
    self.win.wm_title("Create Event")
    
    tk.Label(self.win, text="UID").grid(row=0)
    tk.Entry(self.win, textvariable=self.createUID).grid(row=0, column=1)
    tk.Label(self.win, text="Start Date").grid(row=1)
    tk.Entry(self.win, textvariable=self.date).grid(row=1, column=1)
    tk.Label(self.win, text="Start Time").grid(row=2)
    tk.Entry(self.win, textvariable=self.time).grid(row=2, column=1)
    tk.Checkbutton(self.win, text="UTC?", variable=self.UTC).grid(row=3)
    tk.Button(self.win, text="OK", command=self.createEventWrapper).grid(row=5, column=0, sticky=tk.W, pady=4)
    tk.Button(self.win, text="Cancel", command=self.win.destroy).grid(row=5, column=1, sticky=tk.W, pady=4)
  
  def createAlarmWrapper(self):
    arr = ((c_char * 1000) * 2)()
    self.win.destroy()
    
    self.bottomText.config(state=tk.NORMAL)
    if self.action.get() == "" or self.trigger.get() == "":
      self.bottomText.insert(tk.INSERT, "Alarm not created. Action and trigger must be present.\n>> ")
    else:
      arr[0].value = self.action.get().encode("utf-8")
      arr[1].value = self.trigger.get().encode("utf-8")
      self.cal = self.customAlarm(self.cal, arr, self.eventIndex.get())
      
      self.bottomText.insert(tk.INSERT, "New event created.\n>> ")
      self.updateScreen()
    self.bottomText.config(state=tk.DISABLED)
  
  def createAlarm(self):
    self.action = tk.StringVar()
    self.trigger = tk.StringVar()
    self.eventIndex = tk.IntVar()
    
    self.win = tk.Toplevel(self)
    self.win.wm_title("Create Alarm")
    
    self.numStrs = []
    for i in range(self.eventNum):
      self.numStrs.append(str(i))
    
    tk.Label(self.win, text="Action").grid(row=0)
    tk.Entry(self.win, textvariable=self.action).grid(row=0, column=1)
    tk.Label(self.win, text="Trigger").grid(row=1)
    tk.Entry(self.win, textvariable=self.trigger).grid(row=1, column=1)
    tk.Label(self.win, text="Event #").grid(row=2)
    tkt.Combobox(self.win, textvariable=self.eventIndex, values=self.numStrs).grid(row=2, column=1)
    tk.Button(self.win, text="OK", command=self.createAlarmWrapper).grid(row=4, column=0, sticky=tk.W, pady=4)
    tk.Button(self.win, text="Cancel", command=self.win.destroy).grid(row=4, column=1, sticky=tk.W, pady=4)
  
  def storeAllEvents(self):
    for i in range(self.eventNum):
      string_buffers = [create_string_buffer(800) for i in range(6)]
      pointers = (c_char_p * 6)(*map(addressof, string_buffers))
      self.sqlEvent(self.cal, i, pointers)
      results = [s.value for s in string_buffers]
      
      orgID = None
      if not results[0].decode("utf-8") == "":
        select = 'SELECT * FROM ORGANIZER WHERE name="' + results[0].decode('utf-8') + '";'
        try:
          self.cur.execute(select)
          if len(self.cur.fetchall()) == 0:
            self.cur.execute('INSERT INTO ORGANIZER VALUES (NULL, "' + results[0].decode('utf-8') + '", "' + results[1].decode('utf-8') + '");')
            self.db.commit()
            self.cur.execute(select)
            orgID = self.cur.fetchall()[0][0]
          else:
            self.cur.execute(select)
            orgID = self.cur.fetchall()[0][0]
        except(sql.Error, sql.Warning) as e:
          self.bottomText.config(state=tk.NORMAL)   
          self.bottomText.insert(tk.INSERT, str(e) + "\n>> ")
          self.bottomText.config(state=tk.DISABLED)
      
      if not orgID:
        orgID = "NULL"
        
      try:
        select = 'SELECT * FROM EVENT WHERE summary="' + results[2].decode('utf-8') + '" AND start_time="' + results[3].decode('utf-8') + '";'
        self.cur.execute(select)
        if len(self.cur.fetchall()) == 0:
          eventSql = "INSERT INTO EVENT VALUES (NULL, '" +  results[2].decode('utf-8') + "', STR_TO_DATE('" + results[3].decode('utf-8') + "', '%Y%m%d %H%i%s'), "
          if results[4].decode('utf-8') == "":
            eventSql += "NULL"
          else:
            eventSql += ("'" + results[4].decode('utf-8') + "'")
            
          if orgID:
            eventSql += (", " + str(orgID) + ", " + results[5].decode('utf-8') + ");")
          else:
            eventSql += (", NULL, " + results[5].decode('utf-8') + ");")
          
          self.cur.execute(eventSql)
          self.db.commit()
          self.cur.execute(select)
      except(sql.Error, sql.Warning) as e:
        self.bottomText.config(state=tk.NORMAL)   
        self.bottomText.insert(tk.INSERT, str(e) + "\n>> ")
        self.bottomText.config(state=tk.DISABLED)
      
    self.displayStatus()
    
  def storeEvent(self):
    string_buffers = [create_string_buffer(800) for i in range(6)]
    pointers = (c_char_p * 6)(*map(addressof, string_buffers))
    self.sqlEvent(self.cal, self.tree.item(self.selectEvent)['values'][0] - 1, pointers)
    results = [s.value for s in string_buffers]
    
    orgID = None
    if not results[0].decode("utf-8") == "":
      select = 'SELECT * FROM ORGANIZER WHERE name="' + results[0].decode('utf-8') + '";'
      try:
        self.cur.execute(select)
        if len(self.cur.fetchall()) == 0:
          self.cur.execute('INSERT INTO ORGANIZER VALUES (NULL, "' + results[0].decode('utf-8') + '", "' + results[1].decode('utf-8') + '");')
          self.db.commit()
          self.cur.execute(select)
          orgID = self.cur.fetchall()[0][0]
        else:
          self.cur.execute(select)
          orgID = self.cur.fetchall()[0][0]
      except(sql.Error, sql.Warning) as e:
        self.bottomText.config(state=tk.NORMAL)   
        self.bottomText.insert(tk.INSERT, str(e) + "\n>> ")
        self.bottomText.config(state=tk.DISABLED)
    
    if not orgID:
      orgID = "NULL"
      
    try:
      select = 'SELECT * FROM EVENT WHERE summary="' + results[2].decode('utf-8') + '" AND start_time="' + results[3].decode('utf-8') + '";'
      self.cur.execute(select)
      if len(self.cur.fetchall()) == 0:
        eventSql = "INSERT INTO EVENT VALUES (NULL, '" +  results[2].decode('utf-8') + "', '" + results[3].decode('utf-8') + "', "
        if results[4].decode('utf-8') == "":
          eventSql += "NULL"
        else:
          eventSql += ("'" + results[4].decode('utf-8') + "'")
          
        if orgID:
          eventSql += (", " + str(orgID) + ", " + results[5].decode('utf-8') + ");")
        else:
          eventSql += (", NULL, " + results[5].decode('utf-8') + ");")
        
        self.cur.execute(eventSql)
        self.db.commit()
        self.cur.execute(select)
    except(sql.Error, sql.Warning) as e:
      self.bottomText.config(state=tk.NORMAL)   
      self.bottomText.insert(tk.INSERT, str(e) + "\n>> ")
      self.bottomText.config(state=tk.DISABLED)

    self.displayStatus()
    
  def clearData(self):
    try:
      self.cur.execute("DELETE FROM ORGANIZER;")
      self.cur.execute("ALTER TABLE ORGANIZER AUTO_INCREMENT = 1;")
      self.db.commit()
    except:
      pass
      
    try:
      self.cur.execute("DELETE FROM EVENT;")
      self.cur.execute("ALTER TABLE EVENT AUTO_INCREMENT = 1;")
      self.db.commit()
    except:
      pass
      
    self.displayStatus()
    
  def displayStatus(self):
    organizers = 0
    events = 0
    self.bottomText.config(state=tk.NORMAL)  
    
    try:
      self.cur.execute("SELECT * FROM ORGANIZER")
      organizers = len(self.cur.fetchall())
    except(sql.Error, sql.Warning) as e:
      self.bottomText.insert(tk.INSERT, str(e) + "\n>> ")
    
    try:
      self.cur.execute("SELECT * FROM EVENT")
      events = len(self.cur.fetchall())
    except(sql.Error, sql.Warning) as e:
      self.bottomText.insert(tk.INSERT, str(e) + "\n>> ")
    
    self.bottomText.insert(tk.INSERT, "Database has " + str(organizers) + " organizers and " + str(events) + " events\n>> ")
    self.bottomText.config(state=tk.DISABLED)
    self.updateScreen()
  
  def queryFalse(self):
    self.win.destroy()
    self.isQuery = False
  
  def selectOrg(self):
    self.outputQuery.config(state=tk.NORMAL)
    text = ""
    try:
      self.cur.execute("SELECT e.start_time, e.summary FROM EVENT e INNER JOIN ORGANIZER o ON e.organizer = o.org_id WHERE o.name = '" + str(self.inputOrg.get()) + "'")
      for row in self.cur.fetchall():
        text += (" ".join(str(i) for i in row) + "\n")
    except(sql.Error, sql.Warning) as e:
      text = e
    
    self.outputQuery.insert(tk.INSERT, str(text) + "-------------------\n")
    self.outputQuery.config(state=tk.DISABLED)
  
  def selectEvsSorted(self):
    self.outputQuery.config(state=tk.NORMAL)
    text = ""
    try:
      self.cur.execute("SELECT * FROM EVENT ORDER BY start_time")
      for row in self.cur.fetchall():
        text += (" ".join(str(i) for i in row) + "\n")
    except(sql.Error, sql.Warning) as e:
      text = e
    
    self.outputQuery.insert(tk.INSERT, str(text) + "-------------------\n")
    self.outputQuery.config(state=tk.DISABLED)
    
  def corOrgs(self):
    self.outputQuery.config(state=tk.NORMAL)
    text = ""
    try:
      self.cur.execute("SELECT o.name FROM ORGANIZER o INNER JOIN EVENT e ON e.organizer = o.org_id WHERE e.location = 'Coruscant'")
      for row in self.cur.fetchall():
        text += (" ".join(str(i) for i in row) + "\n")
    except(sql.Error, sql.Warning) as e:
      text = e
    
    self.outputQuery.insert(tk.INSERT, str(text) + "-------------------\n")
    self.outputQuery.config(state=tk.DISABLED)
    
  def contactOrgs(self):
    self.outputQuery.config(state=tk.NORMAL)
    text = ""
    try:
      self.cur.execute("SELECT * FROM ORGANIZER")
      for row in self.cur.fetchall():
        text += ("Contact " + str(row[1]) + " by mail: " + str(row[2]) + "\n")
        
      self.cur.execute("SELECT o.name, e.location, e.start_time FROM ORGANIZER o INNER JOIN EVENT e ON e.organizer = o.org_id WHERE e.location IS NOT NULL")
      for row in self.cur.fetchall():
        text += (str(row[0]) + " can also be met at " + str(row[1]) + " on " + str(row[2]) + ".\n")
    except(sql.Error, sql.Warning) as e:
      text = e
    
    self.outputQuery.insert(tk.INSERT, str(text) + "-------------------\n")
    self.outputQuery.config(state=tk.DISABLED)
    
  def upcomingAlarms(self):
    self.outputQuery.config(state=tk.NORMAL)
    text = ""
    try:
      self.cur.execute("SELECT * FROM EVENT WHERE num_alarms > 0")
      for row in self.cur.fetchall():
        text += (" ".join(str(i) for i in row) + "\n")
    except(sql.Error, sql.Warning) as e:
      text = e
    
    self.outputQuery.insert(tk.INSERT, str(text) + "-------------------\n")
    self.outputQuery.config(state=tk.DISABLED)
    
  def customSelect(self):
    self.outputQuery.config(state=tk.NORMAL)
    text = ""
    try:
      self.cur.execute(str(self.inputQuery.get()))
      for row in self.cur.fetchall():
        text += (" ".join(str(i) for i in row) + "\n")
    except(sql.Error, sql.Warning) as e:
      text = e
    
    self.outputQuery.insert(tk.INSERT, str(text) + "-------------------\n")
    self.outputQuery.config(state=tk.DISABLED)
  
  def clearResults(self):
    self.outputQuery.config(state=tk.NORMAL)
    self.outputQuery.delete('1.0', tk.END)
    self.outputQuery.config(state=tk.DISABLED)
  
  def executeQuery(self):
    if not self.isQuery:
      self.win = tk.Toplevel(self)
      self.win.wm_title("Execute Query")
      self.win.grid_rowconfigure(0, weight=1)
      self.win.grid_columnconfigure(0, weight=1)
      self.win.resizable(width=False, height=False)
      self.win.geometry("450x450") 
      self.win.protocol("WM_DELETE_WINDOW", self.queryFalse)
      
      tk.Button(self.win, text="Select from Events (Sorted by date)", command=self.selectEvsSorted).grid(row=0, column=0, sticky=tk.W)
      
      tk.Button(self.win, text="Select an Organizer", command=self.selectOrg).grid(row=1, column=0, sticky=tk.W)
      self.inputOrg = tk.Entry(self.win, width=100)
      self.inputOrg.grid(row=2, pady=8)
      self.inputOrg.insert(0, "Insert org name here")
      
      tk.Button(self.win, text="Get Coruscant Organizers", command=self.corOrgs).grid(row=3, column=0, sticky=tk.W)
      
      tk.Button(self.win, text="Get Organizer contacts", command=self.contactOrgs).grid(row=4, column=0, sticky=tk.W)
      
      tk.Button(self.win, text="Get Events with Alarms", command=self.upcomingAlarms).grid(row=5, column=0, sticky=tk.W)
      
      self.inputQuery = tk.Entry(self.win, width=100)
      self.inputQuery.grid(row=6, pady=8)
      tk.Button(self.win, text="Submit", command=self.customSelect).grid(row=7, column=0, sticky=tk.W)
      self.outputQuery = scroll.ScrolledText(self.win, wrap=tk.WORD, height=8)
      self.outputQuery.grid(row=8, pady=10)
      self.outputQuery.config(state=tk.DISABLED)
      tk.Button(self.win, text="Clear", command=self.clearResults).grid(row=9, column=0, sticky=tk.W)
      
      self.inputQuery.insert(tk.INSERT, 'SELECT')
      
      self.isQuery = True
  
  def createWidgets(self):
    self.top = self.winfo_toplevel()
    
    self.menuBar = tk.Menu(self.top)
    self.menuBar.config(font=self.menuFont)
    self.top['menu'] = self.menuBar

    self.fileMenu = tk.Menu(self.menuBar, tearoff=False)
    self.menuBar.add_cascade(label='File', menu=self.fileMenu)
    self.fileMenu.add_command(label='Open... (CTRL+O)', command=self.openCal)
    self.fileMenu.add_command(label='Save (CTRL+S)', command=self.saveCal, state=tk.DISABLED)
    self.fileMenu.add_command(label='Save as... (CTRL+A)', command=self.saveCalAs, state=tk.DISABLED)
    self.fileMenu.add_command(label='Exit (CTRL+X)', command=self.close)
    
    self.createMenu = tk.Menu(self.menuBar, tearoff=False)
    self.menuBar.add_cascade(label='Create', menu=self.createMenu)
    self.createMenu.add_command(label='Create calendar', command=self.createCal)
    self.createMenu.add_command(label='Create event', command=self.createEvent, state=tk.DISABLED)
    self.createMenu.add_command(label='Create alarm', command=self.createAlarm, state=tk.DISABLED)
    self.createMenu.add_command(label='Delete Event', command=self.deleteEvent, state=tk.DISABLED)
    
    self.helpMenu = tk.Menu(self.menuBar, tearoff=False)
    self.menuBar.add_cascade(label='Help', menu=self.helpMenu)
    self.helpMenu.add_command(label='About iCalGUI...', command=self.about)
    
    self.dbMenu = tk.Menu(self.menuBar, tearoff=False)
    self.menuBar.add_cascade(label='Database', menu=self.dbMenu)
    self.dbMenu.add_command(label='Store All Events', command=self.storeAllEvents)
    self.dbMenu.add_command(label='Store Current Event', command=self.storeEvent)
    self.dbMenu.add_command(label='Clear Data', command=self.clearData, state=tk.DISABLED)
    self.dbMenu.add_command(label='Display DB Status', command=self.displayStatus)
    self.dbMenu.add_command(label='Execute Query', command=self.executeQuery)
    
    self.pane = tk.PanedWindow(orient=tk.VERTICAL)
    self.pane.grid(row=0)
    
    self.tree = tkt.Treeview(columns=("Event #", "Props", "Alarms", "Summary"), height=16, padding=0)
    self.tree.column("#0", minwidth=0, width=0, stretch=tk.NO)
    self.tree.heading("Event #", text="Event #")   
    self.tree.column("Event #", minwidth=0, width=80, stretch=tk.NO)
    self.tree.heading("Props", text="Props")   
    self.tree.column("Props", minwidth=0, width=80, stretch=tk.NO) 
    self.tree.heading("Alarms", text="Alarms")   
    self.tree.column("Alarms", minwidth=0, width=80, stretch=tk.NO) 
    self.tree.heading("Summary", text="Summary                        ")   
    self.tree.column("Summary", minwidth=0)
    self.tree.bind("<Double-1>", self.showEvent)
    self.tree.bind('<ButtonRelease-1>', self.selectedEvent)
    
    self.bottomText = scroll.ScrolledText(wrap=tk.WORD, height=12)
    self.pane.add(self.tree)
    self.pane.add(self.bottomText)
    self.bottomText.insert(tk.INSERT, '>> ')
    self.bottomText.config(state=tk.DISABLED)

app = Application()
app.mainloop() 