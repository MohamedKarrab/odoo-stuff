# -*- coding: utf-8 -*-
"""
Created on Mon Jan 17 19:00:50 2022

@author: User
"""
from . import auth
import time
import os
import signal
import sys
import json
from . import default_models as dm
from getpass import getpass
directory = os.getcwd()

DEFAULT_USER = "your-email@here.please"
DEFAULT_PASSWORD = "your-password"
DEFAULT_DB = "SSK_ERP_16"

directory = os.getcwd()

class Menu:
    def __init__(self, host):
        self.host = host
        self.db = ''
        self.model_list = []
        self.running = True  # Flag to track whether the program is running

    def check_access(self, uid, password, model, query):
        res = {}
        for ac in ['read', 'write']:
            access = query.execute_kw(self.db, uid, password, model, 'check_access_rights', [ac], {'raise_exception': False})
            res[ac] = access
        return res
    
    def fields_models(self, uid, password, model, query):
        fields = []
        field = query.execute_kw(self.db, uid, password, model, 'fields_get', [], {})
        fields = [f for f in field]
        return fields
    
    def read_model(self, uid, password, model, query, fields):
        model_data = query.execute_kw(self.db, uid, password, model, 'search_read', [], {'fields': fields})        
        if model_data:
            for m in model_data:
                json_data = json.dumps(model_data, indent=4, ensure_ascii=False)        
                print(json_data)
                folder_path = './retrieved_data'
                os.makedirs(folder_path, exist_ok=True)
                file_path = os.path.join(folder_path, f'{model}_model_data.json') 
                with open(file_path, 'a', encoding='utf-8') as file:
                    file.write(json_data + "\n")
                            
    def list_available_models(self):
        if not self.model_list:
            print('No models have been brute-forced yet.')
            return False
        else:
            print('List of available models:')
            for idx, m in enumerate(self.model_list):
                print(f"{idx}: {m}")
            return True
    
    def pause_operation(self, signum, frame):
        """This function is called when CTRL+C is pressed."""
        print("\nCTRL+C detected: Pausing threads, please wait...")
        response = input('[s]top / [c]ontinue / [e]xit: ').strip().lower()
        if response == 's':
            self.running = False  # Stop the operation but keep the program running
        elif response == 'c':
            self.running = True  # Continue the operation
        elif response == 'e':
            sys.exit()

    def MenuOptions(self, version):
        # Set up signal handler for CTRL+C (SIGINT)
        signal.signal(signal.SIGINT, self.pause_operation)
        
        user = input(f"Enter a valid portal or internal user (default: {DEFAULT_USER}) >> ") or DEFAULT_USER
        password = getpass(f"Enter the password (default: {DEFAULT_PASSWORD}) >> ") or DEFAULT_PASSWORD
        self.db = input(f"Specify the database to audit (default: {DEFAULT_DB}) >> ") or DEFAULT_DB

        conexion = auth.Conexion(host=self.host)
        authentic = conexion.proxy('/xmlrpc/2/common')
        uid = authentic.authenticate(self.db, user, password, [])
        if not uid:
            print("Unable to continue without credentials for the instance!")
            return False
        
        op = True
        query = conexion.proxy('/xmlrpc/2/object')
        while op:
            print('\n')
            print('[1] Retrieve instance models')
            print('[2] Retrieve messages')
            print('[3] Brute-force access to models')
            print('[4] List available models')
            print('[5] Get information about an available model')
            print('[x] Exit')
            
            option = input('>> ')
            
            if option == '1':
                access = self.check_access(uid, password, 'ir.model', query)
                print('Model : ir.model Access_Read : ', access['read'])
                print('Model : ir.model Access_write : ', access['write'])
                if access['read']:
                    res = query.execute_kw(self.db, uid, password, 'ir.model', 'search_read', [[]], {'fields': ['name', 'model']})
                    for r in res:
                        try:
                            print('*' * 50)
                            a = self.check_access(uid, password, r['model'], query)
                            print('Model: ', r['model'])
                            print('Model name: ', r['name'])
                            print('Access: Read[', a['read'], '] Write[', a['write'], ']')
                            print('*' * 50)
                            print('')
                            time.sleep(0.5)
                        except Exception as e:
                            pass
                        
            elif option == '2':
                access = self.check_access(uid, password, 'mail.mail', query)
                if access['read']:
                    normalize = lambda p: p if p else ''
                    path = '/mails_' + self.db
                    os.makedirs(directory + path, exist_ok=True)
                    model_mail = query.execute_kw(self.db, uid, password, 'mail.mail', 'search_read', [[]], {'fields': ['name']})
                    print(model_mail)
                    print(len(model_mail), 'Records found!')
                    print('Processing information!')
                    for record in model_mail:
                        record_mail = query.execute_kw(self.db, uid, password, 'mail.mail', 'search_read', [[['id', '=', record['id']]]], {'fields': ['body_html', 'email_to', 'email_from']})
                        if record_mail:
                            record_mail = record_mail[0]
                            with open('./mails_{}/'.format(self.db) + str(record['id']) + '.html', 'w') as f:
                                f.write('email_to ' + normalize(record_mail['email_to']))
                                f.write('email_from ' + normalize(record_mail['email_from']))
                                f.write(record_mail['body_html'])
                                f.close()
                        time.sleep(4)
                else:
                    print('No access to mail.mail')
            
            elif option == '3':
                models = dm.default_models_odoo_old if version['version'] in ['9.0', '10.0', '11.0', '12.0'] else dm.default_models_odoo_new
                self.model_list = []
                self.running = True
                print('Starting brute force, Hit CTRL+C to pause or stop!')
                for m in models:
                    if not self.running:
                        print("Operation paused.")
                        break
                    
                    try:
                        access = self.check_access(uid, password, m, query)
                        print('*' * 50)
                        print('Model : ', m, ' Access_Read : [', access['read'], ']')
                        print('Model : ', m, ' Access_write : [', access['write'], ']')
                        print('*' * 50)
                        print('')
                        if access['read'] or access['write']:
                            self.model_list.append(m)
                    except Exception as e:
                        pass
                print('Process completed!')
                    
            elif option == '4':
                self.list_available_models()
            
            elif option == '5':
                            if self.list_available_models():
                                print('')
                                try:
                                    selected_input = input('Enter model index or name (name doesn\'t have to be in the list): ').strip()
                                    
                                    try:
                                        selected_model = self.model_list[int(selected_input)]
                                    except (ValueError, IndexError):
                                        selected_model = selected_input
            
                                    print(f'Retrieving data for <{selected_model}> model:')
              
                                    fields = self.fields_models(uid, password, selected_model, query)
                                    
                                    self.read_model(uid, password, selected_model, query, fields)
                                except Exception as e:
                                    print(f"An error occurred while retrieving data for model {selected_model}: {str(e)}")
            
            elif option == 'x':
                op = False

