import os
import subprocess
import io
import sys
import signal
import glob
import logging
import threading
import time
import asyncio

realout = sys.stdout
currentJob=None
jobs = []
bgResults = {}
logging.basicConfig(format='%(message)s')
logging.getLogger().setLevel(logging.INFO)

def bghandler():
    while True:
        for i in jobs:
            out,err = i[0].communicate()
            poll = i[0].poll()
            if poll is not None:
                if i[2]:
                    evalCommand(i[2],False,([out],i[3]))
                elif i[3] == "":
                    logging.info(out)
                jobs.remove(i)



def ctrlchandler(*a,**b):
    if currentJob != None:
        try:
            os.kill(currentJob[0].pid,signal.SIGTERM)
        except Exception as err:
            print(err)

signal.signal(signal.SIGINT, ctrlchandler)

def ctrlzhandler(*a,**b):
    if currentJob != None:
        try:
            os.kill(currentJob[0].pid,signal.SIGTSTP)
        except Exception as err:
            print(err)

signal.signal(signal.SIGTSTP, ctrlzhandler)

def main():
    exit = False
    x = threading.Thread(target=bghandler, daemon=True)
    x.start()
    while not exit:
        dir = subprocess.run(["pwd"],stdout=subprocess.PIPE,text=True)
        currentDir = dir.stdout[:-1]
        command = input(currentDir + "$")
        sys.stdout.flush()
        command = parseCommand(command)
        evalCommand(command,False,None)

def evalCommand(command,subcom,prevIn):

    results = []
    infile = None
    if prevIn:
        if prevIn[1] == "|":
            infile = prevIn[0]
        if prevIn[1] == ">":
            infile = writeFile(prevIn[0],getNext(command))
    bg = False
    if command and command[-1] == "&":
        bg = True
    command = subCommandCheck(command)
    while command:
        current,type = getNext(command)
        if type == "<":
            infile = getFile(current)
        else:
            result = evalResults(infile,current,type,subcom,bg,command)
            if bg:
                break
            infile = None
        if type == "|":
            infile=result
        elif type == ">":
            return writeFile(result,getNext(command))
        elif type == "":
            return result

def getFile(current):
    return open(current[0],'r')

def writeFile(result,command):
    f = open(command[0][0],'w')
    for i in result:
        f.write(i)
    return ""

def printResults(result):
    if result:
        for i in result:
            print(i,flush=True)

def getNext(command):
    current = []
    while command:
        token = command.pop(0)
        if token == "|" or token == ">" or token == "<":
            return current,token
        else:
            current.append(token)
    return current,""

def subCommandCheck(command):
        output = []
        foundStart = False
        start = -1
        end = -1
        subcommand = []
        for index,value in enumerate(command):
            entry = value
            if entry:
                if entry[0] == "$" and not foundStart:
                    if entry[1] == "(":
                        entry = entry[2:]
                        foundStart = True
                        start = index
                output.append(entry)
        if foundStart:
            for index,value in reversed(list(enumerate(output))):
                if value[-1]== ")":
                    output[index] = output[index][0:-1]
                    end = index
                    break
            for i in range(start,end+1):
                subcommand.append(output[i])
            for i in range(start,end+1):
                output.pop(start)
            result = ""
            for i in evalCommand(subcommand,True,None):
                result += str(i)
            result = result[:-1]
            output.insert(start,result)
        return output

def evalResults(infile,command,type,subcom,bg,whole):
    result=[]
    globList = doglob(command)
    for toRun in globList:
        result.append(execCommand(infile,toRun,type,subcom,bg,whole))
    return result

def doglob(command):
    globList = []
    globbed = False
    for index, value in enumerate(command):
        for index2,value2 in enumerate(value):
            if value2 == "*" or value2 == "?":
                globbed = True
                for com in glob.glob(value):
                    newCom = command.copy()
                    newCom[index] = com
                    globList.append(newCom)
    if not globbed:
        globList.append(command)
    return globList

def execCommand(infile,command,type,subcom,bg,whole):
    global realout
    global currentJob
    toprint = False
    if type == "" and not subcom:
        toprint = True

    if command[0] == "cd":
        doCd(command)
        return ""
    elif command[0] == "jobs":
        getJobs(command)
        return ""
    elif command[0] == "bg":
        doBg(command)
        return ""
    elif command[0] == "fg":
        doFg(command)
        return ""
    elif command[0] == "exit":
        quit()
    else:
        if infile == None:
            infile = [""]
        if toprint:
            outputter = realout
        else:
            outputter = subprocess.PIPE
        output = []
        for i in infile:
            try:
                if not bg:
                    proc = subprocess.Popen(command,stdout=outputter,text=True,stdin=subprocess.PIPE,preexec_fn=os.setsid)
                    if i:
                        proc.stdin.write(i[0])
                    currentJob = [proc,command[0],whole,type]
                    """while proc.poll is not None:
                        proc.stdin.write(input())
                        print(proc.stdout.readline())"""
                    stdout,stderr = proc.communicate()
                    currentJob=None
                    if toprint:
                        output.append("")
                    else:
                        output.append(stdout)
                else:
                    if command[-1] == "&":
                        command = command[:-1]
                    proc = subprocess.Popen(command,stdout=subprocess.PIPE,text=True,stdin=subprocess.PIPE)
                    proc.stdin.write(i)
                    jobs.append([proc,command[0],whole,type])
                    return ""
            except Exception as err:
                logging.info(err)
                logging.info ("Command Not Found")
                return None
        return output

def makeSTDIN(input):
    f = io.StringIO(input)

def parseCommand(command):
    commandList = command.split()
    return commandList


def drawScreen():
    pass

def makeLineList(bgChr):
    rows,columns = os.popen("stty size","r").read().split()
    pass

def doCd(command):
    if len(command) >= 2:
        os.chdir(os.path.expanduser(command[1]))
    else:
        os.chdir(os.path.expanduser("~"))

def getJobs(command):
    for i in jobs:
        print("PID: " + str(i[0].pid) + " " + i[1])

def doFg(command):
    if len(command)==1:
        getJobs(command)
    else:
        for i in jobs:
            if str(i[0].pid) == command[1]:
                p = i[0]
                currentJob = (p,i[2])
                while p.poll() is not None:
                    time.sleep(0.1)
                jobs.remove(i)
                if p[2]:
                    evalCommand(p[2][:-1],False,(stdout,p[3]))

def doBg(command):
        p = currentJob[0]
        jobs.append(currentJob)
        currentJob[0].send_signal(signal.SIGCONT)
        currentJob[3].append("&")
        currentJob=None


if __name__ == "__main__":
    main()
