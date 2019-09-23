# This Vagrantfile is used for testing with docker version 1.12 and CentOS 7.5
# as a close enough replacement for development to RedHat 7.5 without
# additional steps for requesting licenses every time machine is destroyed.
# After `vagrant up` end you'll have ready to use Docker engine and
# docker-compose.
# Directory `/vagrant` is mounted to local folder so you will find all source
# code there.
#
# Simple steps for starting with this image:
#   vagrant destroy -f && vagrant up
#   vagrant ssh
# Inside running machine:
#   cd /vagrant
#   sudo docker-compose -f docker-compose-dev.yml up -d && sleep 60 && \
#     docker-compose -f docker-compose-metric.yml -f docker-compose-log.yml up


Vagrant.configure("2") do |config|

  # You need to uninstall `vagrant-cachier` plugin to make this work.

  if Vagrant.has_plugin?("vagrant-notify")
    config.notify.enable = false
  end

  # Handle local proxy settings
  if Vagrant.has_plugin?("vagrant-proxyconf")
    if ENV["http_proxy"]
      config.proxy.http = ENV["http_proxy"]
    end
    if ENV["https_proxy"]
      config.proxy.https = ENV["https_proxy"]
    end
    if ENV["no_proxy"]
      config.proxy.no_proxy = ENV["no_proxy"] + ',192.168.50.10,10.0.2.15,127.0.0.1'
    end
  end

  config.vm.hostname = "testing-old-docker"
  config.vm.box = "centos/7"
  config.vm.box_version = "1809.01"  # Use CentOS 7.5
  config.vm.network "private_network",ip:"192.168.50.10"

  config.vm.provider "virtualbox" do |vb|
    vb.gui = false
    vb.memory = "12800"
    vb.cpus = 4
    # vb.customize ["modifyvm", :id, "--cpuexecutioncap", "50"]
  end

  config.vm.provision "shell", privileged: false, inline: <<-SHELL
    set -x

    sudo yum -y install wget git libcgroup libtool-ltdl libseccomp policycoreutils-python

    mkdir -p ~/docker
    cd ~/docker
    wget https://yum.dockerproject.org/repo/main/centos/7/Packages/docker-engine-1.12.6-1.el7.centos.x86_64.rpm \
    https://yum.dockerproject.org/repo/main/centos/7/Packages/docker-engine-selinux-1.12.6-1.el7.centos.noarch.rpm

    # Hack for vagrant-proxyconf plugin...
    sudo mkdir -p /etc/systemd/system/docker.service.d
    sudo sh -c 'echo -e "[Service]\nEnvironmentFile=-/etc/sysconfig/docker" >> /etc/systemd/system/docker.service.d/http-proxy.conf'

    sudo rpm -ivh docker-engine-1.12.6-1.el7.centos.x86_64.rpm docker-engine-selinux-1.12.6-1.el7.centos.noarch.rpm
    sudo systemctl enable docker.service
    sudo systemctl start docker.service

    sudo curl -L https://github.com/docker/compose/releases/download/1.12.0/docker-compose-`uname -s`-`uname -m` -o /usr/bin/docker-compose
    sudo chmod +x /usr/bin/docker-compose

  SHELL

end
