import modbus_tk
import modbus_tk.defines as cst
from modbus_tk import modbus_rtu
import serial
import struct
import datetime
import math

namefile=r"d:\dev"
noscill=4 #номер осциллограмы для чтения минус 1
n_com="13"
n_modbus=15
vsego=0

base_date=datetime.datetime(1900,1,1)
try:
    serialPort = serial.Serial(port='COM'+n_com, baudrate = 19200, bytesize = 8, parity = 'N', stopbits = 1, xonxoff = 0)
    master = modbus_rtu.RtuMaster(serialPort)
    master.set_timeout(2.0)
except:
    print('Не удалось открыть порт на чтение устройства')
else:
    try:
        
        s=''
        s1=''
        header=True
        ol=[]
        os=[]
        oe=[]
        data=[]
        vsego = master.execute(n_modbus,cst.READ_HOLDING_REGISTERS,0x7a6f,1)[0]
        print("Всего осциллограмм:"+str(vsego))
        if vsego>0:
            x=0
            result1=()
            while x<vsego*7:
                zapros= 125 if vsego*7>x+125 else vsego*7-x
                result1 = result1+master.execute(n_modbus,cst.READ_HOLDING_REGISTERS,0x7a72+x, zapros)
                x=x+zapros
                
        oscill=()
        for x in range(vsego):
            ol.append(int(result1[x*7]))
            os.append((base_date + datetime.timedelta(seconds=result1[x*7+1]*65536+result1[x*7+2],milliseconds=result1[x*7+3])).isoformat(sep=" "))
            oe.append((base_date + datetime.timedelta(seconds=result1[x*7+4]*65536+result1[x*7+5],milliseconds=result1[x*7+6])).isoformat(sep=" "))
            print(x+1, ol[x],os[x],oe[x])
        while True:
            try:
                noscill=int(input("Введите номер осциллограммы для чтения:"))
            except:
                print("Ошибка, вы ввели не целое число!!!")
                continue
            break
        
        #print("ваш выбор=",noscill)
        noscill=noscill-1
        if (noscill>=0) & (noscill<=vsego):
            print("Читаем осциллограму №{0:d}".format(noscill+1))
            print(noscill+1, ol[noscill],os[noscill],oe[noscill])
            x=0
            number_file=1
            while header:
                master.execute(n_modbus, cst.WRITE_MULTIPLE_REGISTERS, 0x4096, output_value=[noscill+1])
                result = master.execute(n_modbus,cst.READ_FILE_RECORD,[x,],[124,],number_file=[number_file,])
                x=x+124
                serialPort.flushInput()
                serialPort.flushOutput()
                
                serialPort.flush()
                for y in result[0]:
                    if header:
                        s=s+struct.pack('H',y).decode('cp1251')
                        if s.find("BINARY\r\n")>0:
                            header=False
                            s=s.replace("BINARY","ASCII")
                            sign=s.split("\r\n")
                            sign=sign[1].split(",")
                            sign=(int(sign[0]), int(sign[1].replace("A","")), int(sign[2].replace("D","")))
                    else:
                        #s1=s1+'{0:x} '.format(y)
                        data.append(y)
            lenrecord=5+sign[1]+math.ceil(sign[2]/16)
            if data[0]==26:
                data=data[1:]
                
            while len(data)<ol[noscill]*lenrecord:
                if ol[noscill]*lenrecord-124>len(data):
                    zapros=124
                else:
                    zapros=ol[noscill]*lenrecord-len(data)
                if x+zapros>65535:
                    zapros=65536-x
                master.execute(n_modbus, cst.WRITE_MULTIPLE_REGISTERS, 0x4096, output_value=[noscill+1])
                segment=x&0xffff
                result = master.execute(n_modbus,cst.READ_FILE_RECORD,[x,],[zapros,],number_file=[number_file,])
                x=x+zapros
                if x==65536:
                    x=0
                    number_file=number_file+1
                print(x, number_file)
                serialPort.flushInput()
                serialPort.flushOutput()
                serialPort.flush()
                data=data+list(result[0])
            
            dascii=""
            for i in range(0, len(data), 5+sign[1]+math.ceil(sign[2]/16)):
                d=struct.unpack('II',struct.pack('HHHH',data[i+0],data[i+1],data[i+2],data[i+3]))
                sascii="{0:d},{1:d}".format(d[0],d[1])
                for j in range(sign[1]):
                    d=d+struct.unpack('h',struct.pack('H',data[i+j+4]))
                    sascii=sascii+","+str(d[j+2])
                bity=[]
                for j in range(math.ceil(sign[2]/16)):
                    bity=bity+list(reversed("{0:0>16b}".format(data[i+sign[1]+j+4])))
                for j in range(sign[2]):
                    sascii=sascii+','+bity[j]
                dascii=dascii+sascii+"\r\n"
                #d=d+bity[0:sign[2]]
                #print(d)
            #print(s)
            #print(dascii)
        serialPort.close()
    except:
        print('Не удалось прочитать устройство. Устройство недоступно.')
    else:
        print('Устройство доступно по переднему порту')
        if (noscill>=0) & (noscill<=vsego):
            handle=open(namefile+str(noscill+1)+".cfg","w")
            handle.write(s.replace("\r\n","\n"))
            handle.close()
            handle=open(namefile+str(noscill+1)+".dat","w")
            handle.write(dascii.replace("\r\n","\n"))
            handle.close()
        else:
            print("вы указали отсутствующую осциллограмму")
            
        
