#!/usr/bin/python3
import unshare
import argparse
import os
import sys
import shutil
import time
from cgroupspy import trees
from cgroupspy.interfaces import CommaDashSetFile

def uts_namespace(args):
    unshare.unshare(unshare.CLONE_NEWUTS)
    os.system("hostname " + args.hostname)

def net_namespace(args):
    unshare.unshare(unshare.CLONE_NEWNET)
    os.system("ip link add name eth1 type veth peer name veth1")
    os.system("ip link set dev veth1 netns ")
    os.system("ifconfig eth1 " + args.ip_addr)

def mnt_namespace(args):
    if(os.path.isdir(args.root_path)):
            shutil.rmtree(args.root_path)
    os.mkdir(args.root_path)
    os.system("tar -xzf ubuntu-rootfs.tar.gz -C " + args.root_path + " 2>/dev/null")
    os.system("cp mem loop " + args.root_path + "/home")
    os.system("chmod 766 " + args.root_path + "/home/loop")
    os.system("chmod 766 " + args.root_path + "/home/mem")
    unshare.unshare(unshare.CLONE_NEWNS)
   
def pid_namespace(args):
    unshare.unshare(unshare.CLONE_NEWPID)

def cpu_cgroup(args, id):
    t = trees.Tree()
    cset = t.get_node_by_path('/cpuset/')
    cpu_cgroup = cset.create_cgroup('cpuset_cgroup_'+id)
    cpu_cgroup.controller.clone_children = 1
    cpu_cgroup.controller.cpus = [args.cpu_num]
    cpu_cgroup.controller.mems = [0]
    cpu_cgroup.controller.tasks = os.getpid()

def mem_cgroup(args, id):
    t = trees.Tree()
    mem = t.get_node_by_path('/memory/')
    mem_cgroup = mem.create_cgroup('mem_cgroup_'+id)
    mem_cgroup.controller.clone_children = 1
    mem_cgroup.controller.limit_in_bytes = str(args.mem_size * 1024 * 1024)
    mem_cgroup.controller.swapiness = 0
    mem_cgroup.controller.tasks = os.getpid()
    
def exe_bash(args):
    os.chroot(args.root_path)
    os.chdir(args.root_path)
    newpid = os.fork()
    if newpid == 0:
        os.system("mount -t proc proc /proc")
        os.execle('/bin/bash', '/bin/bash', os.environ)
    else:
        os.wait()
        os.system('su -c "mount proc"')
    pass

if __name__ == "__main__":
    print ("*************************")
    print ("*                       *")
    print ("*      Mini Docker      *")
    print ("*                       *")
    print ("*************************")

    parser = argparse.ArgumentParser(description='This is a miniDocker.')

    parser.add_argument('--hostname', action="store", dest="hostname", type=str, default="administrator",
                    help='set the container\'s hostname')

    parser.add_argument('--ip_addr', action="store", dest="ip_addr", type=str, default="10.0.0.1",
                    help='set the container\'s ip address')

    parser.add_argument('--mem', action="store", dest="mem_size", type=int, default=10,
                    help='set the container\'s memory size (MB)')

    parser.add_argument('--cpu', action="store", dest="cpu_num", type=int, default=0,
                    help='set the container\'s cpu number')

    parser.add_argument('--root_path', action="store", dest="root_path", type=str, default="./new_root",
                    help='set the new root file system path of the container')

    args = parser.parse_args()
    id = str(int(time.time()))

    #create hostname namespace
    uts_namespace(args)
    #create network namespace
    net_namespace(args)
    #create filesystem namespace
    mnt_namespace(args)
    #create pid namespace
    pid_namespace(args)
    #create cpu cgroup
    cpu_cgroup(args, id)
    #create memory cgroup
    mem_cgroup(args, id)
    #execute the bash process "/bin/bash"
    exe_bash(args)
