#!/usr/bin/python3
#Javier García Céspedes
#Juan Francisco Vara Sánchez
#Lucia Cepedano Gutierrez
import sys
import argparse
import os
import subprocess
import types
from os import fdopen, write
from subprocess import call
from os import path
from lxml import etree
from xml.etree import ElementTree as ET

## auto-p2.py -prepare/launch/stop/release -3
##call[('cp'...)]

############################################################################################################################################
#Definición de constantes:
ordenes = ["prepare", "launch", "stop", "release"]  
sf_interfaces = ["0","10.0.2.11/24","10.0.2.12/24","10.0.2.13/24","10.0.2.14/24","10.0.2.15/24"]
sf_ip = ["0","10.0.2.11","10.0.2.12","10.0.2.13","10.0.2.14","10.0.2.15"]
ip_c1 = "10.0.1.2"
dir_actual = path.curdir ##Devuelve la ruta actual: .
dir_actual_abs = path.abspath(dir_actual) ##Devuelve la ruta absoluta. Ej: /Users/javiergarciacespedes/Desktop/c1/c2
LAN1 = {
    "network":  "10.0.1.0",
    "netmask":  "255.255.255.0",
    "gateway":  "10.0.1.1",
    "broadcast": "10.0.1.255"
}
LAN2 = {
    "network": "10.0.2.0",
    "netmask": "255.255.255.0",
    "gateway": "10.0.2.1",
    "broadcast": "10.0.2.255"
}

############################################################################################################################################
#Argumentos posicionales
    #Definición Comandos
def parseArguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("orden", type=str,help="Posibles valores: prepare, launch, stop y release")
    parser.add_argument("-n", "--num_servers", type=int, default=3,help="Indica el número de servidores. Debe ser un valor entre 1 y 5.")
    args = parser.parse_args()
    return args

    #Comprobar si la orden introducida por comandos es correcta
def compruebaOrden(orden):
    if orden in ordenes:
        return orden
    else:
        print("Las opciones disponibles son: prepare, launch, stop y release") 

    #Comprueba si los servers introducidos están entre 1 y 5 
def compruebaServersMax(num_servers):
    if 0<num_servers and 6>num_servers:
        return num_servers
    else:
        print("El número de servers debe ser un entero entre 1 y 5")

############################################################################################################################################
#Definición de métodos etree:
def pause():
    p=input("Pulsa <ENTER> para continuar...")

############################################################################################################################################
#Prepare: crea todos los ficheros qcow2: bridges, lans y sistemas finales
    #Creación de router y sistemas finales

#Creamos el número de servers y sus ficheros de especificaciones
def creacionMV():
    for i in range(1,num_servers+1):
        s_qcow2 = "s%i.qcow2" % i
        s_xml = "s%i.xml" % i
        call(['qemu-img','create','-f','qcow2','-b','cdps-vm-base-p2.qcow2',s_qcow2])
        call(['chmod','+w',s_qcow2])
        call(['cp','plantilla-vm-p2.xml',s_xml])     
    call(['qemu-img','create','-f','qcow2','-b','cdps-vm-base-p2.qcow2','lb.qcow2'])
    call(['chmod','+w','lb.qcow2'])
    call(['cp','plantilla-vm-p2.xml','lb.xml'])
    call(['qemu-img','create','-f','qcow2','-b','cdps-vm-base-p2.qcow2','c1.qcow2'])
    call(['chmod','+w','c1.qcow2'])
    call(['cp','plantilla-vm-p2.xml','c1.xml'])
    servidores_configurados = num_servers

    #Edición de los ficheros xml con etree:
        #Ficheros s%i
def creacionXMLenSI():
    for i in range(1,num_servers+1):
        s_qcow2 = "s%i.qcow2" % i
        s_xml = "s%i.xml" % i
        s_name = "s%i" % i
        tree = etree.parse(s_xml)
        root = tree.getroot()
        name = root.find("name")
        name.text = s_name
        source1 = root.find("./devices/disk/source")
        source1.set("file",dir_actual_abs + "/" + s_qcow2)
        source2 = root.find("./devices/interface/source")
        source2.set("bridge",'LAN2')
        tree.write(s_xml)
    
    #Fichero c1
def creacionXMLenc1():
    tree = etree.parse('c1.xml')
    root = tree.getroot()
    name = root.find("name")
    name.text = 'c1'
    source1 = tree.find("./devices/disk/source")
    source1.set("file",dir_actual_abs + "/" + "c1.qcow2")
    source2 = tree.find("./devices/interface/source")
    source2.set("bridge",'LAN1')
    tree.write('c1.xml')

        #Fichero lb
def creacionXMLenlb():
    tree = etree.parse('lb.xml')
    root = tree.getroot()
    name = root.find("name")
    name.text = 'lb'
    source1 = tree.find("./devices/disk/source")
    source1.set("file",dir_actual_abs + "/" + "lb.qcow2")
    source2 = tree.find("./devices/interface/source")
    source2.set("bridge",'LAN1')
    tree.write('lb.xml')

    fout = open("lb.xml", 'r+')     
    f_lineas = fout.readlines()
    array_lineas = []
    array_lineas.append("      <interface type='bridge'>\n")
    array_lineas.append("       <source bridge='LAN2'/>\n")
    array_lineas.append("       <model type='virtio'/>\n")
    array_lineas.append("      </interface>\n")

    for linea in f_lineas:
        if "</interface>" in linea:
            index_linea=f_lineas.index(linea)
            
    for i in range(0,len(array_lineas)):
        f_lineas.insert(index_linea+i+1,array_lineas[i])

    with open('lb.xml', 'w') as file:   
        for lineas in f_lineas:
            file.writelines(lineas)

    fout.close()
    
    #Creación de Bridges
def creacionBridges():
    call(['sudo','brctl','addbr','LAN1'])
    call(['sudo','brctl','addbr','LAN2'])
    call(['sudo','ifconfig','LAN1','up'])
    call(['sudo','ifconfig','LAN2','up'])

############################################################################################################################################
#Launch: arranca las máquinas virtuales y su consola
    #Definición de las máquinas virtuales
def definirMV():
    for i in range(1,num_servers+1):
        s_xml = "s%i.xml" % i
        call(['sudo','virsh','define',s_xml])
        arranqueMV("s%i" % i)
    call(['sudo','virsh','define','lb.xml'])
    arranqueMV("lb")
    call(['sudo','virsh','define','c1.xml'])
    arranqueMV("c1")

    #Arranque de las máquinas virtuales
def arranqueMV(name):
    call(['sudo','virsh','start',name])


    #Acceso máquinas virtuales
def accesoMV():
    for i in range(1,num_servers+1):
        s_name = "s%i" % i
        call(['xterm','-e','"sudo','virsh' ,'console', s_name+'"'])
    call(['xterm','-e','"sudo' ,'virsh','console','lb"'])
    call(['xterm','-e','"sudo', 'virsh','console','c1"'])

    #Configuración de red: asignación de direcciones IP
#Para lb:
def configuracionLb():
    fichero_host = open(os.getcwd() + '/hostname', 'w')
    fichero_host.write("lb.qcow2")
    fichero_host.close()
    call(["sudo", "virt-copy-in", "-a", "lb.qcow2", os.getcwd() + "/hostname", "/etc"])
    fichero = open(os.getcwd() + '/interfaces', 'w')
    fichero_aux = ["auto lo\n"
                    , "iface lo inet loopback\n"
                    , "auto eth0\n"
                    , "iface eth0 inet static\n"
                    , "    address "  + LAN1['gateway']  + "\n"
                    , "    network "  + LAN1['network']  + "\n"
                    , "    netmask "  + LAN1['netmask']  + "\n"
                    , "    broadcast "+ LAN1['broadcast']+ "\n\n"
                    , "auto eth1\n"
                    , "iface eth1 inet static\n"
                    , "    address "  + LAN2['gateway']  + "\n"
                    , "    netmask "  + LAN2['netmask']  + "\n"]
    fichero.writelines(fichero_aux)
    fichero.close()
    call(["sudo", "virt-copy-in", "-a","lb.qcow2", os.getcwd() + "/interfaces", "/etc/network"])
    call(["sudo", "virt-cat", "-a","lb.qcow2","/etc/network/interfaces"])
    call(['rm','interfaces'])
    call(['rm','hostname'])


#Para host:
def configuracionHost():
    fichero_host = open(os.getcwd() + '/hostname', 'w')
    fichero_host.write("c1.qcow2")
    fichero_host.close()
    call(["sudo", "virt-copy-in", "-a", "c1.qcow2", os.getcwd() + "/hostname", "/etc"])
    fichero = open(os.getcwd() + '/interfaces', 'w')
    fichero_aux = ["auto lo\n"
                    , "iface lo inet loopback\n"
                    , "auto eth0\n"
                    , "iface eth0 inet static\n"
                    , "    address "  + ip_c1 + "\n"
                    , "    network "  + LAN1['network']  +  "\n"
                    , "    netmask "  + LAN1['netmask']  +  "\n"
                    , "    gateway "  + LAN1['gateway']  +  "\n"]
    fichero.writelines(fichero_aux)
    fichero.close()
    call(["sudo", "virt-copy-in", "-a","c1.qcow2", os.getcwd() + "/interfaces", "/etc/network"])
    call(["sudo", "virt-cat", "-a","c1.qcow2","/etc/network/interfaces"])
    call(['rm','interfaces'])
    call(['rm','hostname'])

    #call(['sudo','ifconfig','LAN1','10.0.1.3/24']) 
    #call(['sudo','ip','route','add','10.0.0.0/16','via','10.0.1.1']) 

#Para num_servers
def configuracionMV():
    for i in range(1,num_servers+1):
        s_qcow2 = "s%i.qcow2" %i
        fichero_host = open(dir_actual_abs + '/hostname', 'w')
        fichero_host.write(s_qcow2)
        fichero_host.close()
        call(["sudo", "virt-copy-in", "-a", s_qcow2, os.getcwd() + "/hostname", "/etc"])
        fichero = open(dir_actual_abs + '/interfaces', 'w')
        fichero_aux = ["auto lo\n"
                        , "iface lo inet loopback\n"
                        , "auto eth0\n"
                        , "iface eth0 inet static\n"
                        , "    address " + sf_ip[i] + "\n"
                        , "    network " + LAN2['network']  +  "\n"
                        , "    netmask " + LAN2['netmask']  +  "\n"
                        , "    gateway " + LAN2['gateway']  +  "\n"]
        fichero.writelines(fichero_aux)
        fichero.close()
        call(["sudo", "virt-copy-in", "-a",s_qcow2, os.getcwd() + "/interfaces", "/etc/network"])
        call(["sudo", "virt-cat", "-a",s_qcow2,"/etc/network/interfaces"])
        call(['rm','interfaces'])
        call(['rm','hostname'])


        #call(['sudo','ifconfig','eth0',sf_interfaces[i]])
        #call(['sudo','ip','route','add','default','via','10.0.2.1']) 

#Puesta en marcha del balanceador ---> linea final: "errorfile 504"
def edicionBalanceador():
    call(['service','apache2','stop'])
    f2=open('/etc/haproxy/haproxy.cfg','a')
    f2.write("\nfrontend lb")
    f2.write("\n    bind *:80")
    f2.write("\n    default_backend webservers")
    f2.write("\n")
    f2.write("\nbackend webservers")
    f2.write("\n    mode http")
    f2.write("\n    balance roundrobin")
    for i in range(1,num_servers+1):
        s_name = "s%i" % i
        f2.write("\n    server " + s_name + sf_interfaces[i] + ":80 check","a")
    f2.close()
    call(['sudo','service','haproxy','restart'])


############################################################################################################################################
#Stop: Para las máquinas virtuales(sin liberarlas)
def pararMV():
    for i in range(1,num_servers+1):
        s_name = "s%i" % i
        call(['sudo','virsh','shutdown',s_name])
    call(['sudo','virsh','shutdown','lb'])
    call(['sudo','virsh','shutdown','c1'])

############################################################################################################################################
#Release: libera el espacio, borrando todos los ficheros creados
def borrarPractica():
    for i in range(1,1+num_servers):
        pararMV()
    ###... falta eliminar todos los fichers creados 
    print(dir_actual_abs)
    #call(['cd','/home/jf.vara/Desktop'])
    #call(['cd',dir_actual_abs])
    for i in range(1,1+num_servers):
        s_qcow2 = "s%i.qcow2" % i
        s_xml = "s%i.xml" % i
        call(['rm',s_qcow2]) #borrar imágenes de los sistemas finales
        call(['rm',s_xml]) #borrar xml de los sistemas finales
        call(['sudo','virsh','undefine',s_xml])
    call(['sudo','virsh','shutdown','c1'])
    call(['sudo','virsh','undefine','lb.xml'])
    call(['sudo','virsh','undefine','c1.xml'])
    call(['rm','lb.xml'])
    call(['rm','lb.qcow2'])
    call(['rm','c1.xml'])
    call(['rm','c1.qcow2'])
    #call(['sudo','rm','cdps-vm-base-p2.qcow2'])
    #call(['sudo','rm','plantilla-vm-p2.xml'])



############################################################################################################################################
#Ejecución de programa: ####INCOMPLETO
#servidores_configurados = 0
if __name__ == '__main__':
    argumentos = parseArguments().__dict__
    orden = compruebaOrden(argumentos['orden'])
    num_servers = compruebaServersMax(argumentos['num_servers'])  
    if orden == "prepare":
        creacionMV()
        creacionXMLenSI()
        creacionXMLenc1()
        creacionXMLenlb()
        creacionBridges()
        print("Todo OK. Escenario preparado")
    elif orden == "launch":
        #num_servers = servidores_configurados
        configuracionLb()
        configuracionHost()
        configuracionMV()
        definirMV()
        #edicionBalanceador()
        #accesoMV()
        print("Todo OK. Escenario ejecutado")
    elif orden == "stop":
        #num_servers = servidores_configurados
        pararMV()
        print("Todo OK. Escenario parado")
    elif orden == "release":
        #num_servers = servidores_configurados
        borrarPractica()
        print("Todo OK. Escenario eliminado")
############################################################################################################################################