import os
import sys
import time
import pickle
import socket
import random
import hashlib
import threading

from tools import *
from collections import OrderedDict

class Node:

    def __init__(self, ip, port):
        self.filenameList = []
        self.ip = ip
        self.port = port
        self.address = (ip, port)
        self.id = getHash(ip + ':' + str(port))
        self.pred = (ip, port)
        self.predID = self.id
        self.succ = (ip, port)
        self.succID = self.id
        self.fingerTable = OrderedDict()

        try:
            self.ServerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.ServerSocket.bind((IP, PORT))
            self.ServerSocket.listen()
        except socket.error:
            print('Socket not opened')

    def listenThread(self):
        '''
        Storing the IP and port in address and saving 
        the connection and threading.
        '''
        while True:
            try:
                connection, address = self.ServerSocket.accept()
                connection.settimeout(120)
                threading.Thread(target=self.connectionThread, args=(connection, address)).start()
            except socket.error:
                pass

    def connectionThread(self, connection, address):
        '''
        Thread for each peer connection.
        Types of connections 0 : peer connect
                             1 : client
                             2 : ping
                             3 : lookupID
                             4 : updateSucc/Pred
        '''
        rDataList = pickle.loads(connection.recv(BUFFER))
        connectionType = rDataList[0]
        if connectionType == 0:
            print(f'Connection with: {address[0]}:{address[1]}')
            print('Join network request recevied')
            self.joinNode(connection, address, rDataList)
            self.printMenu()
        elif connectionType == 1:
            print(f'Connection with: {address[0]}:{address[1]}')
            print('Upload/Download request recevied')
            self.transferFile(connection, address, rDataList)
            self.printMenu()
        elif connectionType == 2:
            connection.sendall(pickle.dumps(self.pred))
        elif connectionType == 3:
            self.lookupID(connection, address, rDataList)
        elif connectionType == 4:
            if rDataList[1] == 1:
                self.updateSucc(rDataList)
            else:
                self.updatePred(rDataList)
        elif connectionType == 5:
            self.updateFingerTable()
            connection.sendall(pickle.dumps(self.succ))
        else:
            print('Problem with connection type')
    
    def joinNode(self, connection, address, rDataList):
        '''
        Deals with join network request by other node.
        '''
        if rDataList:
            peerIPport = rDataList[1]
            peerID = getHash(peerIPport[0] + ':' + str(peerIPport[1]))
            oldPred = self.pred
            self.pred = peerIPport
            self.predID = peerID
            sDataList = [oldPred]
            connection.sendall(pickle.dumps(sDataList))
            time.sleep(0.1)
            self.updateFingerTable()
            self.updateOtherFingerTables()

    def transferFile(self, connection, address, rDataList):
        # Choice: 0 = download, 1 = upload
        choice = rDataList[1]
        filename = rDataList[2]
        fileID = getHash(filename)
        # IF client wants to download file
        if choice == 0:
            print(f'Download request for file: {filename}')
            try:
                if filename not in self.filenameList:
                    connection.send('NotFound'.encode('utf-8'))
                    print('File not found')
                else:
                    connection.send('Found'.encode('utf-8'))
                    self.sendFile(connection, filename)
            except ConnectionResetError as error:
                print(error, '\nClient disconnected\n\n')
        # ELSE IF client wants to upload something to network
        elif choice == 1 or choice == -1:
            print(f'Receiving file: {filename}')
            fileID = getHash(filename)
            print(f'Uploading file ID: {fileID}')
            self.filenameList.append(filename)
            self.receiveFile(connection, filename)
            print('Upload complete')
            if choice == 1:
                if self.address != self.succ:
                    self.uploadFile(filename, self.succ, False)

    def lookupID(self, connection, address, rDataList):
        keyID = rDataList[1]
        sDataList = []

        # Case 0: If keyId at self
        if self.id == keyID:
            sDataList = [0, self.address]
        # Case 1: If only one node
        elif self.succID == self.id:
            sDataList = [0, self.address]
        # Case 2: Node id greater than keyId, ask pred
        elif self.id > keyID:
            if self.predID < keyID:
                sDataList = [0, self.address]
            elif self.predID > self.id:
                sDataList = [0, self.address]
            else:
                sDataList = [1, self.pred]
        # Case 3: node id less than keyId USE fingertable to search
        else:
            if self.id > self.succID:
                sDataList = [0, self.succ]
            else:
                value = ()
                for key, value in self.fingerTable.items():
                    if key >= keyID:
                        break
                value = self.succ
                sDataList = [1, value]
        connection.sendall(pickle.dumps(sDataList))

    def updateSucc(self, rDataList):
        newSucc = rDataList[2]
        self.succ = newSucc
        self.succID = getHash(newSucc[0] + ':' + str(newSucc[1]))
    
    def updatePred(self, rDataList):
        newPred = rDataList[2]
        self.pred = newPred
        self.predID = getHash(newPred[0] + ':' + str(newPred[1]))

    def start(self):
        '''
        Accepting connections from other threads.
        '''
        threading.Thread(target=self.listenThread, args=()).start()
        threading.Thread(target=self.pingSucc, args=()).start()
        # In case of connecting to other clients
        while True:
            print('Listening to other clients')
            self.asAClientThread()
    
    def pingSucc(self):
        while True:
            # Ping every 5 seconds
            time.sleep(2)
            # If only one node, no need to ping
            if self.address == self.succ:
                continue

            try:
                pSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                pSocket.connect(self.succ)
                pSocket.sendall(pickle.dumps([2]))
                recvPred = pickle.loads(pSocket.recv(BUFFER))
            except:
                print('\nOffline node dedected!\nStabilizing...')
                # Search for the next succ from the F table
                newSuccFound = False
                value = ()
                for key, value in self.fingerTable.items():
                    if value[0] != self.succID:
                        newSuccFound = True
                        break
                if newSuccFound:
                    self.succ = value[1]
                    self.succID = getHash(self.succ[0] + ':' + str(self.succ[1]))
                    # Inform new succ to update its pred to me now
                    pSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    pSocket.connect(self.succ)
                    pSocket.sendall(pickle.dumps([4, 0, self.address]))
                    pSocket.close()
                else:
                    self.pred = self.address
                    self.predID = self.id
                    self.succ = self.address
                    self.succID = self.id
                self.updateFingerTable()
                self.updateOtherFingerTables()
                self.printMenu()

    def asAClientThread(self):
        '''
        Handles all outgoing connections and printing options.
        '''
        self.printMenu()
        userChoice = input()
        if userChoice == '1':
            ip = input('Enter IP to connect: ')
            port = input('Enter port: ')
            self.sendJoinRequest(ip, int(port))
        elif userChoice == '2':
            self.leaveNetwork()
        elif userChoice == '3':
            filename = input('Enter filename: ')
            fileID = getHash(filename)
            recvIPport = self.getSuccessor(self.succ, fileID)
            self.uploadFile(filename, recvIPport, True)
        elif userChoice == '4':
            filename = input('Enter filename: ')
            self.downloadFile(filename)
        elif userChoice == '5':
            self.printFingerTable()
        elif userChoice == '6':
            print(f'My ID: {self.id}, Predecessor: {self.predID}, Successor: {self.succID}')

    def sendJoinRequest(self, ip, port):
        try:
            recvIPPort = self.getSuccessor((ip, port), self.id)
            peerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peerSocket.connect(recvIPPort)
            sDataList = [0, self.address]

            peerSocket.sendall(pickle.dumps(sDataList))
            rDataList = pickle.loads(peerSocket.recv(BUFFER))
            self.pred = rDataList[0]
            self.predID = getHash(self.pred[0] + ':' + str(self.pred[1]))
            self.succ = recvIPPort
            self.succID = getHash(recvIPPort[0] + ':' + str(recvIPPort[1]))
            sDataList = [4, 1, self.address]
            pSocket2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            pSocket2.connect(self.pred)
            pSocket2.sendall(pickle.dumps(sDataList))
            pSocket2.close()
            peerSocket.close()
        except socket.error:
            print('Socket error. Recheck IP/Port.')
    
    def leaveNetwork(self):
        # First inform my succ to update its pred
        pSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        pSocket.connect(self.succ)
        pSocket.sendall(pickle.dumps([4, 0, self.pred]))
        pSocket.close()
        # Then inform my pred to update its succ
        pSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        pSocket.connect(self.pred)
        pSocket.sendall(pickle.dumps([4, 1, self.succ]))
        pSocket.close()
        print(f'I had files: {self.filenameList}')
        # And also replicating its files to succ as a client
        print('Replicating files to other nodes before leaving')
        for filename in self.filenameList:
            pSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            pSocket.connect(self.succ)
            sDataList = [1, 1, filename]
            pSocket.sendall(pickle.dumps(sDataList))
            with open(filename, 'rb') as file:
                # Getting back confirmation
                pSocket.recv(BUFFER)
                self.sendFile(pSocket, filename)
                pSocket.close()
                print('File replicate')
            pSocket.close()
        
        self.updateOtherFingerTables()
        self.pred = (self.ip, self.port)
        self.predID = self.id
        self.succ = (self.ip, self.port)
        self.succID = self.id
        self.fingerTable.clear()
        print(self.address, 'has left the network')
    
    def uploadFile(self, filename, recvIPport, replicate):
        print('Uploading file', filename)
        sDataList = [1]
        if replicate:
            sDataList.append(1)
        else:
            sDataList.append(-1)
        try:
            file = open(filename, 'rb')
            file.close()
            sDataList = sDataList + [filename]
            cSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            cSocket.connect(recvIPport)
            cSocket.sendall(pickle.dumps(sDataList))
            self.sendFile(cSocket, filename)
            cSocket.close()
            print('File uploaded')
        except IOError:
            print('File not in directory')
        except socket.error:
            print('Error in uploading file')

    def downloadFile(self, filename):
        print('Downloading file', filename)
        fileID = getHash(filename)
        recvIPport = self.getSuccessor(self.succ, fileID)
        sDataList = [1, 0, filename]
        cSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cSocket.connect(recvIPport)
        cSocket.sendall(pickle.dumps(sDataList))
        fileData = cSocket.recv(BUFFER)
        if fileData == b'NotFound':
            print('File not found:', filename)
        else:
            print('Receiving file:', filename)
            self.receiveFile(cSocket, filename)

    def getSuccessor(self, address, keyID):
        rDataList = [1, address]
        recvIPPort = rDataList[1]
        while rDataList[0] == 1:
            peerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                peerSocket.connect(recvIPPort)
                sDataList = [3, keyID]
                peerSocket.sendall(pickle.dumps(sDataList))
                rDataList = pickle.loads(peerSocket.recv(BUFFER))
                recvIPPort = rDataList[1]
                peerSocket.close()
            except socket.error:
                print('Connection denied while getting Successor')
        return recvIPPort
    
    def updateFingerTable(self):
        for i in range(MAX_BITS):
            entryId = (self.id + (2 ** i)) % MAX_NODES
            if self.succ == self.address:
                self.fingerTable[entryId] = (self.id, self.address)
                continue
            recvIPPort = self.getSuccessor(self.succ, entryId)
            recvId = getHash(recvIPPort[0] + ':' + str(recvIPPort[1]))
            self.fingerTable[entryId] = (recvId, recvIPPort)
    
    def updateOtherFingerTables(self):
        here = self.succ
        while True:
            if here == self.address:
                break
            pSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                pSocket.connect(here)
                pSocket.sendall(pickle.dumps([5]))
                here = pickle.loads(pSocket.recv(BUFFER))
                pSocket.close()
                if here == self.succ:
                    break
            except socket.error:
                print('Connection denied')

    def sendFile(self, connection, filename):
        print('Sending file:', filename)
        try:
            with open(filename, 'rb') as file:
                data = file.read()
                print('File size:', len(data))
                fileSize = len(data)
        except:
            print('File not found')
        try:
            with open(filename, 'rb') as file:
                while True:
                    fileData = file.read(BUFFER)
                    time.sleep(0.001)
                    if not fileData:
                        break
                    connection.sendall(fileData)
        except:
            pass
        print('File sent')

    def receiveFile(self, connection, filename):
        '''
        Receiving file in parts if file already in directory.
        '''
        fileAlready = False
        try:
            with open(filename, 'rb') as file:
                data = file.read()
                size = len(data)
                if size == 0:
                    print('Retransmission request sent')
                    fileAlready = False
                else:
                    print('File already present')
                    fileAlready = True
                return
        except FileNotFoundError:
            pass

        if not fileAlready:
            totalData = b''
            recvSize = 0
            try:
                with open(filename, 'wb') as file:
                    while True:
                        fileData = connection.recv(BUFFER)
                        recvSize += len(fileData)
                        if not fileData:
                            break
                        totalData += fileData
                    file.write(totalData)
            except ConnectionResetError:
                print('Data transfer interupted')
                print('Waiting for system to stabilize')
                print('Trying again in 10 seconds')
                time.sleep(5)
                os.remove(filename)
                time.sleep(5)
                self.downloadFile(filename)

    def printMenu(self):
        print('\nChoose an option:\n1. Join Network\n2. Leave Network')
        print('3. Upload File\n4. Download File\n5. Print Finger Table')
        print('6. Print my predecessor and successor\n')

    def printFingerTable(self):
        print('Printing Finger Table')
        for key, value in self.fingerTable.items(): 
            print(f'KeyID: {key}, Value: {value}')

if __name__ == '__main__':

    if len(sys.argv) < 3:
        print('Arguments not supplied (Defaults used)')
    else:
        IP = sys.argv[1]
        PORT = int(sys.argv[2])

    node = Node(IP, PORT)
    print(f'My ID is: {node.id}')
    node.start()
    node.ServerSocket.close()
