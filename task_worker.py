#coding:utf-8

from requests import Session
import urllib3,re,json,threading
from multiprocessing.managers import BaseManager
from multiprocessing import Queue

def check_order(appleId,password,w):
    headers = {
        "Host": "secure.store.apple.com",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": '1',
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 UBrowser/6.2.4094.1 Safari/537.36",
        "Accept-Encoding": "gzip, deflate, br",
    }
    s = Session()
    # Pip安装第三方包遇到SSL错误,解决方法：pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org 包名
    # 报错：requests.exceptions.SSLError: HTTPSConnectionPool，解决方法：s.verify=False
    s.verify = False
    # 警告：InsecureRequestWarning: Unverified HTTPS request is being made. Adding certificate verification is strongly advised，解决方法：urllib3.disable_warnings()
    urllib3.disable_warnings()
    # /cn/shop/order/list?hist=90 得到登录网址
    s.headers = headers
    url_order_list = r"https://secure.store.apple.com/cn/shop/order/list"

    # 报错:requests.exceptions.TooManyRedirects: Exceeded 30 redirects.,解决方法：allow_redirects=False
    response_order_list = s.get(url_order_list, allow_redirects=False)
    url_order_list = response_order_list.headers['location']
    secure_host = re.search('secure.+?.com', url_order_list).group()
    s.headers['Host'] = secure_host

    response_order_list = s.get(url_order_list, allow_redirects=False)
    url_corat = response_order_list.headers['location']

    response_corat = s.get(url_corat)
    textView_corat = response_corat.content.decode('utf-8')
    url_corat_long = re.search('customerLogin":{"url":"(https.+?)",', textView_corat).groups()[0]

    para_x_aos_stk = re.search('x-aos-stk":"(.{5,20})"}},', textView_corat).groups()[0]
    s.headers['X-Requested-With'] = 'XMLHttpRequest'
    s.headers['Content-Type'] = 'application/x-www-form-urlencoded'
    s.headers['x-aos-model-page'] = 'sentryLoginOlssNP'
    s.headers['syntax'] = 'graviton'
    s.headers['modelVersion'] = 'v2'
    s.headers['x-aos-stk'] = para_x_aos_stk
    s.headers['Referer'] = url_corat

    data_corat = "loginHomeOLSS.customerLogin.appleId={}&loginHomeOLSS.customerLogin.password={}".format(appleId,
                                                                                                         password)
    response_corat = s.post(url_corat_long, data=data_corat)
    html_hist_90 = response_corat.json()['head']['data']['url']
    s.headers['Referer'] = url_corat_long

    response_hist_90 = s.get(html_hist_90)

    url_order_w = "https://secure1.store.apple.com/cn/shop/order/detail/506738/{}?_si=000010".format(w)
    s.headers['Referer'] = html_hist_90
    response_order = s.get(url_order_w)

    str_order = re.search(r'init_data.+?({[\s\S]+?)</script>', response_order.content.decode('utf-8')).groups()[0]
    json_order = json.loads(str_order)
    orderItemDetails = json_order['body']['orderDetail']['orderItems']['orderItem-0000101']['orderItemDetails']['d']
    orderItemStatusTracker = json_order['body']['orderDetail']['orderItems']['orderItem-0000101']['orderItemStatusTracker']['d']
    try:
        deliveryDate = json_order['body']['orderDetail']['orderItems']['orderItem-0000101']['orderItemDetails']['d'][
            'deliveryDate']
        productName = json_order['body']['orderDetail']['orderItems']['orderItem-0000101']['orderItemDetails']['d'][
            'productName']
        totalPrice = json_order['body']['orderDetail']['orderItems']['orderItem-0000101']['orderItemDetails']['d'][
            'totalPrice']
        lastName = \
        json_order['body']['orderDetail']['orderItems']['orderItem-0000101']['shippingInfo']['shipping-address']['d'][
            'lastName']
        firstName = \
        json_order['body']['orderDetail']['orderItems']['orderItem-0000101']['shippingInfo']['shipping-address']['d'][
            'firstName']
        street = \
        json_order['body']['orderDetail']['orderItems']['orderItem-0000101']['shippingInfo']['shipping-address']['d'][
            'street']
        street2 = \
        json_order['body']['orderDetail']['orderItems']['orderItem-0000101']['shippingInfo']['shipping-address']['d'][
            'street2']
    except:
        return orderItemDetails['deliveryDate'],orderItemStatusTracker['statusDescription']
    else:
        return [lastName, firstName, street, street2, productName, totalPrice, deliveryDate]

# 创建类似的QueueManager:
class QueueManager(BaseManager):
    pass

# 由于这个QueueManager只从网络上获取Queue，所以注册时只提供名字:
QueueManager.register('queue_accounts')
QueueManager.register('queue_order_list')

# 连接到服务器，也就是运行task_master.py的机器:
server_addr = '192.168.31.47'
print('Connect to server %s...' % server_addr)

# 端口和验证码注意保持与task_master.py设置的完全一致:
m = QueueManager(address=(server_addr, 5000), authkey=b'abc')

# 从网络连接:
m.connect()

# 获取Queue的对象:
accounts = m.queue_accounts()
order_list = m.queue_order_list()

def main():
    try:
        account = accounts.get(timeout=1)
        order_detail=check_order(account[0], account[1], account[2])
        order_list.put(order_detail)
    except Queue.Empty:
        print('accounts queue is empty.')
if __name__ == '__main__':
    main()


