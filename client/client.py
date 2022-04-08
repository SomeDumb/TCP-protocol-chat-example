import socket
import sys
import struct
import threading
import time
from datetime import datetime
import os
import logging
import logging.handlers

class Client:
    def __init__(self, ip):
        """ Server answers """
        self.register_answers = ["GET LOGIN", 'LOGIN EXISTS', 'LOGIN ACCEPTED', 'REGISTER PASS', 'PASSWORD ACCEPTED']
        self.login_answers = ["AUTH LOGIN", "WRONG AUTH", "UNEXISTED LOGIN", "AUTH PASS", "LOGIN SUCCESSFUL"]
        self.messanger_answers = ["GET MEMBERS", "NOT VALID LIST", \
            "SEND CHATERS", "CONNECT TO THE CHAT", "CHOOSE CHAT", \
                "NO USERS", "SEND CHAT", "NO CHATS","CHAT EXISTS"]
        
        host = ip
        port = 2120
        self.addr = (host,port)

        connected = self.connect()



        self.log = logging.getLogger(__name__)

        self.log.setLevel(logging.DEBUG)

        handler = logging.handlers.SysLogHandler(address='/dev/log', facility='local1')

        formatter = logging.Formatter('%(module)s.%(funcName)s: %(message)s')
        
        handler.setFormatter(formatter)

        self.log.addHandler(handler)
        
        handler = logging.StreamHandler(stream=sys.stdout)
        
        self.log.addHandler(handler)

        """ Menu threads """
        self.listen_thread = threading.Thread(target=self.listen)
        self.main_menu_thread = threading.Thread(target=self.main_menu)
        self.messanger_menu_thread = threading.Thread(target=self.messanger_menu)
        
        if connected:
            self.listen_thread.start()
            self.main_menu_thread.start()
    
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
                self.log.error( 'Connection to the server is over')
                break   
    
    def auth(self, message):
        """ Обработка ответов сервера во время авторизации """
        if message == "AUTH LOGIN":
            self.login = input('Введите логин: ')
            self.send_one_message(self.login.encode())
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
        """ Обработка ответов сервера во время регистрации """
        if message == 'GET LOGIN':
            self.login = input('Придумайте логин: ')
            while not self.login:
                self.login = input(('Придумайте корректный логин: '))
            self.send_one_message(self.login.encode())
        elif message == 'LOGIN EXISTS':
            print('Логин существует.')
            self.login = input('Придумайте другой: ')
            while not self.login:
                self.login = input('Придумайте другой: ')
            self.send_one_message(self.login.encode())
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
    
    
    def messanger_menu(self):
        """ Authorized user menu """
        while True:
            
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
                self.log.error( 'Connection to the server is over')

    def chat_menu(self):
        """ Input in concrete chat """
        print('Начало чата!')
        while True:
            message = input()
            try:
                self.send_one_message(message.encode())
            except:
                self.log.error( 'Connection to the server is over')

    def connect(self):
        """ Create socket """
        while True:
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect(self.addr)
                return True
            except:
                command = input('Не удалось получить доступ к серверу, повторить попытку? Д/Н:')
                if command.lower() == 'д':
                    self.connect()
                else:
                    return False
    
    def messanger(self, message):
        """ Authorized user processing server answer """
        if message == 'GET MEMBERS':
            members = input('Введите список участников чата: ')
            self.send_one_message(members.encode())
        elif message == 'NOT VALID LIST':
            members = input('Введите корректный список: ')
            self.send_one_message(members.encode())
        elif message == 'CONNECT TO THE CHAT':        
            self.chat_menu_thread = threading.Thread(target=self.chat_menu)
            self.chat_menu_thread.start()
        elif message == 'SEND CHAT':
            i = str(input('Выберите чат!: '))
            self.send_one_message(i.encode())
        elif message == 'NO USERS':
            print('Нет пользователей для запуска чата! Подождите!')
        elif message == 'NO CHATS':
            answer = input('Нет созданных чатов, создать чат? д/н: ')
            if answer.lower() == 'д':
                self.send_one_message(b'SEND CHATERS')
                self.send_one_message(b'NEW CHAT')
            else:
                self.messanger_menu_thread = threading.Thread(target=self.messanger_menu)
                self.messanger_menu_thread.start()
        
    def listen(self):
        """ Listen to the server and send answer to specific func that processes answer """
        while True:
            try:
                message = self.recv_one_message().decode('utf-8')
                if message in self.register_answers:
                    self.register(message)
                elif message in self.login_answers:
                    self.auth(message)
                elif message in self.messanger_answers:
                    self.messanger(message)
                elif message == 'MESSAGE FROM':
                    sender = self.recv_one_message().decode('utf-8')
                    print(f'Сообщение от {sender}: ')
                else:
                    if hasattr(self, 'chat_menu_thread'):
                        if self.chat_menu_thread.is_alive():
                            print('\n'+message)
                    else:
                        print(message)
                    
            except Exception as e:
                self.log.error( 'Connection to the server is over')
                break

    
    def send_one_message(self, data):
        try:
            length = len(data)
            self.socket.sendall(struct.pack('!I', length))
            self.socket.sendall(data)
        except:
            self.log.error( 'Connection to the server is over')
        
    def recvall(self, count):
        buf = b''
        while count:
            newbuf = self.socket.recv(count)
            if not newbuf: return None
            buf += newbuf
            count -= len(newbuf)
        return buf
    
    def recv_one_message(self):
        lengthbuf = self.recvall(4)
        length, = struct.unpack('!I', lengthbuf)
        return self.recvall(length)