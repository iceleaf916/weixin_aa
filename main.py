#!/usr/bin/python
#! coding=utf-8

import os
import sys
from flask import Flask
from flask import request, make_response, redirect
from flask.ext.sqlalchemy import SQLAlchemy

from wechat_sdk import WechatBasic
from WXBizMsgCrypt import WXBizMsgCrypt

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = \
    'sqlite:///' + os.path.join(basedir, 'data.sqlite')
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True

db = SQLAlchemy(app)

token = "OiE30DUr1JrrUE2z3gsponKLWRdFF7"
encoding_aes_key = "5JWVbmXlhwru2LjNTfw5itMvS5mlKX4iTFoDDEDBpUI"
corpid = "wx67bc386b67021fe5"
wxcpt = WXBizMsgCrypt(token, encoding_aes_key, corpid)
wechat = WechatBasic(token=token)

TEAM_NAMES = {
    "team_01": "001",
    "team_02": "002",
    "team_03": "003",
    "team_04": "004",
    "team_05": "005",
}
START = False
VOTE_LIMIT = 2

class Record(db.Model):
    __tablename__ = 'records'
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(64))
    team_id = db.Column(db.String(64))

    def __repr__(self):
        return '<%s + %s>' % (self.user, self.team_id)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        print ">>>>>", "GET method"
        signature = request.form.get("msg_signature")
        timestamp = request.form.get("timestamp")
        nonce = request.form.get("nonce")
        echostr = request.form.get("echostr")
        if echostr:
            ret, sEchoStr = wxcpt.VerifyURL(signature, timestamp,\
                    nonce, echostr)
            print ">>>>>", sEchoStr
            if sEchoStr:
                return make_response(sEchoStr, 200)
    elif request.method == 'POST':
        print ">>>>>", "POST method"

        signature = request.args.get("msg_signature")
        timestamp = request.args.get("timestamp")
        nonce = request.args.get("nonce")
        body_text = request.data

        ret, body_text = wxcpt.DecryptMsg(body_text, signature, timestamp, nonce)
        wechat.parse_data(body_text)
        message = wechat.get_message()
        response = None
        if message.type == "click":
            if not START:
                response = wechat.response_text(u"活动还未开始")
                response = response.replace(u"\n    ", "").encode("utf-8")
                ret, sEncryptMsg=wxcpt.EncryptMsg(response, nonce)
                if( ret!=0 ):
                    print "ERR: EncryptMsg ret: %s" % ret
                    sys.exit(1)
                return make_response(sEncryptMsg, 200)

            user = message.source
            key = message.key
            res_msg = ""
            if key == "result":
                all_records = Record.query.all()
                res = {}
                for r in all_records:
                    if res.get(r.team_id):
                        res[r.team_id] += 1
                    else:
                        res[r.team_id] = 1
                res_msg = "统计结果："
                for key in ["team_01", "team_02", "team_03", "team_04", "team_05"]:
                    res_msg += "\n%s 队获得 %s 个赞" % (TEAM_NAMES[key], res.get(key, 0))

            elif key in ["team_01", "team_02", "team_03", "team_04", "team_05"]:
                user_records = Record.query.filter_by(user=user)
                if user_records.count() < VOTE_LIMIT:
                    record = Record(user=user, team_id=key)
                    db.session.add(record)
                    db.session.commit()
                    res_msg = u"您已经成功为 %s 队点赞 : )" % TEAM_NAMES[key]
                else:
                    res_msg = u"点赞失败，您最多只能为%s个队点赞！" % VOTE_LIMIT

            if res_msg:
                response = wechat.response_text(res_msg)
        elif message.type == "enter_agent":
            pass
        if response:
            response = response.replace(u"\n    ", "").encode("utf-8")
            ret, sencryptmsg=wxcpt.EncryptMsg(response, nonce)
            if( ret!=0 ):
                print "err: EncryptMsg ret: %s" % ret
                sys.exit(1)
            return make_response(sencryptmsg, 200)
    return make_response("hello world", 200)

@app.route('/hello/')
def hello():
    return "hello world"

if __name__ == '__main__':
    from flask.ext.script import Manager, Shell
    from flask.ext.migrate import Migrate, MigrateCommand
    manager = Manager(app)

    def make_shell_context():
        return dict(app=app, db=db, record=record)
    manager.add_command("shell", Shell(make_context=make_shell_context))

    migrate = Migrate(app, db)
    manager.add_command('db', MigrateCommand)

    manager.run()
