# -*- coding:utf-8 -*-

import websocket,time,json,os,rel,sqlite3,traceback
from threading import Thread
from bs4 import BeautifulSoup

websocket._logging._logger.level = -99

ip='127.0.0.1'
port=5555

SERVER=f'ws://{ip}:{port}'
HEART_BEAT=5005
RECV_TXT_MSG=1
RECV_TXT_CITE_MSG=49
RECV_PIC_MSG=3
USER_LIST=5000
GET_USER_LIST_SUCCSESS=5001
GET_USER_LIST_FAIL=5002
TXT_MSG=555
PIC_MSG=500
AT_MSG=550
CHATROOM_MEMBER=5010
CHATROOM_MEMBER_NICK=5020
PERSONAL_INFO=6500
DEBUG_SWITCH=6000
PERSONAL_DETAIL=6550
DESTROY_ALL=9999
STATUS_MSG=10000
ATTATCH_FILE = 5003
# 'type':49 带引用的消息

'''Initialize HeartbeatHibernate'''
undisturbed_hb = 0

'''Admins Global List'''
OP_list = ['wxid_xd4gc9mu3stx12']

############################# MULTITHREADING ################################
# Extends the Thread class, return values(not recommended)
class ThreadWithReturnValue(Thread):   
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs={}, Verbose=None):
        Thread.__init__(self, group, target, name, args, kwargs)
        self._return = None

    def run(self):
        if self._target is not None:
            self._return = self._target(*self._args,**self._kwargs)
            return self._return

    def join(self, *args):
        Thread.join(self, *args)
        return self._return

################################# OUTPUT&SQL ################################
# Return an ID based on time
def getid():
    return time.strftime("%Y%m%d%H%M%S")

# System Fancy Log
def output(msg,logtype = 'SYSTEM',mode = 'DEFAULT',background = 'DEFAULT'):
    LogColor = {
        'SYSTEM': '034',#Blue
        'ERROR': '037',#White
        'GROUPCHAT': '036',#MINT
        'DM' : '033',#YELLOW
        'HEART_BEAT': '035',#Violet
        'PAT': '037',#White
        'SEND': '032',#Green
        'CALL' : '031',#Red
        'WARNING': '031',#Red
        'CREATE_LINK':'032',#Green
        'STOP_LINK':'031'#Red
    }
    LogMode = {
        'DEFAULT': '0',
        'HIGHLIGHT': '1',
        'UNDERLINE': '4'
    }
    LogBG = {
        'DEFAULT': '',#No BG Color
        'RED' : ';41',# ';' is Intended
        'YELLOW' : ';43',
        'BLUE' : ';44',
        'WHITE' : ';47',
        'GREEN' : ';42',
        'MINT' : ';46'
    }
    color = LogColor.get(logtype)
    mode = LogMode.get(mode)
    bg = LogBG.get(background)

    # Fancy Log
    now=time.strftime("%Y-%m-%d %X")
    print(f"[{now} \033[{mode};{color}{bg}m{logtype}\033[0m] {msg}")

    # Write Error Logs on to Local File
    if logtype == 'ERROR':
        error_log_file = open('ErrorLog.txt','a')
        error_log_file.write(f"[{now} {logtype}] {msg}\n")
        error_log_file.close()

    # print("["+f"{color}[1;35m{LogType}{color}[0m"+"]"+' Success')
    # print(f'[{now}]:{msg}')

# Insert value into a table in an SQL database
def sql_insert(db,dbcur,table,rows,values):
    '''
    Pre-Process
    '''
    # table = f'r{table[:-9]}'
    test_row = rows[-1]
    test_value = values[-1]
    rows = str(rows)[1:-1].replace('\'','')
    values = str(values)[1:-1]
    '''
    Check if line exsists
    '''
    if isinstance(test_value,str):
        check_txt = f"SELECT 1 FROM {table} WHERE {test_row}='{test_value}'"
    else:
        check_txt = f"SELECT 1 FROM {table} WHERE {test_row}={test_value}"
    dbcur.execute(check_txt)
    result = dbcur.fetchone()
    '''
    Value Exists or not
    '''
    if result:
        # output('Skipping This Insert Because Column Exists','WARNING')
        return
    else:
        insert_txt = f"INSERT INTO {table}({rows}) VALUES({values})"
        db.execute(insert_txt)
        db.commit()

# Update values of a table in an SQL database
def sql_update(db,table,col,value,condition = None):
    # table = f'r{table[:-9]}'
    # col = str(col).replace('\'','')

    if isinstance(value,str):
        if condition:
            update_txt = f"UPDATE {table} SET {col} = '{value}' WHERE {condition}"
        else:
            update_txt = f"UPDATE {table} SET {col} = '{value}'"
    else:
        if condition:
            update_txt = f"UPDATE {table} SET {col} = {value} WHERE {condition}"
        else:
            update_txt = f"UPDATE {table} SET {col} = {value}"

    # output(update_txt,mode = 'HIGHLIGHT')
    db.execute(update_txt)
    db.commit()

# Fetch values from table given condition
def sql_fetch(dbcur,table,cols = ['*'],condition = None):
    cols = str(cols)[1:-1].replace('\'','')
    # cols = str(cols)[1:-1]

    if condition:
        fetch_txt = f"SELECT {cols} FROM {table} WHERE {condition}"
    else:
        fetch_txt = f"SELECT {cols} FROM {table}"
    # output(fetch_txt,mode = 'HIGHLIGHT')
    dbcur.execute(fetch_txt)
    result = dbcur.fetchall()
    return [i for i in result]

# Fuzzy Match queries by virtual table in FTS5
def sql_match(db,dbcur,table,cols = ['*'],conditionCol = None,keyword = None):
    if not keyword:
        return ['-1']
    elif not conditionCol:
        return ['-1']

    source = db
    db = sqlite3.connect(":memory:")
    db.backup(source)
    dbcur = db.cursor()

    dbcur.execute('DROP TABLE IF EXISTS fuzzysearch')

    fetchcols = cols
    fetchcols.append(conditionCol)
    origin_data = sql_fetch(dbcur,table,fetchcols)
    # output(origin_data)

    cols = str(cols)[1:-1].replace('\'','')
    fetchcols_str = str(fetchcols)[1:-1].replace('\'','')

    dbcur.execute(f'create virtual table fuzzysearch using fts5({fetchcols_str}, tokenize="porter unicode61");')

    for row in origin_data:
        # output(str(row)[1:-1])
        dbcur.execute(f'insert into fuzzysearch ({fetchcols_str}) values ({str(row)[1:-1]});')

    db.commit()

    if isinstance(keyword,str):
        match_txt = f"SELECT {cols} FROM fuzzysearch WHERE {conditionCol} MATCH '{keyword}*'"
    else:
        match_txt = f"SELECT {cols} FROM fuzzysearch WHERE {conditionCol} MATCH {keyword}*"

    # output(match_txt)
    result = dbcur.execute(match_txt).fetchall()
    # output(result)

    dbcur.execute('DROP TABLE IF EXISTS fuzzysearch')
    db.commit()

    return [i for i in result]

# Drop table
def sql_destroy(db,table):
    destroy_txt = f"DROP TABLE {table}"
    db.execute(destroy_txt)
    db.commit()

# Delete row from table
def sql_delete(db,table,condition = None):
    if not condition:
        output('Did not specify which delete condition.','WARNING',background = "WHITE")
        return ['-1']

    delete_txt = f"DELETE FROM {table} WHERE {condition}"
    db.execute(delete_txt)
    db.commit()

################################### HTTP ####################################
''' I did not use this section afterall so maybe you can try it'''
def send(uri,data):
    base_data={
        'id':getid(),
        'type':'null',
        'roomid':'null',
        'wxid':'null',
        'content':'null',
        'nickname':'null',
        'ext':'null',
    }
    base_data.update(data)
    url=f'http://{ip}:{port}/{uri}'
    res=requests.post(url,json={'para':base_data},timeout=5)
    return res.json()

def get_member_nick(roomid = 'null',wxid = None):
    # 获取指定群的成员的昵称 或 微信好友的昵称
    uri='api/getmembernick'
    data={
        'type':CHATROOM_MEMBER_NICK,
        'wxid':wxid,
        'roomid':roomid or 'null'
    }
    respJson=send(uri,data)
    return json.loads(respJson['content'])['nick']

def get_personal_info():
    # 获取本机器人的信息
    uri='/api/get_personal_info'
    data={
        'id':getid(),
        'type':PERSONAL_INFO,
        'content':'op:personal info',
        'wxid':'null',
    }
    respJson=send(uri,data)
    print(respJson)

################################# websocket #################################
# debug switch
def debug_switch():
    qs={
        'id':getid(),
        'type':DEBUG_SWITCH,
        'content':'off',
        'wxid':'ROOT',
    }
    return json.dumps(qs)

# Returns the message to get nicknames of a person in a chatroom
# Returned value goes to handle_nick function
def get_chat_nick_p(wxid,roomid):
    qs={
        'id':getid(),
        'type':CHATROOM_MEMBER_NICK,
        'wxid': wxid,
        'roomid' : f'{roomid}@chatroom',
        'content' : 'null',
        'nickname':'null',
        'ext':'null'
    }
    return json.dumps(qs)

# Handles chatroom nickname
def handle_nick(j):
    data=eval(j['content'])
    nickname = data['nick']
    wxid = data['wxid']
    roomid = data['roomid']

    sql_update(conn,f'r{roomid[:-9]}','groupUsrName',nickname,f"wxid = '{wxid}'")
    # output(f'nickname:{nickname}')

# Returns the message to get a chatroom memberlist
# Returned value goes to handle_memberlist function
def get_chatroom_memberlist(roomid = 'null'):
    qs={
        'id':getid(),
        'type':CHATROOM_MEMBER,
        'roomid': roomid,
        'wxid':'null',
        'content':'op:list member',
        'nickname':'null',
        'ext':'null'
    }
    # 'content':'op:list member',
    return json.dumps(qs)

# Handles memberlist of a chatroom
def handle_memberlist(j):
    data=j['content']
    for d in data:
        roomid = d['room_id']
        room_num = roomid[:-9]
        # output(f'roomid:{roomid}')
        members = d['member']

        sql_initialize_group(f'r{room_num}')

        for m in members:
            sql_insert(conn,cur,f'r{room_num}',['wxid'],[m])
            sql_insert(conn,cur,'Users',['wxid'],[m])
            ws.send(get_chat_nick_p(m,room_num))

# Returns the message to get personal detail of a person
# Not a lot of detail. Didn't use this
def get_personal_detail(wxid):
    qs={
        'id':getid(),
        'type':PERSONAL_DETAIL,
        'content':'op:personal detail',
        'wxid': wxid,
        'roomid':'null',
        'content':'null',
        'nickname':'null',
        'ext':'null',
    }
    return json.dumps(qs)

# Handles personal details
def handle_personal_detail(j):
    output(j)

# Returns the message to get the current logged in WXID's contacts
# Returned value handled by handle_wxuser_list function
def send_wxuser_list():
    '''
    获取微信通讯录用户名字和wxid
    '''
    qs={
        'id':getid(),
        'type':USER_LIST,
        'roomid':'null',
        'wxid':'null',
        'content':'null',
        'nickname':'null',
        'ext':'null',
    }
    return json.dumps(qs)

# Handle the accounts' contacts
def handle_wxuser_list(j):
    i=0
    for item in j['content']:
        i+=1
        output(f"{i} {item['wxid']} {item['name']}")

        if item['wxid'][-8:] == 'chatroom':
            sql_insert(conn,cur,'Groupchats',['roomid','groupname'],[item['wxid'][:-9],item['name']])
            sql_update(conn,'Groupchats','groupname',item['name'],f"roomid = '{item['wxid'][:-9]}'")
        else:
            sql_insert(conn,cur,'Users',['wxid','wxcode','realUsrName'],[item['wxid'],item['wxcode'],item['name']])


    ws.send(get_chatroom_memberlist(item['wxid']))

    # output('启动完成')

################################# INITIALIZE ###############################
# Heartbeat to the local websocket server
def heartbeat(msgJson):
    global undisturbed_hb
    undisturbed_hb += 1
    if undisturbed_hb < 5:
        output('Success','HEART_BEAT','HIGHLIGHT')
    elif undisturbed_hb == 5:
        output('Undisturbed in 5 min. Hiding heartbeat logs. zZZ',logtype = 'HEART_BEAT',mode = 'HIGHLIGHT')

    # print("["+f"\033[1;35m{LogType}\033[0m"+"] "+' Success')

# On opening, refresh the contact and everyone's alias in chatrooms
def on_open(ws):
    #初始化
    ws.send(send_wxuser_list())
    for wxid in OP_list:
        sql_update(conn,'Users','powerLevel',3,f"wxid = '{wxid}'")

    # ws.send(get_chatroom_memberlist())

# On error, output an error message in the terminal
def on_error(ws,error):
    output(f'on_error:{error}','ERROR','HIGHLIGHT','RED')

# On close, send out a warning indicating that the server closed
def on_close(ws,signal,status):
    output("Server Closed",'WARNING','HIGHLIGHT','WHITE')

# Initialize one SQL table for groupchat
def sql_initialize_group(roomid):
    initialize_group = f'''CREATE TABLE IF NOT EXISTS {roomid}
            (wxid TEXT,
            groupUsrName TEXT);'''
    conn.execute(initialize_group)
    conn.commit()

# Initialize a table for all users
def sql_initialize_users():
    initialize_users = f'''CREATE TABLE IF NOT EXISTS Users
            (wxid TEXT,
            wxcode TEXT,
            arcID NUMBER NOT NULL DEFAULT -1,
            qqID NUMBER NOT NULL DEFAULT -1,
            pjskID NUMBER NOT NULL DEFAULT -1,
            realUsrName TEXT,
            powerLevel NUMBER NULL DEFAULT 0,
            banned NUMBER NOT NULL DEFAULT 0);'''
    conn.execute(initialize_users)
    conn.commit()

# Initialize a table to record the groupnames
def sql_initialize_groupnames():
    initialize_gn = f'''CREATE TABLE IF NOT EXISTS Groupchats
            (roomid TEXT,
            groupname TEXT);'''
    conn.execute(initialize_gn)
    conn.commit()

################################# SEND MSG #################################
# Destroy the city you live in
def destroy_all():
    qs={
        'id':getid(),
        'type':DESTROY_ALL,
        'content':'none',
        'wxid':'node',
    }
    return json.dumps(qs)

# Return the message to send a Wechat Message to given wxid
def send_msg(msg,wxid='null'):
    if msg.endswith('.png'):
        msg_type=PIC_MSG
    else:
        msg_type=TXT_MSG

    qs={
        'id':getid(),
        'type':msg_type,
        'wxid':wxid,
        'roomid':'null',
        'content':msg,
        'nickname':'null',
        'ext':'null'
    }

    output(f'{msg} -> {wxid}','SEND')
    return json.dumps(qs)

# Return the message to send an attachment(file/image) to given wxid
def send_attatch(filepath,wxid = 'null'):
    qs={
        'id':getid(),
        'type':ATTATCH_FILE,
        'wxid':wxid,
        'roomid':'null',
        'content':filepath,
        'nickname':'null',
        'ext':'null'
    }
    output(f'File @ {filepath} -> {wxid}','SEND')
    return json.dumps(qs)

############################## HANDLES #####################################
# Pat/Newcomer
def handle_status_msg(msgJson):
    # output(f'收到消息:{msgJson}')

    if '拍了拍我' in msgJson['content']['content']:
        # patpat
        pass

    if '邀请' in msgJson['content']['content']:
        # Newcomer in groupchat
        # Refresh/send welcome message
        ws.send(send_wxuser_list())
        roomid=msgJson['content']['id1']
        ws.send(send_msg(f'欢迎进群',wxid=roomid))

# Sent message log
def handle_sent_msg(msgJson):
    output(msgJson['content'],mode = 'HIGHLIGHT')

# Cite/Shared Links
def handle_cite_msg(msgJson):
    # 处理带引用的文字消息和转发链接
    msgXml=msgJson['content']['content'].replace('&amp;','&').replace('&lt;','<').replace('&gt;','>')
    soup=BeautifulSoup(msgXml,features="xml")

    if soup.appname.string == '哔哩哔哩':
        output(f'Video from BiliBili: {soup.title.string} URL: {soup.url.string}')
        return

    # print(soup.prettify())
    refmsg = [child for child in soup.refermsg.strings if child != '\n']
    # output(refmsg)

    msgJson={
        'content':soup.select_one('title').text,
        'refcontent': refmsg[5],
        'refnick': refmsg[4],
        'id':msgJson['id'],
        'id1':msgJson['content']['id2'],
        'id2': refmsg[2],
        'id3':'',
        'srvid':msgJson['srvid'],
        'time':msgJson['time'],
        'type':msgJson['type'],
        'wxid':msgJson['content']['id1']
    }
    handle_recv_msg(msgJson)

# Handles nothing
def handle_at_msg(msgJson):
    output(msgJson)

# Pictures
def handle_recv_pic(msgJson):
    msgJson = msgJson['content']

    if msgJson['id2']:
        roomid=msgJson['id1'] #群id
        senderid=msgJson['id2'] #个人id
        
        nickname = sql_fetch(cur,f'r{roomid[:-9]}',['groupUsrName'],f"wxid = '{senderid}'")[0][0]
        roomname = sql_fetch(cur,'Groupchats',['groupname'],f'roomid = {roomid[:-9]}')[0][0]
        '''
        Terminal Log
        '''
        output(f'{roomname}-{nickname}: [IMAGE]','GROUPCHAT')
    else:
        senderid=msgJson['id1'] #个人id
        destination = senderid

        nickname = sql_fetch(cur,'Users',['realUsrName'],f"wxid = '{senderid}'")[0][0]
        '''
        Terminal Log
        '''
        output(f'{nickname}: [IMAGE]','DM')

# Call(Activated by handle_recv_msg)
def handle_recv_call(keyword,callerid,destination,nickname,roomname = None):
    # Check if banned
    caller_isbanned = sql_fetch(cur,'Users',['banned'],f"wxid = '{callerid}'")
    if caller_isbanned[0][0] == 1:
        return

    # Split input by space
    call_data = keyword.split(' ')
    #handle mobile @
    if len(call_data) > 1 and call_data[0] == '':
        call_data = call_data[1:]

    # Functions switch
    # 'callkeyword': function
    # Add more if you want
    functions = {
        'bind': bindID,
        'ban': ban,
        'unban':unban,
        'refresh': refresh,
        'setadmin':setadmin,
        'punch':punch,
        'setsuper': setsuper,
    }
    '''
    Terminal Log
    '''
    if roomname:
        output(f'{roomname}-{nickname}: {keyword}','CALL','HIGHLIGHT')
    else:
        output(f'{nickname}: {keyword}','CALL','HIGHLIGHT')

    '''
    Call individual function
    '''
    real_data = call_data[1:] # real input data seperated by space
    send_function = send_msg # can change by using conditions, didnt do it

    # Some time-consuming functions run on a seperate thread
    if call_data[0].lower() == 'help':
        ws.send(send_msg('这可能需要一会,请耐心等待。',destination))
        t = Thread(target='[YOUR FUNCTION HERE]',args = ('[YOUR ARGUMENTS HERE]'))
        t.start()
        return

    # If called non-existent function
    if call_data[0].lower() not in functions.keys():
        output('Called non-existent function','WARNING',background = 'WHITE')
        ws.send(send_msg('没有该指令。',destination))
        return

    # Call function, reply 
    try:
        # Functions return a list, msg is at [0]
        ansList = functions.get(call_data[0].lower())(real_data,callerid,destination)
        # Reply message
        ws.send(send_function(ansList[0],destination))

    # Except errors, reply error message
    except Exception as e:
        # traceback
        output(traceback.print_exc())
        # log
        output(f'ERROR ON CALL: {e}','ERROR','HIGHLIGHT','RED')
        # reply
        ws.send(send_msg('出错了＿|￣|○\n请尝试检查指令参数，调用help或把WDS@出来',destination))

    # ws.send(send_msg('收到调用',dest))

# Handle recieved message
def handle_recv_msg(msgJson):
    # Disturbed, reset Heartbeat count
    global undisturbed_hb
    undisturbed_hb = 0

    # output(msgJson)
    
    isCite = False
    # If cite message
    if msgJson['id2']:
        isCite = True

    # Chatroom message
    if '@chatroom' in msgJson['wxid']:
        roomid=msgJson['wxid'] #群id
        senderid=msgJson['id1'] #个人id
        
        nickname = sql_fetch(cur,f'r{roomid[:-9]}',['groupUsrName'],f"wxid = '{senderid}'")[0][0]
        roomname = sql_fetch(cur,'Groupchats',['groupname'],f'roomid = {roomid[:-9]}')[0][0]
        '''
        Handle User Calls
        '''
        keyword=msgJson['content'].replace('\u2005','')
        # 如果开头是@
        if keyword[:8] == '@WindBot':
            handle_recv_call(keyword[8:],senderid,roomid,nickname,roomname)
            return
        '''
        Terminal Log
        '''
        if not isCite:
            output(f'{roomname}-{nickname}: {keyword}','GROUPCHAT')
        else:
            output(f"{roomname}-{nickname}: {keyword}\n\
                「-> {msgJson['refnick']} : {msgJson['refcontent']}",'GROUPCHAT')
    # Direct Message
    else:
        roomid = None
        senderid=msgJson['wxid'] #个人id
        destination = senderid
        nickname = sql_fetch(cur,'Users',['realUsrName'],f"wxid = '{senderid}'")[0][0]
        '''
        Handle User Calls
        '''
        # 如果开头是@
        keyword=msgJson['content'].replace('\u2005','')
        if keyword[:2] == 'WB':
            handle_recv_call(keyword[2:],senderid,senderid,nickname)
            return
        '''
        Terminal Log
        '''
        if not isCite:
            output(f'{nickname}: {keyword}','DM')
        else:
            output(f"{nickname}: {keyword}\n\
                「-> {msgJson['refnick']} : {msgJson['refcontent']}",'DM')
    '''
    RESPONSE TO KEYWORD
    '''
    if keyword == 'help':
        if roomid:
            ws.send(send_attatch('Y:\\our\\help\\image\\path\\help.jpg',msgJson['wxid']))
    elif keyword=='ding':
        ws.send(send_msg('dong',wxid=msgJson['wxid']))
    elif keyword=='dong':
        ws.send(send_msg('ding',wxid=msgJson['wxid']))
    elif keyword == '6':
        if roomid:
            ws.send(send_msg('WB很不喜欢单走一个6哦',wxid=msgJson['wxid']))
            # ban([msgJson['id1']],OP_list[0],msgJson['wxid'])

######################### ON MSG SWITCH #####################################
def on_message(ws,message):
    j=json.loads(message)
    resp_type=j['type']
    # output(j)
    # output(resp_type)

    # switch结构
    action={
        CHATROOM_MEMBER_NICK:handle_nick,
        PERSONAL_DETAIL:handle_personal_detail,
        AT_MSG:handle_at_msg,
        DEBUG_SWITCH:handle_recv_msg,
        PERSONAL_INFO:handle_recv_msg,
        TXT_MSG:handle_sent_msg,
        PIC_MSG:handle_sent_msg,
        ATTATCH_FILE:handle_sent_msg,
        CHATROOM_MEMBER:handle_memberlist,
        RECV_PIC_MSG:handle_recv_pic,
        RECV_TXT_MSG:handle_recv_msg,
        RECV_TXT_CITE_MSG:handle_cite_msg,
        HEART_BEAT:heartbeat,
        USER_LIST:handle_wxuser_list,
        GET_USER_LIST_SUCCSESS:handle_wxuser_list,
        GET_USER_LIST_FAIL:handle_wxuser_list,
        STATUS_MSG:handle_status_msg,
    }
    action.get(resp_type,print)(j)

############################# FUNCTIONS #####################################

# Demonstration Function
def bindID(datalist,callerid,roomid = None):
    bindapp = {
        'arc': 'arcID',
        'qq': 'qqID',
        'pjsk': 'pjskID'
    }
    app, usrID = datalist[0],datalist[1]
    appsqlID = bindapp.get(app)

    sql_update(conn,'Users',appsqlID,usrID,f"wxid = '{callerid}'")

    message = f'已绑定至 {app}ID: {usrID}'
    return [message]

########################## MANAGING FUNCTIONS ##############################
# Ignore calls from wxid
def ban(datalist,callerid,roomid):
    # output(datalist)
    caller_level = sql_fetch(cur,'Users',['powerLevel'],f"wxid = '{callerid}'")
    # output(caller_level)

    if caller_level[0][0] < 2:
        return ['您的权限不足。']
    # output(roomid)

    if datalist[0] == '*':
        datalist = [row[0] for row in sql_fetch(cur,f'r{roomid[:-9]}',['wxid'])]

    cnt = 0
    for nickname in datalist:
        wxid = nickname
        if wxid[:4] != 'wxid':
            try:
                wxid = sql_fetch(cur,f'r{roomid[:-9]}',['wxid'],f"groupUsrName = '{nickname}'")[0][0]
            except Exception as e:
                output('Skipping user because user doesn\'t exist','WARNING','HIGHLIGHT','WHITE')
                continue
        if wxid in OP_list:
            ws.send(send_msg('不建议ban了WDS捏',roomid))
            continue
        cnt += 1
        # output(wxid)
        sql_update(conn,'Users','banned',1,f"wxid = '{wxid}'")

    return[f'应Ban{len(datalist)}人,实Ban{cnt}人,下班']

# Unban
def unban(datalist,callerid,roomid):
    # output(datalist)
    caller_level = sql_fetch(cur,'Users',['powerLevel'],f"wxid = '{callerid}'")
    # output(caller_level)

    if caller_level[0][0] < 2:
        return ['您的权限不足。']

    # output(roomid)
    if datalist[0] == '*':
        datalist = [row[0] for row in sql_fetch(cur,f'r{roomid[:-9]}',['wxid'])]

    cnt = 0
    for nickname in datalist:
        wxid = nickname
        if wxid[:4] != 'wxid':
            try:
                wxid = sql_fetch(cur,f'r{roomid[:-9]}',['wxid'],f"groupUsrName = '{nickname}'")[0][0]
            except Exception as e:
                output('Skipping user because user doesn\'t exist','WARNING','HIGHLIGHT','WHITE')
                continue
        cnt += 1
        # output(wxid)
        sql_update(conn,'Users','banned','0',f"wxid = '{wxid}'")

    return[f'应Unban{len(datalist)}人,实Unban{cnt}人,下班']

# Refresh Users list on the go
def refresh(datalist,callerid,roomid = None):
    caller_level = sql_fetch(cur,'Users',['powerLevel'],f"wxid = '{callerid}'")
    # output(caller_level)

    if caller_level[0][0] < 3:
        return ['您的权限不足。']

    ws.send(send_wxuser_list())
    return['已刷新']

# Set admin to user
def setadmin(datalist,callerid,roomid = None):
    caller_level = sql_fetch(cur,'Users',['powerLevel'],f"wxid = '{callerid}'")
    # output(caller_level)

    if caller_level[0][0] < 2:
        return ['您的权限不足。']

    if datalist[0] == '*':
        datalist = [row[0] for row in sql_fetch(cur,f'r{roomid[:-9]}',['wxid'])]

    cnt = 0
    for nickname in datalist:
        wxid = nickname
        if wxid[:4] != 'wxid':
            try:
                wxid = sql_fetch(cur,f'r{roomid[:-9]}',['wxid'],f"groupUsrName = '{nickname}'")[0][0]
                if wxid in OP_list:
                    continue
            except Exception as e:
                output('Skipping user because user doesn\'t exist','WARNING','HIGHLIGHT','WHITE')
                continue
        cnt+=1
        # output(wxid)
        sql_update(conn,'Users','powerLevel',2,f"wxid = '{wxid}'")

    return[f'应设置{len(datalist)}人,实设置{cnt}人,下班']

# Punch somebody to remove their admin privilege
def punch(datalist,callerid,roomid = None):
    caller_level = sql_fetch(cur,'Users',['powerLevel'],f"wxid = '{callerid}'")
    # output(caller_level)

    if caller_level[0][0] < 2:
        return ['您的权限不足。']
    cnt = 0

    if datalist[0] == '*':
        datalist = [row[0] for row in sql_fetch(cur,f'r{roomid[:-9]}',['wxid'])]

    for nickname in datalist:
        wxid = nickname
        if wxid[:4] != 'wxid':
            try:
                wxid = sql_fetch(cur,f'r{roomid[:-9]}',['wxid'],f"groupUsrName = '{nickname}'")[0][0]
            except Exception as e:
                output('Skipping user because user doesn\'t exist','WARNING','HIGHLIGHT','WHITE')
                continue
        if wxid in OP_list:
            ws.send(send_msg('不建议取消WDS的权限捏',roomid))
            continue
        # output(wxid)
        cnt+=1
        sql_update(conn,'Users','powerLevel',0,f"wxid = '{wxid}'")

    return[f'应取消{len(datalist)}人,实取消{cnt}人,下班']

# Rickroll Function
def setsuper(datalist,callerid,roomid = None):
    ws.send(send_msg('NEVER GONNA GIVE YOU UP\nBUT I AM GONNA LET YOU DOWN\nSAY GOODBYE',roomid))
    ban([callerid],'wxid_xd4gc9mu3stx12',roomid)
    punch([callerid],'wxid_xd4gc9mu3stx12',roomid)
    return['']

################################ MAIN #######################################
# This if contition runs when you start the program
if __name__ == "__main__":
    ''' Initialize SQL'''
    conn = sqlite3.connect('./botDB.db')
    cur = conn.cursor()

    sql_initialize_users()
    sql_initialize_groupnames() 

    '''Initialize Websocket'''
    # websocket.enableTrace(True)
    ws = websocket.WebSocketApp(SERVER,
                            on_open=on_open,
                            on_message=on_message,
                            on_error=on_error,
                            on_close=on_close)

    ws.run_forever(dispatcher=rel, reconnect=5)  # Set dispatcher to automatic reconnection, 5 second reconnect delay if connection closed unexpectedly
    rel.signal(2, rel.abort)  # Keyboard Interrupt
    rel.dispatch()