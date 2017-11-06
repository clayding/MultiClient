
IOTWan的Host端代码。

代码框架里面主要是用Actor类。这个类继承了线程类，同时增加的消息队列，用于给其他线程发送消息和处理其他线程的消息。每个actor的实例就是一个线程，每个线程会不断调用Act和handlemessage函数。handlemessage函数用来处理其他发过来的消息；同时act会不停的处理自己的其他输入信息。具体实现可以看actor.py里面的loop函数。

在host上面，我们会启动一个gw_server的Actor类（GWserver.py），同时为每个AP启动一个SerialThread的actor类(GwSerial.py + GWAp.py - GW_AP类用于保存AP的相关信息；AP与串口的对应及配置都可以再global.py里面修改)。每个SerialThread处理相应的AP发来的串口数据，把相应的cmd（ap=》host）通过message发给gw_server; gw_server在处理完cmd后，如果需要，就给SerialThread发cmd（host=》ap）；然后SerialThread会再通过串口把cmd发给AP.

python工具建议使用pycharm。编辑和运行比较方便。

文件的说明：
ServiceThread.py: Actor的父类，实现线程功能
Messagequeue.py: 实现消息队列
Actor.py: 实现actor功能，每个actor是一个独立的线程，并能够发送和处理消息
Global.py：全局变量，及配置
GwServer.Py：是一个actor，实现server功能，发送和处理与每个AP间的cmd
GWAP.py：用于存储AP的配置，dev_list，数据等信息
GWSerial：是串口读写的Actor，与一个GW_AP相对应，与连接的AP进行串口通信
gw_main.py: host程序的主入口，创建GWServer和SerialThread（也就是GWserial里面的类），并建立之间的actor