import os
import sys
import time
import json
import re
import paramiko


class SSH_CONNECT():
    def __init__(self, cfg):
        self._cfg = cfg

    def exec_host_cmd(self, content, debug=False):
        result = ""
        for x in range(5):
            print("SSH Connect IP %s ..." % self._cfg['mgmt_ip'])
            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(self._cfg['mgmt_ip'], 22, username=self._cfg['username'], password=self._cfg['password'], timeout=5)
                stdin, stdout, stderr = client.exec_command(content)
                result = stdout.read()
                client.close()
                break
            except Exception as err:
                print(err)
                print("Connect IP %s ...fail, Wait 30 seconds and reconnect" % self._cfg['mgmt_ip'])
                time.sleep(30)

        if debug == True: print(result)
        return result

    def ping(self, ip, count=15, debug=False):
        expected_str = '64 bytes from ' + ip

        result_ping = self.exec_host_cmd('ping -c {} {}'.format(count, ip), debug)
        if(expected_str in result_ping.decode()):
            return 'success'
        else:
            return 'failure'

    def run_cmd(self, cmd, debug=False):
        run_result = self.exec_host_cmd(cmd, debug)
        return run_result

def show_step(step, msg, sieve_len=40):
    str_len = (len(msg) + len( "Step"+str(step)+":"))/2
    both_len = sieve_len-int(str_len)
    if both_len < 0:
        left_right = int(str_len)
    else:
        left_right = int(str_len)*2+(int(both_len)*2)
    print()
    print("="*left_right)
    print("%s" % "="*both_len+"Step"+str(step)+":"+msg+"="*both_len)
    print("="*left_right)


if len(sys.argv) < 4:
    print('no argument')
    sys.exit()

print("user:pw= "+sys.argv[1])
print("Host IP: " +sys.argv[2])
print("upload images: " + sys.argv[3])
user_pw=sys.argv[1]
host_ip = sys.argv[2]

vm_name = ""
vm_ip = ""

show_step(1, "Check upload "+sys.argv[3]+ " file")
cmd1 = 'curl -X GET -u '+user_pw+' '+host_ip+':30880/kapis/virtualization.ecpaas.io/v1alpha1/minio/images'
print(cmd1)
result = os.popen(cmd1).read()
print("result= %s" % result)
result = json.loads(result)
result_list = result["items"]
file_mark=0
if result["items"] == None:
    print("Not found any body.. ")
else:
    print("File Length: "+ str(len(result_list)))
    for j in range(0, len(result_list)):
        if result_list[j]["name"] == sys.argv[3] and result_list[j]["size"] != 0:
            file_mark=1
            print("Found that the file already exists")
            break

if file_mark == 0:
    show_step(1.1, "Start upload "+sys.argv[3]+ " file")
    upload_file = "uploadfile=@"+sys.argv[3]
    url = "/kapis/virtualization.ecpaas.io/v1alpha1/minio/image"
    cmd1 = 'curl -X POST -u '+user_pw+' -H "Content-Type: multipart/form-data" --form "'+upload_file+'" '+host_ip+':30880'+url
    print(cmd1)
    result = os.popen(cmd1).read()
    print("result= %s" % result)

    show_step(1.2, "Check upload file size")
    for i in range(5):
        time.sleep (10)
        cmd1 = 'curl -X GET -u '+user_pw+' '+host_ip+':30880/kapis/virtualization.ecpaas.io/v1alpha1/minio/images'
        print(cmd1)
        result = os.popen(cmd1).read()
        print("result= %s" % result)
        result = json.loads(result)
        result_list = result["items"]
        if result["items"] == None:
            print("Not found any body.. ")
            continue
        print("File Length: "+ str(len(result_list)))
        loop_mark=1
        for j in range(0, len(result_list)):
            if result_list[j]["name"] == sys.argv[3] and result_list[j]["size"] != 0:
                loop_mark=0
                break
            else:
                continue
        if loop_mark == 0: break



show_step(2, "create template image with "+sys.argv[3])
data = {
    "cpu_cores": 1,
    "description": "",
    "memory": 2,
    "minio_image_name": sys.argv[3],
    "name": "i2",
    "os_family": "ubuntu",
    "shared": False,
    "size": 20,
    "type": "cloud",
    "version": "20.04_LTS_64bit"
}
url = "/kapis/virtualization.ecpaas.io/v1/namespaces/default/images"
cmd1 = 'curl -u '+user_pw+' -H "Content-Type: application/json" -X POST -d \''+json.dumps(data)+'\' '+host_ip+':30880'+url
result = os.popen(cmd1).read()
print("result= %s" % result)
#time.sleep (180)
result = json.loads(result)

show_step(2.1, "Check virtual machine status from "+result["id"])
cmd1 = "kubectl get dv " + result["id"]
for x in range(0, 36):
    time.sleep(20)
    result_vm_status = os.popen(cmd1).read()
    print(result_vm_status)
    if "100.0" in result_vm_status:
        break
    else:
        if x <= 35: continue
        print("The virtual machine took too long to create. fail")
        sys.exit(0)

show_step(3, "Create a virtual machine template by "+result["id"])
time.sleep(5)
data = {
    "name": "h1",
    "description": "",
    "cpu_cores": 1,
    "memory": 2,
    "disk": [],
    "guest": {
        "username": "root",
        "password": "abc1234"
    },
    "image": {
        "id": result["id"],
        "size": 20,
        "namespace": "default"
    },
    "namespace": "default"
}
url = "/kapis/virtualization.ecpaas.io/v1/namespaces/default/virtualmachines"
cmd1 = 'curl -u '+user_pw+' -H "Content-Type: application/json" -X POST -d \''+json.dumps(data)+'\' '+host_ip+':30880'+url
result = os.popen(cmd1).read()
print("result= %s" % result)
#time.sleep (180)

result_dict = json.loads(result)
vm_name = result_dict["id"]

show_step(4, "Check virtual machine status from "+result_dict["id"])
cmd1 = "kubectl get vm " + result_dict["id"]
for x in range(0, 25):
    time.sleep(10)
    result_vm_status = os.popen(cmd1).read()
    print(result_vm_status)
    if "Running" in result_vm_status:
        break
    else:
        if x <= 24: continue
        print("The virtual machine took too long to create. fail")
        sys.exit(0)

show_step(5, "Get the virtual machine IP from "+result_dict["id"])
time.sleep(10)
cmd1="kubectl get pods -o wide "
result_k8s = os.popen(cmd1).read()
print("result= %s" % result_k8s)
list_data = ",".join(result_k8s.split())
list_data = list_data.split(",")
print(list_data)
list_data_len = len(list_data)
for data_loc in range(0, list_data_len):
    if result_dict["id"] in list_data[data_loc]:
        #print(list_data[data_loc+5])
        vm_ip=list_data[data_loc+5]
        break

print(list_data[data_loc] + " IP = " +vm_ip)
delay_time = 30
print("The virtual machine has been final start up, please wait for %d seconds." % delay_time)
time.sleep(delay_time)

#vm_ip="10.233.127.154"
show_step(6, "Test whether the PING of the virtual machine is passed from "+vm_ip)
cmd1 = "ping -c 16 "+vm_ip
result = os.popen(cmd1).read()
print(result)
vm_cfg = {
    "mgmt_ip": vm_ip,
    "username": "root",
    "password": "abc1234"
}
vm_connect = SSH_CONNECT(vm_cfg)
if("success" in vm_connect.ping("8.8.8.8", 4, True)):
    print("========================")
    print("===   ping test pass ===")
    print("========================")
else:
    print("Ping Test Fail ...  Cannot connect vm "+vm_ip)



show_step(7, "Get all PVC data ")
cmd1="kubectl get pvc"
result_k8s = os.popen(cmd1).read()
print("result= %s" % result_k8s)

show_step(8, "Create Data disk of VM")
data = {
    "description": "",
    "name": "data1",
    "namespace": "default",
    "size": 10
}
url = "/kapis/virtualization.ecpaas.io/v1/namespaces/default/disks"
cmd1 = 'curl -u '+user_pw+' -H "Content-Type: application/json" -X POST -d \''+json.dumps(data)+'\' '+host_ip+':30880'+url
result = os.popen(cmd1).read()
print("result= %s" % result)

# # result_dict= {
# #  "id": "disk-7f43ef58"
# # }

result_dict = json.loads(result)
result_disk = result_dict["id"]
print("New disk id = ", result_disk)

show_step(9, "Check new PVC status ")
cmd1="kubectl get pvc"
for x in range(0, 10):
    time.sleep(10)
    result_status = os.popen(cmd1).read()
    print("result= %s" % result_status)
    list_data = ",".join(result_status.split())
    list_data = list_data.split(",")
    list_data_len = len(list_data)
    loop_mark=1
    for data_loc in range(0, list_data_len):
        if result_disk in list_data[data_loc] and "Bound" in list_data[data_loc+1]:
            loop_mark=0
            break
    if loop_mark == 0:
        msg = "The data disk of %s has been bound" % result_disk
        print("="*len(msg))
        print(msg)
        print("="*len(msg))
        break
    if x <= 9: continue
    print("Create new data disk. fail")
    sys.exit(0)

#result_disk = "disk-cc027cb3"
#vm_name = "vm-df096cfe"
show_step(10, "Check VM")
url = "/kapis/virtualization.ecpaas.io/v1/virtualmachines"
cmd1 = 'curl -u '+user_pw+' -H "Content-Type: application/json" -X GET '+host_ip+':30880'+url
result_status = os.popen(cmd1).read()
result_dict = json.loads(result_status)
vm_data = result_dict["items"]
loop_mark=1
for data_loc in range(0, len(vm_data)):
    print(vm_data[data_loc])
    if vm_name in vm_data[data_loc]["id"]:
        loop_mark=0
        break
if loop_mark == 1:
    print("The %s of VM not exists. fail" % vm_name)
    sys.exit(0)

show_step(10.1, "Mount data dick on VM")
data = {
  "disk": [
    {
      "action": "mount",
      "id": result_disk,
      "namespace": "default"
    }
  ]
}
url = "/kapis/virtualization.ecpaas.io/v1/namespaces/default/virtualmachines/%s" % vm_name
cmd1 = 'curl -u '+user_pw+' -H "Content-Type: application/json" -X PUT -d \''+json.dumps(data)+'\' '+host_ip+':30880'+url
result = os.popen(cmd1).read()
print("result= %s" % result)

show_step(11, "Check vm mount disk status ")
url = "/kapis/virtualization.ecpaas.io/v1/namespaces/default/virtualmachines/%s" % vm_name
cmd1 = 'curl -u '+user_pw+' -H "Content-Type: application/json" -X GET '+host_ip+':30880'+url
for x in range(0, 6):
    time.sleep(10)
    result_status = os.popen(cmd1).read()
    #print("result= %s" % result_status)
    result_dict = json.loads(result_status)
    disk_data = result_dict["disks"]
    loop_mark=1
    for data_loc in range(0, len(disk_data)):
        print(disk_data[data_loc])
        if result_disk in disk_data[data_loc]["id"]:
            loop_mark=0
            break
    if loop_mark == 0:
        msg = "The data disk of %s has been mount" % result_disk
        print("="*len(msg))
        print(msg)
        print("="*len(msg))
        break
    if x <= 4: continue
    print("Mount data disk of %s. fail" % result_disk)
    sys.exit(0)

show_step(12, "Confirm whether the virtual machine has been mounted with PVC")
vm_cfg = {
    "mgmt_ip": vm_ip,
    "username": "root",
    "password": "abc1234"
}
pass_mark=0
for x in range(0, 6):
    time.sleep(10)
    vm_connect = SSH_CONNECT(vm_cfg)
    ssh_result = vm_connect.run_cmd("lsblk", True).decode().split("\n")
    for p in ssh_result:
        print(p)
        if "10G" in p: pass_mark=1
    if(pass_mark == 1):
        msg = "The new PVC has been mounted on the virtual machine => PASS"
        print("="*len(msg))
        print("%s" % msg)
        print("="*len(msg))
        break
if pass_mark == 0: print("New PVC fails to mount on virtual machine => FAIL")
