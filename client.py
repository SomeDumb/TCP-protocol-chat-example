import socket
import sys
import struct
import threading
import time

class Client:
    def __init__(self):
        """ LOGIN STATES """
        self.register_answers = ["GET LOGIN", 'LOGIN EXISTS', 'LOGIN ACCEPTED', 'REGISTER PASS', 'PASSWORD ACCEPTED']
        self.login_answers = ["AUTH LOGIN", "WRONG AUTH", "UNEXISTED LOGIN", "AUTH PASS", "LOGIN SUCCESSFUL"]
        self.messanger_answers = ["GET MEMBERS", "NOT VALID LIST", "SEND CHATERS", "CONNECT TO THE CHAT", "CHOOSE CHAT", "NO USERS", "SEND CHAT"]
        self.chat_answers = ["MESSAGE FROM"]
        host = socket.gethostname()
        port = 2120
        self.addr = (host,port)
        
        connected = self.connect()
        self.listen_thread = threading.Thread(target=self.listen)
        self.main_menu_thread = threading.Thread(target=self.main_menu)
        self.messanger_menu_thread = threading.Thread(target=self.messanger_menu)
        if connected:

            self.listen_thread.start()
            self.main_menu_thread.start()
    
    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect(self.addr)
        except:
            command = input('Не удалось получить доступ к серверу, повторить попытку? Д/Н:')
            if command.lower() == 'д':
                self.connect()
            else:
                return False
                
        
    
    def main_menu(self):
        while True:
            ''' Главное меню для регистрации и авторизации '''
            
            try:
                command = input('Комманды: 1. Регистрация\n 2. Авторизация \n команда: ')
                if  command == '1':
                    self.send_one_message(b'REGISTER')
                    break
                elif command == '2':
                    self.send_one_message(b'LOGIN')
                    break
                else:
                    self.send_one_message(command.encode('utf-8'))
                    
            except Exception as e:
                print(e)
                print('connection is over')
                break
    
    def messanger_menu(self):
        while True:
            ''' Меню мессенджера '''
            try:
                command = input('Комманды: 1. Создать чат \n 2. Присоеденится существуещему чату\n Комманда: ')
                if  command == '1':
                    self.send_one_message(b'SEND CHATERS')
                    self.send_one_message(b'NEW CHAT')
                    break
                if command == '2':
                    self.send_one_message(b'JOIN CHAT')
                    break
            except:
                pass
    
    def messanger(self, message):
        if message == 'GET MEMBERS':
            members = input('Введите список участников чата: ')
            self.send_one_message(members.encode())
        elif message == 'NOT VALID LIST':
            members = input('Введите корректный список: ')
            self.send_one_message(members.encode())
        elif message == 'CONNECT TO THE CHAT':        
            th = threading.Thread(target=self.chat_menu)
            th.start()
        elif message == 'SEND CHAT':
            i = str(input('Выберите чат!: '))
            self.send_one_message(i.encode())
        elif message == 'NO USERS':
            print('Нет пользователей для запуска чата! Подождите!')
        elif message == 'CHOOSE CHAT':
            pass
        
    def chat_menu(self):
        print('Начало чата!')
        while True:
            message = input('')
            self.send_one_message(message.encode())
            
    def listen(self):
        while True:
            try:
                message = self.recv_one_message(self.socket).decode('utf-8')
                #print(f'\n MESSAGE from server: "{message}"')
                if message in self.register_answers:
                    self.register(message)
                elif message in self.login_answers:
                    self.login(message)
                elif message in self.messanger_answers:
                    self.messanger(message)
                elif message == 'MESSAGE FROM':
                    sender = self.recv_one_message(self.socket).decode('utf-8')
                    print(f'Сообщение от {sender}: ')
                else:
                    print(message)
            except:
                pass
    
    def login(self, message):
        if message == "AUTH LOGIN":
            login = input('Введите логин: ')
            self.send_one_message(login.encode())
        elif message == "AUTH PASS":
            password = input('Введите пароль: ')
            self.send_one_message(password.encode())
        elif message == "LOGIN SUCCESSFUL":
            print("Успешный вход!")
            self.messanger_menu_thread.start()
        elif message == "WRONG AUTH":
            print("Неверный логин или пароль, повторите попытку.")
            self.send_one_message(b'LOGIN')

    def register(self, message):
        if message == 'GET LOGIN':
            login = input('Придумайте логин: ')
            while not login:
                login = input(('Придумайте корректный логин: '))
            self.send_one_message(login.encode())
        elif message == 'LOGIN EXISTS':
            print('Логин существует.')
            login = input('Придумайте другой: ')
            while not login:
                login = input('Придумайте другой: ')
            self.send_one_message(login.encode())
        elif message == 'LOGIN ACCEPTED':
            print('Логин принят!')
        elif message == 'REGISTER PASS':
            password = input('Придумайте пароль: ')
            self.send_one_message(password.encode())
        elif message == 'PASSWORD ACCEPTED':
            print('Пароль принят')
            self.messanger_menu_thread.start()
        else:
            password = input('Придумайте пароль: ')
            while not password:
                password = input('Придумайте пароль: ')
            self.send_one_message(password.encode())         

    def get_chaters(self):
        chaters = False
        while not chaters:
            self.send_one_message(b'\nget_chaters')
            chaters = self.tcp_socket.recv(1024)
        return chaters.decode()
    
    def send_one_message(self, data):
        length = len(data)
        self.socket.sendall(struct.pack('!I', length))
        self.socket.sendall(data)
        #print('MESSAGE SENDED: ', data)
        
    def recvall(self, sock, count):
        buf = b''
        while count:
            newbuf = sock.recv(count)
            if not newbuf: return None
            buf += newbuf
            count -= len(newbuf)
        return buf
    
    def recv_one_message(self, sock):
        lengthbuf = self.recvall(sock, 4)
        length, = struct.unpack('!I', lengthbuf)
        return self.recvall(sock, length)
    
client = Client()