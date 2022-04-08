import socket
import threading
import shortuuid
import bcrypt
import struct
import json
import sys
import os
import select
import time
from datetime import datetime
import logging
import logging.handlers

def breadcrumb(json_dict_or_list, value):
  if json_dict_or_list == value:
    return [json_dict_or_list]
  elif isinstance(json_dict_or_list, dict):
    for k, v in json_dict_or_list.items():
      p = breadcrumb(v, value)
      if p:
        return [k] + p
  elif isinstance(json_dict_or_list, list):
    lst = json_dict_or_list
    for i in range(len(lst)):
      p = breadcrumb(lst[i], value)
      if p:
        return [str(i)] + p

class Server:
    def __init__(self, ip, port):
        
        self.log = logging.getLogger(__name__)

        self.log.setLevel(logging.DEBUG)

        handler = logging.handlers.SysLogHandler(address='/dev/log', facility='local1')

        formatter = logging.Formatter('%(module)s.%(funcName)s: %(message)s')
        
        handler.setFormatter(formatter)

        self.log.addHandler(handler)
        
        handler = logging.StreamHandler(stream=sys.stdout)
        
        self.log.addHandler(handler)
        
        self.host = ip
        self.port = port
        addr = (self.host,self.port)
        if os.path.exists('chats.json'):
            self.chats = self.from_json('chats.json')
        else:
            self.chats = {}
            open('chats.json', mode='a').close()
        
        if os.path.exists('users.json'):
            self.users = self.from_json('users.json')
        else:
            self.users = {}
            open('users.json', mode='a').close()
            
    

        self.connections = {}
        self.chat_connections = {}
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.bind(addr)
            self.socket.listen(2)
            self.log.info(f"Server started on <{ip}:{str(port)}>")
            self.bind()
        except Exception as e:
            self.log.error(f'Unable to listen <{ip}:{str(port)}>')
            self.log.error('SERVER INIT: ' + str(e))
        
    def create_uid(self, dir):
        uid = shortuuid.ShortUUID().random(length=4)
        if uid in dir:
            while uid in self.dir:
                uid = shortuuid.ShortUUID().random(length=4)
        return str(uid)
    
    def create_chat(self, admin, users):
        uid = self.create_uid(self.chats)
        self.chats[uid] = {'users':users, 'admin':admin}
        self.save_dict(self.chats,'chats.json')
        return uid
    
    def register(self, conn, address, message):
        try:
            self.send_one_message(conn, b'GET LOGIN')
            while True:
                login = self.recv_one_message(conn)
                if login==None:
                    raise Exception
                login = login.decode('utf-8')
                uid=self.create_uid(self.users)
                if login in [u['login'] for u in self.users.values()]:
                    self.send_one_message(conn, b'LOGIN EXISTS')
                else:
                    self.send_one_message(conn, b'LOGIN ACCEPTED')
                    break
            
            self.send_one_message(conn, b'REGISTER PASS')
            password = self.recv_one_message(conn)
            if password==None:
                raise Exception
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(password, salt)
            self.users[uid] = {'login':login, 'password':hashed.decode(), 'chats':None}
            self.send_one_message(conn, b'PASSWORD ACCEPTED')
            self.save_dict(self.users,'users.json')
            self.log.info(self.users)
            self.connections[uid]=conn
            th = threading.Thread(target=self.listen_user,args=(conn, address, uid))
            th.start()
        except Exception as e:
            self.log.error('REGISTRATION FAILED: ' + str(e))
    
    def listen_anonim(self, conn, address):
        """ Прослушивание анонимного чатера """
        while True:
            try:
                message = self.recv_one_message(conn)
                if message==None:
                    self.log.info(f'Connection on {address} is over')
                    break
                message = message.decode()
                if message == 'REGISTER':
                    self.register(conn,address, message)
                    break
                elif message == 'LOGIN':
                    self.send_one_message(conn,b'AUTH LOGIN')
                    login = self.recv_one_message(conn)
                    if login==None:
                        raise Exception
                    login = login.decode()
                    if login in [u['login'] for u in self.users.values()]:
                        uid = breadcrumb(self.users, login)[0]

                        self.send_one_message(conn,b'AUTH PASS')
                        passwd = self.recv_one_message(conn)
                        if passwd==None:
                            raise Exception
                        if bcrypt.checkpw(passwd, self.users[uid]['password'].encode()):
                            self.send_one_message(conn,b'LOGIN SUCCESSFUL')
                            self.connections[uid]=conn
                            th = threading.Thread(target=self.listen_user,args=(conn, address, uid))
                            th.start()
                            break
                        else:
                            self.send_one_message(conn,b'WRONG AUTH')
                    else:
                        self.send_one_message(conn,b'AUTH PASS')
                        self.send_one_message(conn,b'WRONG AUTH')
            except Exception as e:
                self.log.error(f"ANONIM MENU: On {str(address)} connection is dead: " + str(e))
                break
    
    def send_all_chaters(self, chat, chat_uid, message):
        for chater in chat['users']:
            try:
                if self.chat_connections[chater]==chat_uid:
                    self.send_one_message(self.connections[chater], message.encode())
            except Exception as e:
                self.log.info( f'SEND MESSAGE TO CHATERS: User {self.users[chater]["login"]} not connected to the chat')
                continue
            
    def listen_chat(self, conn, address, chat_uid, user_uid):
        chat = self.chats[chat_uid]
        self.chat_connections[user_uid]=chat_uid

        message = f'Пользователь "{self.users[user_uid]["login"]}" Вошёл в чат!'
        self.send_all_chaters(chat, chat_uid, message)
        
        while True:
            try:
                message = self.recv_one_message(conn)
                if message==None:
                    message = f'Пользователь {self.users[user_uid]["login"]} покинул чат'
                    self.send_all_chaters(chat, chat_uid, message)
                    break
                message = message.decode()
                message_send = f'Отправлено {datetime.now()} "{self.users[user_uid]["login"]}": {message}'
                self.send_all_chaters(chat, chat_uid, message_send)
            except Exception as e:
                message = f'Пользователь {self.users[user_uid]["login"]} покинул чат'
                self.log.error(f'LISTEN CHAT: {message}:' + str(e))
                self.send_all_chaters(chat, chat_uid, message)
                break
    
    def existing_chat(self, users):
        for u in self.chats:
            if set(self.chats[u]['users']) == set(users):
                return u
        else:
            return False
                
    
    def listen_user(self, conn, address, uid):
        self.connections[uid] = conn
        me = self.users[uid]
        user_uid = uid
        while True:
            try:
                message = self.recv_one_message(conn)
                if message==None:
                    break
                message = message.decode()
                if message == 'NEW CHAT':
                    self.send_one_message(conn,b'GET MEMBERS')
                    users = self.recv_one_message(conn)
                    if users==None:
                        raise Exception
                    
                    users = users.decode('utf-8').split(',')
                    users.append(me['login'])
                    for user in users:
                        if not user in [u['login'] for u in self.users.values()]:
                            self.send_one_message(conn, b'NOT VALID LIST')
                    else:
                        self.send_one_message(conn, b'CONNECT TO THE CHAT')
                        users_uids = [breadcrumb(self.users, user)[0] for user in users]
                        self.log.info(users_uids)
                        uid = self.existing_chat(users_uids)
                        if not uid:
                            uid = self.create_chat(user, users_uids)
                            th = threading.Thread(target=self.listen_chat,args=(conn, address, uid, user_uid))
                            th.start()
                            break
                        else:
                            th = threading.Thread(target=self.listen_chat,args=(conn, address, uid, user_uid))
                            th.start()
                            break
                elif message == 'SEND CHATERS':
                    chaters = [u['login'] for u in self.users.values() if me['login']!=u['login']]
                    if len(chaters)>0:
                        chaters = ', '.join(chaters)
                        message = f'Количество пользователей: {len(self.users)}. \n Пользователи: {chaters}'
                        self.send_one_message(conn, message.encode())
                    else:
                        self.send_one_message(conn, b"NO USERS")
                elif message == 'JOIN CHAT':
                    chats = []
                    self.log.info('joining chat')
                    for chat in self.chats.values():
                        if uid in chat['users']:
                            chats.append(chat)
                    message = ''
                    if len(chats)>0:
                        for i in range(len(chats)):
                            chat = chats[i]
                            message+=f'\n{str(i)}: '
                            users = ",".join([self.users[u]['login'] for u in chat['users']])
                            message+=users
                        self.send_one_message(conn, message.encode())
                        self.send_one_message(conn, b'SEND CHAT')
                        i = self.recv_one_message(conn)
                        if i == None:
                            raise Exception
                        i = i.decode('utf-8')
                        uid = breadcrumb(self.chats, chats[int(i)])[0]

                        self.send_one_message(conn, b'CONNECT TO THE CHAT')
                        th = threading.Thread(target=self.listen_chat,args=(conn, address, uid, user_uid))
                        th.start()
                        break
                    else:
                        self.send_one_message(conn, b'NO CHATS')
                else:
                    self.log.info(message)        
            except Exception as e:
                self.log.error(f'AUTHENTICATED USER: On {str(address)} connection is dead: ' + str(e))
                break
            
    def bind(self):
        while True:
            conn, address = self.socket.accept()
            th = threading.Thread(target=self.listen_anonim,args=(conn, address))
            th.start()
            self.log.info("NEW USER JOIND")
            
    def send_one_message(self, sock, data):
        try:
            length = len(data)
            sock.sendall(struct.pack('!I', length))
            sock.sendall(data)
            self.log.info(f'MESSAGE SENDED: "{data.decode()}"')
        except Exception as e:
            self.log.error(f'MESSAGE NOT SEND: {str(e)}')
        
    def recvall(self, sock, count):
        buf = b''
        while count:
            newbuf = sock.recv(count)
            if not newbuf: return None
            buf += newbuf
            count -= len(newbuf)
        return buf

    def recv_one_message(self, sock):
        try:
            lengthbuf = self.recvall(sock, 4)
            length, = struct.unpack('!I', lengthbuf)
            return self.recvall(sock, length)
        except:
            return None
        
    @staticmethod
    def from_json(file):
        if os.path.getsize(file) > 0:
            with open(file) as json_file:
                data = json.load(json_file)
            return data
        else:
            return {}
    
    @staticmethod
    def save_dict(dictionary,filename):
        with open(filename, "w") as outfile:
            json.dump(dictionary, outfile)