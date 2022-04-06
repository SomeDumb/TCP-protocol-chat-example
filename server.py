#Модуль socket для сетевого программирования
import socket
import threading
import shortuuid
import bcrypt
import struct
import json
import os
def find_key(d, value):
    for k,v in d.items():
        if isinstance(v, dict):
            p = find_key(v, value)
            if p:
                return [k] + p
        elif v == value:
            return [k]

class Server:
    def __init__(self, ip, port):
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
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.bind(addr)
            self.socket.listen()
            print(f"Server started on <{ip}:{port}>")
            self.bind()
        except Exception as e:
            print(f'Unable to listen <{ip}:{port}>')
            print(e)
        

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
    
    @staticmethod
    def from_json(file):
        if os.path.getsize(file) > 0:
            with open(file) as json_file:
                data = json.load(json_file)
            return data
        else:
            return {}
    
    def get_user_chats(self, login):
        pass
    
    @staticmethod
    def save_dict(dictionary,filename):
        with open(filename, "w") as outfile:
            json.dump(dictionary, outfile)
    
    def register(self, conn, address, message):
        try:
            self.send_one_message(conn, b'GET LOGIN')
            while True:
                login = self.recv_one_message(conn).decode('utf-8')
                uid=self.create_uid(self.users)
                if login in [u['login'] for u in self.users.values()]:
                    self.send_one_message(conn, b'LOGIN EXISTS')
                else:
                    self.send_one_message(conn, b'LOGIN ACCEPTED')
                    break
            
            self.send_one_message(conn, b'REGISTER PASS')
            password = self.recv_one_message(conn)
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(password, salt)
            self.users[uid] = {'login':login, 'password':hashed.decode(), 'chats':None}
            self.send_one_message(conn, b'PASSWORD ACCEPTED')
            self.save_dict(self.users,'users.json')
            print(self.users)
            self.connections[uid]=conn
            th = threading.Thread(target=self.listen_user,args=(conn, address, uid))
            th.start()
        except Exception as e:
            print(e)
            print('registration failed')
    
    def listen_anonim(self, conn, address):
        """ Прослушивание анонимного чатера """
        while True:
            try:
                message = self.recv_one_message(conn).decode('utf-8')
                if message == 'REGISTER':
                    self.register(conn,address, message)
                    break
                elif message == 'LOGIN':
                    self.send_one_message(conn,b'AUTH LOGIN')
                    login = self.recv_one_message(conn).decode('utf-8')
                    if login in [u['login'] for u in self.users.values()]:
                        uid = find_key(self.users, login)[0]

                        self.send_one_message(conn,b'AUTH PASS')
                        passwd = self.recv_one_message(conn)
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
                #print(e)
                print(f"On {str(address)} connection is dead")
                break
            
    def listen_chat(self, conn, address, chat, user_uid):
        while True:
            try:
                message = self.recv_one_message(conn).decode('utf-8')
                message_send = self.users[user_uid]['login']+ ':' + message
                for chater in chat['users']:
                    try:
                        if chater != user_uid:
                            self.send_one_message(self.connections[chater], message_send.encode())
                    except:
                        print('User not connected')
                        continue
            except Exception as e:
                print('User disconnected')
                break
    
    def existing_chat(self, users):
        for u in self.chats.values():
            if set(u['users']) == users:
                return u
        return False
                
    
    def listen_user(self, conn, address, uid):
        self.connections[uid] = conn
        me = self.users[uid]
        user_uid = uid
        while True:
            try:
                message = self.recv_one_message(conn).decode()
                if message == 'NEW CHAT':
                    self.send_one_message(conn,b'GET MEMBERS')
                    users = self.recv_one_message(conn).decode('utf-8').split(',')
                    print(users)
                    for user in users:
                        if not user in [u['login'] for u in self.users.values()]:
                            self.send_one_message(conn, b'NOT VALID LIST')
                    else:
                        self.send_one_message(conn, b'CONNECT TO THE CHAT')
                        users_uids = [find_key(self.users, user)[0] for user in users]
                        users_uids.append(uid)
                        print(users_uids)
                        uid = self.existing_chat(users_uids)
                        if not uid:
                            uid = self.create_chat(user, users_uids)
                            self.send_one_message(conn, b'CONNECT TO THE CHAT')
                            th = threading.Thread(target=self.listen_chat,args=(conn, address, uid, user_uid))
                            th.start()
                            break
                        else:
                            self.send_one_message(conn, b'CONNECT TO THE CHAT')
                            th = threading.Thread(target=self.listen_chat,args=(conn, address, uid, user_uid))
                            th.start()
                            break
                elif message == 'SEND CHATERS':
                    chaters = [u['login'] for u in self.users.values() if me['login']!=u['login']]
                    if len(chaters)>1:
                        chaters = ', '.join(chaters)
                        message = f'Количество пользователей: {len(self.users)}. \n Пользователи: {chaters}'
                        self.send_one_message(conn, message.encode())
                    else:
                        self.send_one_message(conn, b"NO USERS")
                elif message == 'JOIN CHAT':
                    chats = []
                    for chat in self.chats.values():
                        if uid in chat['users']:
                            chats.append(chat)
                    message = ''
                    for i in range(len(chats)):
                        chat = chats[i]
                        message+=f'\n{str(i)}: '
                        users = ",".join([self.users[u]['login'] for u in chat['users']])
                        message+=users
                    self.send_one_message(conn, message.encode())
                    self.send_one_message(conn, b'SEND CHAT')
                    i = self.recv_one_message(conn).decode('utf-8')
                    uid = chats[int(i)]
                    self.send_one_message(conn, b'CONNECT TO THE CHAT')
                    th = threading.Thread(target=self.listen_chat,args=(conn, address, uid, user_uid))
                    th.start()
                    break
                else:
                    print(message)        
            except Exception as e:
                print(e)
                print(f"On {str(address)} connection is dead")
                break
            
    def bind(self):
        while True:
            conn, address = self.socket.accept()
            th = threading.Thread(target=self.listen_anonim,args=(conn, address))
            th.start()
            print("NEW USER JOIND")
            
    def send_one_message(self, sock, data):
        try:
            length = len(data)
            sock.sendall(struct.pack('!I', length))
            sock.sendall(data)
            print('MESSAGE SENDED: ', data)
        except:
            pass
        
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
            pass

ip = input('Введите ip сервера: ')
serv = Server(ip, 2120)